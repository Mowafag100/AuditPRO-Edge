"use client";
import { useState, useEffect } from "react";

export default function Home() {
  const [token, setToken] = useState(null);
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [data, setData] = useState(null);
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    const savedToken = localStorage.getItem("token");
    if (savedToken) { setToken(savedToken); fetchHistory(savedToken); }
  }, []);

  const fetchHistory = async (t) => {
    try {
      const res = await fetch("http://127.0.0.1:8090/history", { headers: { "Authorization": `Bearer ${t}` } });
      const result = await res.json();
      setHistory(Array.isArray(result) ? result : []);
    } catch (e) { setHistory([]); }
  };

  const handleLogin = async (e) => {
    e.preventDefault();
    const formData = new URLSearchParams();
    formData.append("username", username); formData.append("password", password);
    const res = await fetch("http://127.0.0.1:8090/login", { method: "POST", body: formData });
    const result = await res.json();
    if (result.access_token) {
      setToken(result.access_token);
      localStorage.setItem("token", result.access_token);
      fetchHistory(result.access_token);
    } else { alert("Login Failed"); }
  };

  const processFile = async (e) => {
    const file = e.target.files[0]; if (!file) return;
    setLoading(true);
    const formData = new FormData(); formData.append("file", file);
    try {
      const res = await fetch("http://127.0.0.1:8090/analyze-contract", {
        method: "POST",
        headers: { "Authorization": `Bearer ${token}` },
        body: formData
      });
      const result = await res.json();
      setData(result);
      fetchHistory(token);
    } catch (err) {
      alert("Server connection error");
    } finally {
      setLoading(false); // هذا السطر يضمن توقف التحميل مهما حدث
    }
  };

  if (!token) {
    return (
      <div className="min-h-screen bg-[#0a0f1a] flex items-center justify-center p-6 text-left">
        <form onSubmit={handleLogin} className="bg-[#151c2c] p-10 rounded-3xl border border-slate-800 w-full max-w-sm space-y-6">
          <h2 className="text-3xl font-black text-center text-blue-500 uppercase">Audit AI</h2>
          <input type="text" placeholder="Username" onChange={(e)=>setUsername(e.target.value)} className="w-full p-4 bg-[#0d121f] rounded-xl border border-slate-700 text-white outline-none" />
          <input type="password" placeholder="Password" onChange={(e)=>setPassword(e.target.value)} className="w-full p-4 bg-[#0d121f] rounded-xl border border-slate-700 text-white outline-none" />
          <button type="submit" className="w-full bg-blue-600 text-white font-bold py-4 rounded-xl">SIGN IN</button>
        </form>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#0a0f1a] text-slate-200 p-6 md:p-12 text-left">
      <div className="max-w-6xl mx-auto flex justify-between items-center mb-12">
        <h1 className="text-3xl font-black text-white italic tracking-tighter uppercase">Audit <span className="text-blue-500">PRO</span></h1>
        <button onClick={() => {setToken(null); localStorage.removeItem("token");}} className="text-red-500 text-xs font-bold uppercase">Logout</button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-10">
        <div className="lg:col-span-2">
          <div className="bg-[#151c2c] rounded-[2.5rem] border border-slate-800 p-10 shadow-2xl relative">
            <div className="relative border-2 border-dashed border-slate-700 p-16 rounded-[2rem] text-center bg-[#0d121f] group cursor-pointer">
              <input type="file" onChange={processFile} className="absolute inset-0 opacity-0 cursor-pointer" />
              <p className="text-lg font-medium text-slate-400">Upload Contract for AI Analysis</p>
            </div>

            {loading && <div className="mt-10 text-center text-blue-400 animate-pulse font-bold uppercase">Analyzing Logic...</div>}

            {data && !loading && (
              <div className="mt-12 space-y-8 animate-in fade-in duration-500">
                <div className="flex justify-between items-center p-8 bg-[#0a0f1a] rounded-[1.5rem] border border-slate-800">
                   <div>
                     <span className="text-[10px] text-slate-500 block mb-2 uppercase tracking-[0.3em]">Risk Index</span>
                     <span className={`text-6xl font-black ${data.risk_score > 50 ? 'text-red-500' : 'text-emerald-500'}`}>{data.risk_score}%</span>
                   </div>
                   <div className="max-w-md">
                     <p className="text-xs text-slate-400 leading-relaxed">{data.summary}</p>
                   </div>
                </div>
              </div>
            )}
          </div>
        </div>

        <div className="bg-[#151c2c] rounded-[2.5rem] border border-slate-800 p-8 shadow-xl">
          <h3 className="text-xs font-black text-slate-500 mb-8 uppercase tracking-[0.4em]">Audit History</h3>
          <div className="space-y-4 max-h-[600px] overflow-y-auto">
            {history.map((item, index) => (
              <div key={index} className="p-5 bg-[#0d121f] rounded-2xl border border-slate-800">
                <div className="flex justify-between items-center mb-2">
                  <span className="text-xs font-bold text-slate-300">{item.filename}</span>
                  <span className="text-xs font-black text-emerald-500">{item.risk_score}%</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
