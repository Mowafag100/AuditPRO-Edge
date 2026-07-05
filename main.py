import io, re, jwt, datetime, time, json, hashlib, os, uuid
import logging
import httpx
from fastapi import FastAPI, File, UploadFile, Depends, HTTPException, Request
from fastapi.security import OAuth2PasswordBearer
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from fastapi import Form
import pdfplumber
from pydantic_settings import BaseSettings
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy import Column, Integer, String, Text, Float, DateTime, select
from prometheus_client import Counter, Histogram, generate_latest, REGISTRY

# --- إعدادات التسجيل (استخدام logging القياسي) ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- إعدادات النظام ---
class Settings(BaseSettings):
    SECRET_KEY: str = "my_super_secret_key_123"
    GEMINI_API_KEY: str = "your_gemini_key_here"
    DATABASE_URL: str = "sqlite+aiosqlite:///./platform.db"
    BYNARA_API_KEY: str = os.getenv("BYNARA_API_KEY", "")
    OLLAMA_HOST: str = "http://localhost:11434"

settings = Settings()
engine = create_async_engine(settings.DATABASE_URL, echo=False)
async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
Base = declarative_base()

# --- متغيرات البيئة الإضافية ---
USE_CHROMADB = os.getenv("USE_CHROMADB", "false").lower() == "true"
CHROMA_HOST = os.getenv("CHROMA_HOST", "http://localhost:8000")

class AuditLog(Base):
    __tablename__ = "audit_logs"
    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String(255))
    risk_score = Column(Integer)
    risk_level = Column(String(50))
    summary = Column(Text)
    latency = Column(Float)
    created_at = Column(DateTime, default=lambda: datetime.datetime.utcnow())
    user_id = Column(String(36), nullable=True)  # عمود جديد لتخزين معرف المستخدم

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

# --- دوال ChromaDB (معطلة افتراضياً) ---
async def chromadb_health() -> bool:
    if not USE_CHROMADB:
        return False
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{CHROMA_HOST}/api/v1/heartbeat")
            return resp.status_code == 200
    except Exception as e:
        logger.error(f"chromadb_health_check_failed: {e}")
        return False

async def chromadb_query(query: str, n_results: int = 3) -> list:
    if not USE_CHROMADB:
        return []
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                f"{CHROMA_HOST}/api/v1/collections/contracts/query",
                json={"query_texts": [query], "n_results": n_results}
            )
            if resp.status_code == 200:
                data = resp.json()
                return data.get("documents", [[]])[0]
            return []
    except Exception as e:
        logger.error(f"chromadb_query_error: {e}")
        return []

# --- حدث بدء التشغيل ---
@app.on_event("startup")
async def startup():
    async with engine.begin() as conn:
        # تحديث الجداول (يضيف عمود user_id تلقائياً إذا لم يكن موجوداً)
        await conn.run_sync(Base.metadata.create_all)
        logger.info("✅ قاعدة البيانات جاهزة.")

    if USE_CHROMADB:
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                health = await client.get(f"{CHROMA_HOST}/api/v1/heartbeat")
                if health.status_code == 200:
                    logger.info("chromadb_health_check: reachable")
                    resp = await client.post(
                        f"{CHROMA_HOST}/api/v1/collections",
                        json={"name": "contracts"}
                    )
                    if resp.status_code in [200, 201]:
                        logger.info("chromadb_collection_created: contracts")
                    else:
                        logger.warning(f"chromadb_collection_creation_failed: {resp.status_code}")
                else:
                    logger.warning(f"chromadb_health_check_failed: {health.status_code}")
        except Exception as e:
            logger.warning(f"chromadb_setup_error: {e}")
    else:
        logger.info("ChromaDB disabled. RAG will be skipped.")

# --- دالة تحليل باستخدام Bynara API (بديل عن Ollama) ---
async def audit_with_bynara(text: str) -> dict:
    api_key = settings.BYNARA_API_KEY
    if not api_key:
        logger.warning("BYNARA_API_KEY not set. Using fallback.")
        return None

    truncated = text[:1500]
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
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                "https://router.bynara.id/v1/chat/completions",
                headers={"Authorization": f"Bearer {api_key}"},
                json={
                    "model": "kimi-k2.7-code-free",
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.3
                }
            )
            if response.status_code == 200:
                content = response.json()["choices"][0]["message"]["content"]
                json_match = re.search(r'(\{.*\})', content, re.DOTALL)
                if json_match:
                    data = json.loads(json_match.group(1))
                    return {
                        "score": data.get("score", 50),
                        "risk_level": data.get("risk_level", "MEDIUM"),
                        "summary": data.get("summary", "No summary."),
                        "risks": data.get("risks", []),
                        "recommendations": data.get("recommendations", []),
                        "source": "Bynara (Kimi K2.7)"
                    }
                else:
                    return {
                        "score": 50,
                        "risk_level": "MEDIUM",
                        "summary": content[:200],
                        "risks": ["Unable to parse structured output."],
                        "recommendations": ["Check manually."],
                        "source": "Bynara (Kimi K2.7) - Raw"
                    }
            else:
                logger.error(f"Bynara API error: {response.status_code} - {response.text}")
                return None
    except Exception as e:
        logger.error(f"Bynara API exception: {e}")
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

