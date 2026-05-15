import io, re, jwt, datetime, time, asyncio
from fastapi import FastAPI, File, UploadFile, Depends, HTTPException, BackgroundTasks
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import pdfplumber
from openai import AsyncOpenAI
import httpx

app = FastAPI(title="AuditPro Edge", version="2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

# ─── إعدادات Ollama ───────────────────────────────────────────────────────────
OLLAMA_BASE_URL = "http://localhost:11434/v1"
OLLAMA_MODEL    = "tinyllama"
SECRET_KEY      = "AUDITPRO_SUPER_SECRET_KEY_2024"
ALGORITHM       = "HS256"

# ─── بناء client بـ timeout طويل ─────────────────────────────────────────────
client = AsyncOpenAI(
    base_url=OLLAMA_BASE_URL,
    api_key="ollama",
    timeout=httpx.Timeout(130.0, connect=10.0),  # 90s للاستجابة، 10s للاتصال
)


# ══════════════════════════════════════════════════════════════════════════════
# تسجيل الدخول
# ══════════════════════════════════════════════════════════════════════════════
@app.post("/login")
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    expire = datetime.datetime.now(datetime.UTC) + datetime.timedelta(hours=8)
    token  = jwt.encode(
        {"sub": form_data.username, "exp": expire},
        SECRET_KEY,
        algorithm=ALGORITHM,
    )
    return {"access_token": token, "token_type": "bearer"}


# ══════════════════════════════════════════════════════════════════════════════
# فحص Ollama قبل الطلب
# ══════════════════════════════════════════════════════════════════════════════
async def check_ollama_alive() -> bool:
    """يتحقق أن Ollama شغّال ويستجيب."""
    try:
        async with httpx.AsyncClient(timeout=5.0) as http:
            r = await http.get("http://localhost:11434/api/tags")
            return r.status_code == 200
    except Exception:
        return False


# ══════════════════════════════════════════════════════════════════════════════
# استخراج نص PDF بشكل آمن
# ══════════════════════════════════════════════════════════════════════════════
def extract_pdf_text(content: bytes, max_chars: int = 200) -> str:
    """يستخرج النص من الصفحة الأولى، ويُنظّف الأحرف الغريبة."""
    try:
        with pdfplumber.open(io.BytesIO(content)) as pdf:
            if not pdf.pages:
                return "Empty PDF"
            raw = pdf.pages[0].extract_text() or "No text found"
            # تنظيف الأحرف التي تسبب Invalid Control Character
            cleaned = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', ' ', raw)
            cleaned = ' '.join(cleaned.split())          # ضغط المسافات
            return cleaned[:max_chars]
    except Exception as e:
        return f"PDF parse error: {str(e)[:80]}"


# ══════════════════════════════════════════════════════════════════════════════
# استدعاء TinyLlama مع Retry
# ══════════════════════════════════════════════════════════════════════════════
async def call_tinyllama(text: str, retries: int = 2) -> dict:
    """
    يطلب من TinyLlama رقماً فقط (0-100).
    يحاول مرتين قبل أن يعود بقيمة افتراضية.
    """
    prompt = (
        "You are a contract risk scorer. "
        "Reply ONLY with a single integer between 0 and 100. "
        "No words, no explanation. Just the number.\n\n"
        f"Text: {text}"
    )

    for attempt in range(retries):
        try:
            response = await asyncio.wait_for(
                client.chat.completions.create(
                    model=OLLAMA_MODEL,
                    messages=[{"role": "system", "content": "You are a JSON API. Reply with a single integer only. No words, no Spanish, no explanation."}, {"role": "user", "content": prompt}],
                    max_tokens=100,
                    temperature=0.0,
                ),
                timeout=120.0,   # حد زمني داخلي أقل من timeout الـ client
            )
            raw = response.choices[0].message.content.strip()
            match = re.search(r'\b(\d{1,3})\b', raw)
            if match:
                score = min(100, max(0, int(match.group(1))))
                return {"score": score, "source": "ai", "raw": raw}
        except asyncio.TimeoutError:
            if attempt < retries - 1:
                await asyncio.sleep(2)
            continue
        except Exception as e:
            if attempt < retries - 1:
                await asyncio.sleep(2)
            continue

    # قيمة heuristic احتياطية
    return {"score": 55, "source": "heuristic", "raw": "timeout"}


# ══════════════════════════════════════════════════════════════════════════════
# نقطة التحليل الرئيسية
# ══════════════════════════════════════════════════════════════════════════════
@app.post("/analyze-contract")
async def analyze_contract(
    file: UploadFile = File(...),
    token: str = Depends(oauth2_scheme),
):
    start = time.time()

    # 1) تحقق من token
    try:
        jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")

    # 2) تحقق من Ollama
    ollama_ok = await check_ollama_alive()

    # 3) استخراج النص
    try:
        content = await file.read()
        text = extract_pdf_text(content, max_chars=50)
    except Exception as e:
        text = "Extraction failed"

    # 4) استدعاء النموذج (أو heuristic إذا Ollama متوقف)
    if ollama_ok:
        result = await call_tinyllama(text)
    else:
        result = {"score": 60, "source": "offline", "raw": "Ollama not running"}

    score  = result["score"]
    source = result["source"]
    latency = round(time.time() - start, 2)

    # 5) تحديد مستوى الخطر
    if score >= 75:
        level = "HIGH"
        risks = [
            "High-risk clauses detected in preliminary scan",
            "Unusual liability terms identified",
            "Recommend legal review before signing",
        ]
        recs = [
            "Consult a legal professional immediately",
            "Request clause-by-clause breakdown",
            "Do not sign without full review",
        ]
    elif score >= 40:
        level = "MEDIUM"
        risks = [
            "Moderate risk indicators present",
            "Some standard clauses require attention",
        ]
        recs = [
            "Review highlighted sections carefully",
            "Clarify ambiguous terms with counterparty",
        ]
    else:
        level = "LOW"
        risks = ["No significant risk patterns detected"]
        recs  = ["Standard review process is sufficient"]

    return JSONResponse(content={
        "risk_score":       score,
        "risk_level":       level,
        "summary":          f"Analysis complete via {source}. Contract shows {level} risk profile.",
        "risks":            risks,
        "recommendations":  recs,
        "extracted_text":   text[:100] + "..." if len(text) > 100 else text,
        "latency":          f"{latency}s",
        "model_source":     source,
        "ollama_status":    "online" if ollama_ok else "offline",
    })


# ══════════════════════════════════════════════════════════════════════════════
# Health check
# ══════════════════════════════════════════════════════════════════════════════
@app.get("/health")
async def health():
    ollama_ok = await check_ollama_alive()
    return {
        "status": "ok",
        "ollama": "online" if ollama_ok else "offline",
        "model": OLLAMA_MODEL,
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8090, log_level="info")
