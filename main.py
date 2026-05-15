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
            text = pdf.pages[0].extract_text()[:500] if pdf.pages else ""
        
        PROMPT = "JSON ONLY: {\"risk_score\": int, \"summary\": \"str\", \"risks\": [\"str\"], \"recommendations\": [\"str\"]}"
        
        response = await client.chat.completions.create(
            model="tinyllama",
            messages=[{"role": "system", "content": PROMPT}, {"role": "user", "content": text}],
            temperature=0.1
        )
        
        raw = response.choices[0].message.content
        json_match = re.search(r'\{.*\}', raw, re.DOTALL)
        res_data = json.loads(json_match.group(0)) if json_match else {"risk_score": 0, "summary": "Analysis failed"}
        
        latency = round(time.time() - start_time, 2)
        engine_info = "TinyLlama 1.1B (Edge)"
        
        conn = sqlite3.connect("platform.db")
        cursor = conn.cursor()
        cursor.execute("INSERT INTO history (username, filename, risk_score, summary, risks, recommendations, engine, latency, timestamp) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                       (payload.get("sub"), file.filename, res_data.get('risk_score', 0), res_data.get('summary', ''), 
                        json.dumps(res_data.get('risks', [])), json.dumps(res_data.get('recommendations', [])), 
                        engine_info, latency, datetime.datetime.now()))
        conn.commit()
        conn.close()
        
        return {**res_data, "engine": engine_info, "latency": f"{latency}s", "runtime": "Ollama/Termux"}
    except Exception as e:
        print(f"Error: {e}")
        return {"risk_score": 0, "summary": f"System Error: {str(e)}"}

@app.get("/history")
async def get_history(token: str = Depends(oauth2_scheme)):
    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    conn = sqlite3.connect("platform.db")
    cursor = conn.cursor()
    cursor.execute("SELECT filename, risk_score, summary, risks, recommendations, engine, latency, timestamp FROM history WHERE username = ? ORDER BY id DESC", (payload.get("sub"),))
    rows = cursor.fetchall()
    conn.close()
    return [{"filename": r[0], "risk_score": r[1], "summary": r[2], "risks": json.loads(r[3]), "recommendations": json.loads(r[4]), "engine": r[5], "latency": r[6], "date": r[7]} for r in rows]

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8090)
