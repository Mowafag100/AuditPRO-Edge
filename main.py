import io, re, jwt, datetime, time
from fastapi import FastAPI, File, UploadFile, Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import pdfplumber
import anthropic
import os

app = FastAPI(title="AuditPro Edge", version="3.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

SECRET_KEY  = "AUDITPRO_SUPER_SECRET_KEY_2024_XX"
ALGORITHM   = "HS256"
CLAUDE_KEY  = os.environ.get("ANTHROPIC_API_KEY", "")

# ══════════════════════════════════════════════════════
@app.post("/login")
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    expire = datetime.datetime.now(datetime.UTC) + datetime.timedelta(hours=8)
    token  = jwt.encode({"sub": form_data.username, "exp": expire}, SECRET_KEY, algorithm=ALGORITHM)
    return {"access_token": token, "token_type": "bearer"}

# ══════════════════════════════════════════════════════
def extract_pdf_text(content: bytes, max_chars: int = 500) -> str:
    try:
        with pdfplumber.open(io.BytesIO(content)) as pdf:
            if not pdf.pages:
                return "Empty PDF"
            raw = pdf.pages[0].extract_text() or "No text found"
            cleaned = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', ' ', raw)
            return ' '.join(cleaned.split())[:max_chars]
    except Exception as e:
        return f"PDF error: {str(e)[:80]}"

# ══════════════════════════════════════════════════════
def analyze_with_claude(text: str) -> dict:
    if not CLAUDE_KEY:
        return {"score": 55, "source": "no_api_key"}

    client = anthropic.Anthropic(api_key=CLAUDE_KEY)

    prompt = f"""Analyze this contract text and respond with ONLY a JSON object, no markdown, no explanation:

Contract: {text}

Respond with exactly this format:
{{"risk_score": <0-100>, "risk_level": "<LOW|MEDIUM|HIGH>", "summary": "<one sentence>", "risks": ["<risk1>", "<risk2>"], "recommendations": ["<rec1>", "<rec2>"]}}"""

    message = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=300,
        messages=[{"role": "user", "content": prompt}]
    )

    raw = message.content[0].text.strip()
    # تنظيف markdown إذا وُجد
    raw = re.sub(r'```json|```', '', raw).strip()
    data = __import__('json').loads(raw)

    return {
        "score":           min(100, max(0, int(data.get("risk_score", 55)))),
        "risk_level":      data.get("risk_level", "MEDIUM"),
        "summary":         data.get("summary", "Analysis complete."),
        "risks":           data.get("risks", []),
        "recommendations": data.get("recommendations", []),
        "source":          "claude-haiku",
    }

# ══════════════════════════════════════════════════════
@app.post("/analyze-contract")
async def analyze_contract(
    file: UploadFile = File(...),
    token: str = Depends(oauth2_scheme),
):
    start = time.time()

    try:
        jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")

    try:
        content = await file.read()
        text = extract_pdf_text(content, max_chars=500)
    except Exception as e:
        text = f"Extraction failed: {str(e)[:50]}"

    try:
        result = analyze_with_claude(text)
    except Exception as e:
        result = {
            "score": 50, "risk_level": "MEDIUM",
            "summary": f"Fallback analysis. Error: {str(e)[:100]}",
            "risks": ["Analysis engine error"], "recommendations": ["Retry later"],
            "source": "fallback",
        }

    latency = round(time.time() - start, 2)

    # إذا Claude أعطى risk_level، استخدمه — وإلا احسبه من السكور
    score      = result["score"]
    risk_level = result.get("risk_level") or ("HIGH" if score >= 75 else "MEDIUM" if score >= 40 else "LOW")

    if score >= 75:
        risks = result.get("risks") or ["High-risk clauses detected", "Unusual liability terms"]
        recs  = result.get("recommendations") or ["Consult legal professional", "Do not sign without review"]
    elif score >= 40:
        risks = result.get("risks") or ["Moderate risk indicators present"]
        recs  = result.get("recommendations") or ["Review highlighted sections carefully"]
    else:
        risks = result.get("risks") or ["No significant risk patterns detected"]
        recs  = result.get("recommendations") or ["Standard review process is sufficient"]

    return JSONResponse(content={
        "risk_score":      score,
        "risk_level":      risk_level,
        "summary":         result.get("summary", "Analysis complete."),
        "risks":           risks,
        "recommendations": recs,
        "extracted_text":  text[:100] + "..." if len(text) > 100 else text,
        "latency":         f"{latency}s",
        "model_source":    result["source"],
        "ollama_status":   "n/a",
    })

@app.get("/health")
async def health():
    return {"status": "ok", "model": "claude-haiku", "api_key_set": bool(CLAUDE_KEY)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8090, log_level="info")