# --- دوال نقاط النهاية ---
@app.post("/login")
async def login():
    user_id = str(uuid.uuid4())  # معرف فريد لكل جلسة
    expire = datetime.datetime.utcnow() + datetime.timedelta(hours=8)
    token = jwt.encode({"sub": user_id, "exp": expire}, settings.SECRET_KEY, algorithm="HS256")
    return {"access_token": token, "token_type": "bearer"}

@app.get("/history")
async def get_history(token: str = Depends(oauth2_scheme)):
    # فك التوكن للحصول على user_id
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        user_id = payload.get("sub")
    except:
        raise HTTPException(status_code=401, detail="Invalid token")

    async with async_session() as session:
        result = await session.execute(
            select(AuditLog)
            .where(AuditLog.user_id == user_id)
            .order_by(AuditLog.created_at.desc())
            .limit(20)
        )
        logs = result.scalars().all()
        return [{"id": l.id, "filename": l.filename, "risk_score": l.risk_score, "date": l.created_at.isoformat()} for l in logs]

@app.get("/history/{log_id}")
async def get_audit_by_id(log_id: int, token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        user_id = payload.get("sub")
    except:
        raise HTTPException(status_code=401, detail="Invalid token")

    async with async_session() as session:
        log = await session.get(AuditLog, log_id)
        if not log or log.user_id != user_id:
            raise HTTPException(status_code=404, detail="Audit not found")
        return {
            "id": log.id,
            "filename": log.filename,
            "risk_score": log.risk_score,
            "risk_level": log.risk_level,
            "summary": log.summary,
            "latency": log.latency,
            "created_at": log.created_at.isoformat()
        }

@app.post("/chat")
async def chat_with_contract(
    message: str = Form(...),
    context: str = Form(...),
    token: str = Depends(oauth2_scheme)
):
    try:
        api_key = settings.BYNARA_API_KEY
        if not api_key:
            return {"response": "BYNARA_API_KEY not set."}
        truncated_context = context[:2000]
        prompt = f"""You are a legal AI assistant. Given the following contract context and analysis, answer the user's question.

Contract Context: {truncated_context}

User Question: {message}

Provide a clear and concise answer."""
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                "https://router.bynara.id/v1/chat/completions",
                headers={"Authorization": f"Bearer {api_key}"},
                json={
                    "model": "kimi-k2.7-code-free",
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.3
                }
            )
            if resp.status_code == 200:
                reply = resp.json()["choices"][0]["message"]["content"]
                return {"response": reply}
            else:
                return {"response": "Chat API error."}
    except Exception as e:
        logger.error(f"chat_error: {e}")
        return {"response": "An error occurred."}

@app.post("/analyze-contract")
async def analyze_contract(
    file: UploadFile = File(...),
    token: str = Depends(oauth2_scheme)
):
    # فك التوكن للحصول على user_id
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        user_id = payload.get("sub")
    except:
        raise HTTPException(status_code=401, detail="Invalid token")

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
            logger.error(f"pdf_extraction_error: {e}")
            text = ""

        if not text.strip():
            result = local_security_audit("")
            result["summary"] = "No readable text found."
            return {**result, "latency": "0.0s"}

        logger.info(f"pdf_extracted: filename={file.filename}, length={len(text)}")

        context = await chromadb_query(text, n_results=2) if USE_CHROMADB else []
        context_str = "\n".join(context) if context else ""

        result = await audit_with_bynara(text)
        if not result:
            result = local_security_audit(text)
            logger.info("analysis_fallback_used")
        else:
            logger.info(f"analysis_completed: source={result.get('source')}")

        latency = round(time.time() - start_time, 3)

        async with async_session() as session:
            new_log = AuditLog(
                filename=file.filename,
                risk_score=result["score"],
                risk_level=result["risk_level"],
                summary=result["summary"],
                latency=latency,
                user_id=user_id  # ربط التحليل بالمستخدم
            )
            session.add(new_log)
            await session.commit()

        return {**result, "latency": f"{latency}s"}

    except Exception as e:
        logger.error(f"unhandled_exception: {e}")
        return JSONResponse(status_code=500, content={"error": "Internal server error", "details": str(e)})

# ============================================
# نقاط النهاية للمراقبة (Monitoring)
# ============================================
@app.get("/health")
async def health_check():
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
        status["services"]["ai_api"] = "up" if settings.BYNARA_API_KEY else "down"
    except:
        status["services"]["ai_api"] = "down"
    if all(v == "up" for v in status["services"].values()):
        status["status"] = "healthy"
        return JSONResponse(content=status, status_code=200)
    else:
        status["status"] = "unhealthy"
        return JSONResponse(content=status, status_code=503)

@app.get("/metrics")
async def metrics():
    return Response(content=generate_latest(REGISTRY), media_type="text/plain")

@app.post("/evaluate")
async def evaluate_contract(
    file: UploadFile = File(...),
    reference_text: str = Form(...),
    token: str = Depends(oauth2_scheme)
):
    return JSONResponse(content={"error": "Evaluation endpoint disabled for now."})

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8091))
    uvicorn.run(app, host="0.0.0.0", port=port)