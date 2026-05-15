import io, re, jwt, datetime, time, json
from fastapi import FastAPI, File, UploadFile, Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import pdfplumber
import httpx
import os

app = FastAPI(title="AuditPro Edge", version="3.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")
SECRET_KEY  = "AUDITPRO_SUPER_SECRET_KEY_2024_XX"
ALGORITHM   = "HS256"
GEMINI_KEY  = os.environ.get("GEMINI_API_KEY", "")
GEMINI_URL  = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"

@app.post("/login")
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    expire = datetime.datetime.now(datetime.UTC) + datetime.timedelta(hours=8)
    token  = jwt.encode({"sub": form_data.username, "exp": expire}, SECRET_KEY, algorithm=ALGORITHM)
    return {"access_token": token, "token_type": "bearer"}

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

async def analyze_with_gemini(text: str) -> dict:
    if not GEMINI_KEY:
        return {"score": 55, "risk_level": "MEDIUM", "summary": "No API key set.",
                "risks": ["API key missing"], "recommendations": ["Set GEMINI_API_KEY"], "source": "no_key"}

    prompt = f"""Analyze this contract and reply ONLY with a JSON object, no markdown:

Contract: {text}

Reply with exactly:
{{"risk_score": <0-100>, "risk_level": "<LOW|MEDIUM|HIGH>", "summary": "<one sentence>", "risks": ["<risk1>", "<risk2>"], "recommendations": ["<rec1>", "<rec2>"]}}"""

    async with httpx.AsyncClient(timeout=30.0) as client:
        res = await client.post(
            f"{GEMINI_URL}?key={GEMINI_KEY}",
            json={"contents": [{"parts": [{"text": prompt}]}]}
        )
        res.raise_for_status()
        raw = res.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
        raw = re.sub(r'```json|```', '', raw).strip()
        data = json.loads(raw)
        return {
            "score":           min(100, max(0, int(data.get("risk_score", 55)))),
            "risk_level":      data.get("risk_level", "MEDIUM"),
            "summary":         data.get("summary", "Analysis complete."),
            "risks":           data.get("risks", []),
            "recommendations": data.get("recommendations", []),
            "source":          "gemini-2.0-flash",
        }

@app.post("/analyze-contract")
async def analyze_contract(file: UploadFile = File(...), token: str = Depends(oauth2_scheme)):
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
        result = await analyze_with_gemini(text)
    except Exception as e:
        result = {"score": 50, "risk_level": "MEDIUM",
                  "summary": f"Fallback. Error: {str(e)[:80]}",
                  "risks": ["Analysis error"], "recommendations": ["Retry"], "source": "fallback"}

    score      = result["score"]
    risk_level = result.get("risk_level") or ("HIGH" if score >= 75 else "MEDIUM" if score >= 40 else "LOW")

    return JSONResponse(content={
        "risk_score":      score,
        "risk_level":      risk_level,
        "summary":         result.get("summary", "Analysis complete."),
        "risks":           result.get("risks", []),
        "recommendations": result.get("recommendations", []),
        "extracted_text":  text[:100] + "..." if len(text) > 100 else text,
        "latency":         f"{round(time.time() - start, 2)}s",
        "model_source":    result["source"],
        "ollama_status":   "n/a",
    })

@app.get("/health")
async def health():
    return {"status": "ok", "model": "gemini-2.0-flash", "api_key_set": bool(GEMINI_KEY)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8090, log_level="info")
