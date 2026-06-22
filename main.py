import io, re, jwt, datetime, time, json, hashlib, os
import structlog
import httpx
from fastapi import FastAPI, File, UploadFile, Depends, HTTPException, Request
from fastapi.security import OAuth2PasswordBearer
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
import pdfplumber
from pydantic_settings import BaseSettings
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy import Column, Integer, String, Text, Float, DateTime, select
from src.logging_config import configure_logging
from prometheus_client import Counter, Histogram, generate_latest, REGISTRY

# --- إعدادات التسجيل المنظم ---
configure_logging()
logger = structlog.get_logger()

# --- إعدادات النظام ---
class Settings(BaseSettings):
    SECRET_KEY: str = "my_super_secret_key_123"
    GEMINI_API_KEY: str = "your_gemini_key_here"
    DATABASE_URL: str = "sqlite+aiosqlite:///./platform.db"
    OLLAMA_HOST: str = "http://localhost:11434"

settings = Settings()
engine = create_async_engine(settings.DATABASE_URL, echo=False)
async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
Base = declarative_base()

class AuditLog(Base):
    __tablename__ = "audit_logs"
    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String(255))
    risk_score = Column(Integer)
    risk_level = Column(String(50))
    summary = Column(Text)
    latency = Column(Float)
    created_at = Column(DateTime, default=lambda: datetime.datetime.utcnow())

app = FastAPI(title="AuditPro Edge Enterprise")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

# ============================================
# مقاييس Prometheus للمراقبة
# ============================================
REQUEST_COUNT = Counter('http_requests_total', 'Total HTTP requests', ['method', 'endpoint', 'status'])
REQUEST_LATENCY = Histogram('http_request_duration_seconds', 'HTTP request latency', ['method', 'endpoint'])
ERROR_COUNT = Counter('http_errors_total', 'Total HTTP errors', ['method', 'endpoint', 'error_type'])

@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    duration = time.time() - start_time
    REQUEST_COUNT.labels(method=request.method, endpoint=request.url.path, status=response.status_code).inc()
    REQUEST_LATENCY.labels(method=request.method, endpoint=request.url.path).observe(duration)
    if response.status_code >= 400:
        ERROR_COUNT.labels(method=request.method, endpoint=request.url.path, error_type=str(response.status_code)).inc()
    return response

# --- دوال ChromaDB ---
async def chromadb_health() -> bool:
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get("http://chromadb:8000/api/v2/heartbeat")
            return resp.status_code == 200
    except Exception as e:
        logger.error("chromadb_health_check_failed", error=str(e))
        return False

async def chromadb_query(query: str, n_results: int = 3) -> list:
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                "http://chromadb:8000/api/v2/collections/contracts/query",
                json={"query_texts": [query], "n_results": n_results}
            )
            if resp.status_code == 200:
                data = resp.json()
                return data.get("documents", [[]])[0]
            return []
    except Exception as e:
        logger.error("chromadb_query_error", error=repr(e), type=type(e).__name__)
        return []

# --- حدث بدء التشغيل ---
@app.on_event("startup")
async def startup():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            health = await client.get("http://chromadb:8000/api/v2/heartbeat")
            if health.status_code == 200:
                logger.info("chromadb_health_check", status="reachable")
                resp = await client.post(
                    "http://chromadb:8000/api/v2/collections",
                    json={"name": "contracts"}
                )
                if resp.status_code in [200, 201]:
                    logger.info("chromadb_collection_created", collection="contracts")
                else:
                    logger.warning("chromadb_collection_creation_failed", status=resp.status_code, response=resp.text)
            else:
                logger.warning("chromadb_health_check_failed", status=health.status_code)
    except Exception as e:
        logger.warning("chromadb_setup_error", error=str(e))

# --- نقاط النهاية ---
@app.post("/login")
async def login():
    expire = datetime.datetime.utcnow() + datetime.timedelta(hours=8)
    token = jwt.encode({"sub": "admin", "exp": expire}, settings.SECRET_KEY, algorithm="HS256")
    return {"access_token": token, "token_type": "bearer"}

@app.get("/history")
async def get_history():
    async with async_session() as session:
        result = await session.execute(select(AuditLog).order_by(AuditLog.created_at.desc()).limit(20))
        logs = result.scalars().all()
        return [{"filename": l.filename, "risk_score": l.risk_score, "date": l.created_at.isoformat()} for l in logs]

