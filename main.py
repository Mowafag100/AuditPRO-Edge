import io, json, re, jwt, datetime, hashlib, sqlite3, time, os
from fastapi import FastAPI, File, UploadFile, Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
import pdfplumber
from openai import AsyncOpenAI

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")
client = AsyncOpenAI(base_url="http://localhost:11434/v1", api_key="ollama", timeout=120.0)

SECRET_KEY = "SUPER_SECRET_KEY_123"
ALGORITHM = "HS256"
USER_DB = {"admin": hashlib.sha256("admin123".encode()).hexdigest()}

def init_db():
    conn = sqlite3.connect("platform.db")
    cursor = conn.cursor()
    cursor.execute("""CREATE TABLE IF NOT EXISTS history (
        id INTEGER PRIMARY KEY AUTOINCREMENT, 
        username TEXT, filename TEXT, risk_score INTEGER, 
        summary TEXT, risks TEXT, recommendations TEXT, 
        engine TEXT, latency REAL, timestamp DATETIME)""")
    conn.commit()
    conn.close()

init_db()

@app.post("/login")
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    user_pw_hash = USER_DB.get(form_data.username)
    if not user_pw_hash or hashlib.sha256(form_data.password.encode()).hexdigest() != user_pw_hash:
        raise HTTPException(status_code=401, detail="Unauthorized")
    expire = datetime.datetime.now(datetime.UTC) + datetime.timedelta(minutes=60)
    token = jwt.encode({"sub": form_data.username, "exp": expire}, SECRET_KEY, algorithm=ALGORITHM)
    return {"access_token": token, "token_type": "bearer"}

@app.post("/analyze-contract")
async def analyze_contract(file: UploadFile = File(...), token: str = Depends(oauth2_scheme)):
    start_time = time.time()
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        content = await file.read()
        text = ""
        with pdfplumber.open(io.BytesIO(content)) as pdf:
            for page in pdf.pages[:2]: # قراءة أول صفحتين لدقة أعلى
                text += page.extract_text() or ""
        
        text = text[:1200] # زيادة حجم السياق
        
        PROMPT = "JSON ONLY: {\"risk_score\": int, \"summary\": \"str\", \"risks\": [\"str\"], \"recommendations\": [\"str\"]}"
        
        response = await client.chat.completions.create(
            model="tinyllama",
            messages=[
                {"role": "system", "content": "You are a legal AI. Output ONLY valid JSON."},
                {"role": "user", "content": f"{PROMPT}\n\nContract text: {text}"}
            ],
            temperature=0.2
        )
        
        raw = response.choices[0].message.content
        json_match = re.search(r'\{.*\}', raw, re.DOTALL)
        res_data = json.loads(json_match.group(0)) if json_match else {"risk_score": 0, "summary": "Failed to parse AI output"}
        
        latency = round(time.time() - start_time, 2)
        engine_info = "TinyLlama 1.1B (Optimized)"
        
        conn = sqlite3.connect("platform.db")
        cursor = conn.cursor()
        cursor.execute("INSERT INTO history (username, filename, risk_score, summary, risks, recommendations, engine, latency, timestamp) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                       (payload.get("sub"), file.filename, res_data.get('risk_score', 0), res_data.get('summary', ''), 
                        json.dumps(res_data.get('risks', [])), json.dumps(res_data.get('recommendations', [])), 
                        engine_info, latency, datetime.datetime.now()))
        conn.commit()
        conn.close()
        
        return {**res_data, "engine": engine_info, "latency": f"{latency}s"}
    except Exception as e:
        return {"risk_score": 0, "summary": f"System Error: {str(e)}"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8090)
