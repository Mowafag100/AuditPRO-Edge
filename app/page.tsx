"use client";
import { useState, useEffect } from 'react';

export default function Home() {
  const [file, setFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);
  const [analysis, setAnalysis] = useState<any>(null);
  const [typedSummary, setTypedSummary] = useState("");
  const [history, setHistory] = useState([]);
  const [token, setToken] = useState('');

  const login = async () => {
    const formData = new URLSearchParams();
    formData.append('username', 'admin');
    formData.append('password', 'admin123');
    const res = await fetch('http://127.0.0.1:8090/login', { method: 'POST', body: formData });
    const data = await res.json();
    setToken(data.access_token);
  };

  const fetchHistory = async () => {
    if (!token) return;
    const res = await fetch('http://127.0.0.1:8090/history', {
      headers: { 'Authorization': `Bearer ${token}` }
    });
    const data = await res.json();
    setHistory(data);
  };

  const typeEffect = (text: string) => {
    let i = 0;
    setTypedSummary("");
    const timer = setInterval(() => {
      setTypedSummary((prev) => prev + text.charAt(i));
      i++;
      if (i >= text.length) clearInterval(timer);
    }, 25);
  };

  const analyze = async () => {
    if (!file || !token) return;
    setLoading(true);
    setAnalysis(null);
    const formData = new FormData();
    formData.append('file', file);
    const res = await fetch('http://127.0.0.1:8090/analyze-contract', {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${token}` },
      body: formData
    });
    const data = await res.json();
    setAnalysis(data);
    setLoading(false);
    if (data.summary) typeEffect(data.summary);
    fetchHistory();
  };

  useEffect(() => { login(); }, []);
  useEffect(() => { if (token) fetchHistory(); }, [token]);

  return (
    <div className="min-h-screen bg-black text-white p-6 font-sans">
      <div className="max-w-5xl mx-auto">
        <header className="flex justify-between items-center mb-10 border-b border-zinc-800 pb-6">
          <h1 className="text-xl font-bold bg-gradient-to-r from-emerald-400 to-blue-500 bg-clip-text text-transparent">AuditPRO Edge v2</h1>
          <div className="px-3 py-1 bg-zinc-900 border border-zinc-800 rounded-full text-[10px] text-zinc-500 font-mono">STATUS: LOCAL_AI_ACTIVE</div>
        </header>

        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
          {[
            { label: 'Latency', val: analysis?.latency || 'Ready' },
            { label: 'Security', val: 'AES-256/JWT' },
            { label: 'Memory', val: 'Optimized' },
            { label: 'Engine', val: 'TinyLlama 1.1B' }
          ].map((m, i) => (
            <div key={i} className="bg-zinc-900/40 border border-zinc-800 p-4 rounded-xl">
              <p className="text-[9px] uppercase text-zinc-500 mb-1">{m.label}</p>
              <p className="text-xs font-mono text-white">{m.val}</p>
            </div>
          ))}
        </div>

        <main className="grid md:grid-cols-3 gap-8">
          <div className="md:col-span-2 space-y-6">
            <div className="bg-zinc-900 border border-zinc-800 rounded-2xl p-8 text-center border-dashed">
              <input type="file" onChange={(e) => setFile(e.target.files?.[0] || null)} className="hidden" id="file-up" />
              <label htmlFor="file-up" className="cursor-pointer block">
                <p className="text-zinc-500 text-sm">{file ? file.name : "Select Legal PDF"}</p>
              </label>
              <button onClick={analyze} disabled={loading || !file} className="mt-6 w-full py-3 bg-emerald-600 hover:bg-emerald-500 text-white rounded-lg transition-all text-sm font-bold">
                {loading ? "Processing via Local LLM..." : "Run Analysis"}
              </button>
            </div>

            {analysis && (
              <div className="bg-zinc-900 border border-zinc-800 rounded-2xl p-6 animate-in fade-in duration-700">
                <div className="flex justify-between mb-4">
                  <h3 className="text-sm font-bold">Analysis Results</h3>
                  <span className="text-emerald-400 font-mono text-sm">{analysis.risk_score}% Risk</span>
                </div>
                <p className="text-zinc-400 text-sm leading-relaxed min-h-[60px]">
                  {typedSummary}
                  <span className="inline-block w-1.5 h-4 bg-emerald-500 ml-1 animate-pulse"></span>
                </p>
                
                <div className="grid grid-cols-2 gap-4 mt-6 border-t border-zinc-800 pt-6">
                  <div>
                    <h4 className="text-[10px] text-red-400 uppercase mb-2">Risks</h4>
                    {analysis.risks?.map((r:any, i:number) => <p key={i} className="text-[11px] text-zinc-500 mb-1">• {r}</p>)}
                  </div>
                  <div>
                    <h4 className="text-[10px] text-emerald-400 uppercase mb-2">Actions</h4>
                    {analysis.recommendations?.map((r:any, i:number) => <p key={i} className="text-[11px] text-zinc-500 mb-1">✓ {r}</p>)}
                  </div>
                </div>
              </div>
            )}
          </div>

          <div className="bg-zinc-900/20 border border-zinc-800 rounded-2xl p-5">
            <h3 className="text-xs text-zinc-500 mb-4 uppercase">Recent Audits</h3>
            <div className="space-y-3">
              {history.map((h:any, i) => (
                <div key={i} className="p-3 border border-zinc-800 rounded-lg bg-black/40">
                  <p className="text-[11px] truncate text-zinc-300">{h.filename}</p>
                  <p className="text-[9px] text-zinc-600 mt-1">{h.date}</p>
                </div>
              ))}
            </div>
          </div>
        </main>
      </div>
    </div>
  );
}