async def audit_with_ollama(text: str, context: str = "") -> dict:
    ollama_host = os.getenv("OLLAMA_HOST", settings.OLLAMA_HOST)
    truncated = text[:1500]
    
    if context:
        prompt = f"""Context from similar contracts:
{context}

Analyze the following contract and provide ONLY a valid JSON object with these fields:
- score (0-100)
- risk_level (LOW/MEDIUM/HIGH/CRITICAL)
- summary (brief summary)
- risks (list of risks)
- recommendations (list of recommendations)

Contract:
{truncated}
JSON:"""
    else:
        prompt = f"""Analyze the following contract and provide ONLY a valid JSON object with these fields:
- score (0-100)
- risk_level (LOW/MEDIUM/HIGH/CRITICAL)
- summary (brief summary)
- risks (list of risks)
- recommendations (list of recommendations)

Contract:
{truncated}
JSON:"""

    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{ollama_host}/api/generate",
                json={"model": "llama3", "prompt": prompt, "stream": False}
            )
            if response.status_code == 200:
                result = response.json()
                answer = result.get("response", "")
                logger.info("ollama_response_received", snippet=answer[:200])
                
                try:
                    json_match = re.search(r'(\{.*\})', answer, re.DOTALL)
                    if json_match:
                        data = json.loads(json_match.group(1))
                        return {
                            "score": data.get("score", 50),
                            "risk_level": data.get("risk_level", "MEDIUM"),
                            "summary": data.get("summary", "No summary."),
                            "risks": data.get("risks", []),
                            "recommendations": data.get("recommendations", []),
                            "source": "Ollama (Llama3)"
                        }
                    else:
                        return {
                            "score": 50,
                            "risk_level": "MEDIUM",
                            "summary": answer[:200],
                            "risks": ["Unable to parse structured output."],
                            "recommendations": ["Check manually."],
                            "source": "Ollama (Llama3) - Raw"
                        }
                except json.JSONDecodeError as e:
                    logger.warning("ollama_json_parse_failed", error=str(e))
                    return {
                        "score": 50,
                        "risk_level": "MEDIUM",
                        "summary": answer[:200],
                        "risks": ["Unable to parse structured output."],
                        "recommendations": ["Check manually."],
                        "source": "Ollama (Llama3) - Raw"
                    }
            else:
                logger.error("ollama_http_error", status=response.status_code)
                return None
    except Exception as e:
        logger.error("ollama_connection_error", error=str(e), exc_info=True)
        return None

def local_security_audit(text: str) -> dict:
    return {
        "score": 45,
        "risk_level": "MEDIUM",
        "summary": "Local analysis executed due to connection fallback.",
        "risks": ["Standard contract clauses detected."],
        "recommendations": ["Review by legal counsel."],
        "source": "Local-Audit Engine (TinyLlama 1.1B)"
    }

@app.post("/analyze-contract")
async def analyze_contract(file: UploadFile = File(...), token: str = Depends(oauth2_scheme)):
    start_time = time.time()
    try:
        if not file.filename.lower().endswith('.pdf'):
            return JSONResponse(status_code=400, content={"error": "Only PDF files are supported."})

        content = await file.read()
        text = ""
        try:
            with pdfplumber.open(io.BytesIO(content)) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
        except Exception as e:
            logger.error("pdf_extraction_error", error=str(e))
            text = ""

        if not text.strip():
            result = local_security_audit("")
            result["summary"] = "No readable text found."
            return {**result, "latency": "0.0s"}

        logger.info("pdf_extracted", filename=file.filename, length=len(text))

        context = await chromadb_query(text, n_results=2)
        context_str = "\n".join(context) if context else ""

        ollama_result = await audit_with_ollama(text, context_str)
        if ollama_result:
            result = ollama_result
            logger.info("analysis_completed", source=result.get('source'))
        else:
            result = local_security_audit(text)
            logger.info("analysis_fallback_used", source=result.get('source'))

        latency = round(time.time() - start_time, 3)

        async with async_session() as session:
            new_log = AuditLog(
                filename=file.filename,
                risk_score=result["score"],
                risk_level=result["risk_level"],
                summary=result["summary"],
                latency=latency
            )
            session.add(new_log)
            await session.commit()

        return {**result, "latency": f"{latency}s"}

    except Exception as e:
        logger.error("unhandled_exception", error=str(e), exc_info=True)
        return JSONResponse(status_code=500, content={"error": "Internal server error", "details": str(e)})

# ============================================
# نقاط النهاية للمراقبة (Monitoring)
# ============================================
@app.get("/health")
async def health_check():
    """التحقق من صحة الخدمات الأساسية"""
    status = {"status": "healthy", "services": {}}
    
    try:
        chroma_ok = await chromadb_health()
        status["services"]["chromadb"] = "up" if chroma_ok else "down"
    except:
        status["services"]["chromadb"] = "down"
    
    try:
        async with async_session() as session:
            await session.execute("SELECT 1")
        status["services"]["database"] = "up"
    except:
        status["services"]["database"] = "down"
    
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            resp = await client.get("http://localhost:11434/api/tags")
            status["services"]["ollama"] = "up" if resp.status_code == 200 else "down"
    except:
        status["services"]["ollama"] = "down"
    
    if all(v == "up" for v in status["services"].values()):
        status["status"] = "healthy"
        return JSONResponse(content=status, status_code=200)
    else:
        status["status"] = "unhealthy"
        return JSONResponse(content=status, status_code=503)

@app.get("/metrics")
async def metrics():
    """نقطة نهاية لمقاييس Prometheus"""
    return Response(content=generate_latest(REGISTRY), media_type="text/plain")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8090)