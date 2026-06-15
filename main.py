import io, re, jwt, datetime, time, json, hashlib
from fastapi import FastAPI, File, UploadFile, Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import pdfplumber
import httpx
from pydantic_settings import BaseSettings
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy import Column, Integer, String, Text, Float, DateTime
import redis.asyncio as aioredis

# 1. إدارة الإعدادات والبيئة الحساسة
class Settings(BaseSettings):
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    GEMINI_API_KEY: str
    DATABASE_URL: str
    REDIS_URL: str

    class Config:
        env_file = ".env"

settings = Settings()

GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"

# 2. إعداد قاعدة البيانات والـ ORM (PostgreSQL Async)
engine = create_async_engine(settings.DATABASE_URL, echo=False)
async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
Base = declarative_base()

class AuditLog(Base):
    __tablename__ = "audit_logs"
    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String(255))
    file_hash = Column(String(64), index=True)
    risk_score = Column(Integer)
    risk_level = Column(String(50))
    summary = Column(Text)
    latency = Column(Float)
    created_at = Column(DateTime, default=lambda: datetime.datetime.now(datetime.UTC))

# 3. إعداد الـ Cache (Redis Async)
redis_client = aioredis.from_url(settings.REDIS_URL, decode_responses=True)

app = FastAPI(title="AuditPro Edge Enterprise", version="3.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

@app.on_event("startup")
async def startup():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

@app.post("/login")
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    if form_data.username == "admin" and form_data.password == "admin":
        expire = datetime.datetime.now(datetime.UTC) + datetime.timedelta(hours=8)
        token = jwt.encode({"sub": form_data.username, "exp": expire}, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
        return {"access_token": token, "token_type": "bearer"}
    raise HTTPException(status_code=400, detail="Incorrect username or password")

def extract_all_pdf_text(content: bytes) -> str:
    try:
        with pdfplumber.open(io.BytesIO(content)) as pdf:
            full_text = []
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    full_text.append(text)
            if not full_text:
                return "Empty PDF"
            raw = " ".join(full_text)
            cleaned = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', ' ', raw)
            return ' '.join(cleaned.split())
    except Exception as e:
        return f"PDF error: {str(e)[:80]}"

async def analyze_with_gemini(text: str) -> dict:
    if not settings.GEMINI_API_KEY:
        return {"score": 55, "risk_level": "MEDIUM", "summary": "No API key set.",
                "risks": ["API key missing"], "recommendations": ["Set GEMINI_API_KEY"], "source": "no_key"}

    prompt = f"""Analyze this contract and reply ONLY with a JSON object, no markdown blocks:

Contract: {text}

Reply with exactly this JSON structure:
{{"risk_score": <0-100>, "risk_level": "<LOW|MEDIUM|HIGH>", "summary": "<one sentence analysis>", "risks": ["<risk1>", "<risk2>"], "recommendations": ["<rec1>", "<rec2>"]}}"""

    async with httpx.AsyncClient(timeout=45.0) as client:
        res = await client.post(
            f"{GEMINI_URL}?key={settings.GEMINI_API_KEY}",
            json={"contents": [{"parts": [{"text": prompt}]}]}
        )
        res.raise_for_status()
        raw = res.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
        raw = re.sub(r'```json|```', '', raw).strip()
        data = json.loads(raw)
        return {
            "score": min(100, max(0, int(data.get("risk_score", 55)))),
            "risk_level": data.get("risk_level", "MEDIUM"),
            "summary": data.get("summary", "Analysis complete."),
            "risks": data.get("risks", []),
            "recommendations": data.get("recommendations", []),
            "source": "gemini-2.0-flash",
        }

@app.post("/analyze-contract")
async def analyze_contract(file: UploadFile = File(...), token: str = Depends(oauth2_scheme)):
    start_time = time.time()
    
    try:
        jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")

    content = await file.read()
    
    file_hash = hashlib.sha256(content).hexdigest()
    cached_result = await redis_client.get(file_hash)
    
    if cached_result:
        result = json.loads(cached_result)
        latency = round(time.time() - start_time, 3)
        return JSONResponse(content={**result, "latency": f"{latency}s", "cache_hit": True})

    text = extract_all_pdf_text(content)
    if "PDF error" in text or text == "Empty PDF":
        raise HTTPException(status_code=400, detail=text)

    try:
        result = await analyze_with_gemini(text)
    except Exception as e:
        result = {"score": 50, "risk_level": "MEDIUM",
                  "summary": f"Fallback due to error: {str(e)[:80]}",
                  "risks": ["Analysis error"], "recommendations": ["Retry"], "source": "fallback"}

    score = result["score"]
    risk_level = result.get("risk_level") or ("HIGH" if score >= 75 else "MEDIUM" if score >= 40 else "LOW")
    latency = round(time.time() - start_time, 2)

    response_data = {
        "risk_score": score,
        "risk_level": risk_level,
        "summary": result.get("summary", "Analysis complete."),
        "risks": result.get("risks", []),
        "recommendations": result.get("recommendations", []),
        "extracted_text_preview": text[:150] + "...",
        "model_source": result["source"],
        "cache_hit": False
    }

    await redis_client.setex(file_hash, 86400, json.dumps(response_data))

    async with async_session() as session:
        log = AuditLog(
            filename=file.filename,
            file_hash=file_hash,
            risk_score=score,
            risk_level=risk_level,
            summary=result.get("summary", "Analysis complete."),
            latency=latency
        )
        session.add(log)
        await session.commit()

    return JSONResponse(content={**response_data, "latency": f"{latency}s"})

@app.get("/health")
async def health():
    try:
        await redis_client.ping()
        redis_status = "connected"
    except Exception:
        redis_status = "disconnected"
        
    return {
        "status": "ok",
        "model": "gemini-2.0-flash",
        "api_key_set": bool(settings.GEMINI_API_KEY),
        "redis_cache_status": redis_status
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8090, log_level="info")
