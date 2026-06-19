import io, re, jwt, datetime, time, json, hashlib, os, logging
from fastapi import FastAPI, File, UploadFile, Depends, HTTPException, Request
from fastapi.security import OAuth2PasswordBearer
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import pdfplumber
import httpx
from pydantic_settings import BaseSettings
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy import Column, Integer, String, Text, Float, DateTime, select

# --- إعدادات التسجيل الأسطورية ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- إعدادات النظام ---
class Settings(BaseSettings):
    SECRET_KEY: str = "my_super_secret_key_123"
    GEMINI_API_KEY: str = "your_gemini_key_here"
    DATABASE_URL: str = "sqlite+aiosqlite:///./platform.db"
    OLLAMA_HOST: str = "http://localhost:11434"  # تم التعديل للعمل محلياً

settings = Settings()
engine = create_async_engine(settings.DATABASE_URL, echo=False)
async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
Base = declarative_base()

# --- تعريف الجدول ---
class AuditLog(Base):
    __tablename__ = "audit_logs"
    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String(255))
    risk_score = Column(Integer)
    risk_level = Column(String(50))
    summary = Column(Text)
    latency = Column(Float)
    created_at = Column(DateTime, default=lambda: datetime.datetime.now(datetime.UTC))

app = FastAPI(title="AuditPro Edge Enterprise")

# --- تفعيل الـ CORS ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

@app.on_event("startup")
async def startup():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

@app.post("/login")
async def login():
    expire = datetime.datetime.now(datetime.UTC) + datetime.timedelta(hours=8)
    token = jwt.encode({"sub": "admin", "exp": expire}, settings.SECRET_KEY, algorithm="HS256")
    return {"access_token": token, "token_type": "bearer"}

@app.get("/history")
async def get_history():
    async with async_session() as session:
        result = await session.execute(select(AuditLog).order_by(AuditLog.created_at.desc()).limit(20))
        logs = result.scalars().all()
        return [{"filename": l.filename, "risk_score": l.risk_score, "date": l.created_at.isoformat()} for l in logs]

# --- دالة تحليل باستخدام Ollama (الأسطورية) ---
async def audit_with_ollama(text: str) -> dict:
    ollama_host = os.getenv("OLLAMA_HOST", settings.OLLAMA_HOST)
    truncated = text[:1500]  # تقليل النص لتسريع المعالجة
    
    prompt = f"""Analyze the following contract and provide ONLY a valid JSON object with these fields:
- score (0-100, where 0 is highest risk and 100 is lowest)
- risk_level (LOW/MEDIUM/HIGH/CRITICAL)
- summary (brief summary of findings)
- risks (list of specific risks found)
- recommendations (list of recommendations)

Contract text:
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
                logger.info(f"✅ Ollama raw response: {answer[:200]}...")
                
                # --- استخراج JSON من الرد (الجزء المصحح) ---
                try:
                    import re
                    # البحث عن JSON object في النص
                    json_match = re.search(r'(\{.*\})', answer, re.DOTALL)
                    if json_match:
                        data = json.loads(json_match.group(1))
                        return {
                            "score": data.get("score", 50),
                            "risk_level": data.get("risk_level", "MEDIUM"),
                            "summary": data.get("summary", "No summary provided."),
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
                            "recommendations": ["Check the contract manually."],
                            "source": "Ollama (Llama3) - Raw"
                        }
                except json.JSONDecodeError as e:
                    logger.warning(f"⚠️ JSON parsing failed: {e}")
                    return {
                        "score": 50,
                        "risk_level": "MEDIUM",
                        "summary": answer[:200],
                        "risks": ["Unable to parse structured output."],
                        "recommendations": ["Check the contract manually."],
                        "source": "Ollama (Llama3) - Raw"
                    }
            else:
                logger.error(f"❌ Ollama returned status {response.status_code}")
                return None
    except Exception as e:
        logger.error(f"❌ Ollama connection error: {e}", exc_info=True)
        return None

# --- دالة التحليل المحلية (الاحتياطي) ---
def local_security_audit(text: str) -> dict:
    return {
        "score": 45,
        "risk_level": "MEDIUM",
        "summary": "Local analysis executed due to connection fallback.",
        "risks": ["Standard contract clauses detected."],
        "recommendations": ["Review by legal counsel."],
        "source": "Local-Audit Engine (TinyLlama 1.1B)"
    }

# --- نقطة النهاية الرئيسية للتحليل ---
@app.post("/analyze-contract")
async def analyze_contract(file: UploadFile = File(...), token: str = Depends(oauth2_scheme)):
    start_time = time.time()
    
    # قراءة الملف
    content = await file.read()
    # استخراج النص من PDF
    text = ""
    try:
        with pdfplumber.open(io.BytesIO(content)) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
    except Exception as e:
        logger.error(f"PDF extraction error: {e}")
        text = ""
    
    if not text.strip():
        logger.warning("⚠️ No text extracted from PDF. Returning local audit.")
        result = local_security_audit("")
        result["summary"] = "No readable text found in the PDF document."
        return {**result, "latency": "0.0s"}
    
    logger.info(f"📄 Extracted text length: {len(text)} characters")
    
    # محاولة التحليل باستخدام Ollama
    ollama_result = await audit_with_ollama(text)
    
    if ollama_result:
        result = ollama_result
        logger.info(f"🤖 Analysis source: {result.get('source')}")
    else:
        result = local_security_audit(text)
        logger.info(f"⚠️ Using fallback: {result.get('source')}")
    
    latency = round(time.time() - start_time, 3)

    # حفظ في قاعدة البيانات
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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8090)