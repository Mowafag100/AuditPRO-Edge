"use client";
import { useState, useEffect, useRef } from 'react';

// إعداد الرابط الأساسي للاتصال بالباك إيند
const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8090';

// ---------- مكونات إضافية ----------

// 1. مقياس المخاطر الدائري
function RiskGauge({ score }: { score: number }) {
  const radius = 56;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (score / 100) * circumference;
  const color = score >= 70 ? 'text-emerald-400' : score >= 40 ? 'text-yellow-400' : 'text-red-500';

  return (
    <div className="flex flex-col items-center">
      <div className="relative w-36 h-36">
        <svg className="w-36 h-36 transform -rotate-90">
          <circle cx="72" cy="72" r={radius} stroke="#27272a" strokeWidth="12" fill="none" />
          <circle
            cx="72" cy="72" r={radius}
            stroke="currentColor"
            strokeWidth="12"
            fill="none"
            strokeDasharray={circumference}
            strokeDashoffset={offset}
            className={`${color} transition-all duration-1000`}
          />
        </svg>
        <div className="absolute inset-0 flex items-center justify-center">
          <span className="text-3xl font-bold text-white">{score}</span>
        </div>
      </div>
      <span className="text-xs text-zinc-500 mt-2">Risk Score</span>
    </div>
  );
}

// ---------- المكون الرئيسي ----------
export default function Home() {
  // الحالات الأساسية
  const [file, setFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);
  const [analysis, setAnalysis] = useState<any>(null);
  const [typedSummary, setTypedSummary] = useState("");
  const [history, setHistory] = useState<any[]>([]);
  const [token, setToken] = useState('');

  // حالات الميزات الجديدة
  const [selectedHistory, setSelectedHistory] = useState<any>(null);     // التحليل المحدد من السجل
  const [chatMessages, setChatMessages] = useState<{ role: 'user' | 'assistant', content: string }[]>([]);
  const [chatInput, setChatInput] = useState('');
  const [chatLoading, setChatLoading] = useState(false);
  const chatEndRef = useRef<HTMLDivElement>(null);

  // ----------------- دوال أساسية -----------------

  const login = async () => {
    try {
      const formData = new URLSearchParams();
      formData.append('username', 'admin');
      formData.append('password', 'admin123');
      const res = await fetch(`${API_BASE}/login`, {
        method: 'POST',
        body: formData
      });
      const data = await res.json();
      setToken(data.access_token);
    } catch (error) {
      console.error("Login Error:", error);
    }
  };

  const fetchHistory = async () => {
    if (!token) return;
    try {
      const res = await fetch(`${API_BASE}/history`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      const data = await res.json();
      setHistory(data);
    } catch (error) {
      console.error("History Error:", error);
    }
  };

  // جلب تفاصيل تحليل محدد من السجل
  const fetchHistoryDetail = async (id: number) => {
    if (!token) return;
    try {
      const res = await fetch(`${API_BASE}/history/${id}`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (!res.ok) throw new Error('Not found');
      const data = await res.json();
      setSelectedHistory(data);
      // عرض الملخص بتأثير الكتابة
      if (data.summary) typeEffect(data.summary);
    } catch (error) {
      console.error("Fetch history detail error:", error);
    }
  };

  // تأثير الكتابة (Typewriter)
  const typeEffect = (text: string) => {
    let i = 0;
    setTypedSummary("");
    const timer = setInterval(() => {
      setTypedSummary((prev) => prev + text.charAt(i));
      i++;
      if (i >= text.length) clearInterval(timer);
    }, 25);
    return () => clearInterval(timer);
  };

  // تحليل ملف جديد
  const analyze = async () => {
    if (!file || !token) return;
    setLoading(true);
    setAnalysis(null);
    setSelectedHistory(null); // إلغاء تحديد أي تحليل سابق
    const formData = new FormData();
    formData.append('file', file);
    try {
      const res = await fetch(`${API_BASE}/analyze-contract`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}` },
        body: formData
      });
      const data = await res.json();
      setAnalysis(data);
      if (data.summary) typeEffect(data.summary);
      await fetchHistory();
    } catch (error) {
      console.error("Analysis Error:", error);
    } finally {
      setLoading(false);
    }
  };

  // إرسال رسالة إلى الشات
  const sendChatMessage = async () => {
    if (!chatInput.trim() || !token) return;
    const userMsg = chatInput.trim();
    setChatInput('');
    setChatMessages(prev => [...prev, { role: 'user', content: userMsg }]);

    // تجميع السياق (نص المستند + التحليل الحالي)
    const context = analysis?.summary + '\n' + (analysis?.risks?.join(', ') || '') + (analysis?.recommendations?.join(', ') || '');
    if (!context) {
      setChatMessages(prev => [...prev, { role: 'assistant', content: 'Please upload and analyze a document first.' }]);
      return;
    }

    setChatLoading(true);
    try {
      const formData = new URLSearchParams();
      formData.append('message', userMsg);
      formData.append('context', context.slice(0, 2000)); // تقطيع للحد الطول
      const res = await fetch(`${API_BASE}/chat`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}` },
        body: formData
      });
      const data = await res.json();
      setChatMessages(prev => [...prev, { role: 'assistant', content: data.response || 'No response' }]);
    } catch (error) {
      console.error('Chat error:', error);
      setChatMessages(prev => [...prev, { role: 'assistant', content: 'Sorry, an error occurred.' }]);
    } finally {
      setChatLoading(false);
    }
  };

  // تحميل تقرير PDF (مبدئي)
  const downloadReport = () => {
    if (!analysis) return;
    const content = `
AuditPRO Edge Report
-------------------
Filename: ${analysis.filename || 'Unknown'}
Risk Score: ${analysis.score || analysis.risk_score || 'N/A'}
Risk Level: ${analysis.risk_level || 'N/A'}
Summary: ${analysis.summary || 'N/A'}
Risks: ${analysis.risks?.join('\n  - ') || 'None'}
Recommendations: ${analysis.recommendations?.join('\n  - ') || 'None'}
Source: ${analysis.source || 'Unknown'}
Latency: ${analysis.latency || 'N/A'}
    `;
    const blob = new Blob([content], { type: 'application/pdf' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `AuditReport_${new Date().toISOString().slice(0,10)}.pdf`;
    a.click();
    URL.revokeObjectURL(url);
  };

  // ----------------- تأثيرات (Effects) -----------------

  useEffect(() => { login(); }, []);
  useEffect(() => { if (token) fetchHistory(); }, [token]);

  // تمرير الشات للأسفل عند إضافة رسالة جديدة
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [chatMessages]);

  // ----------------- عرض الواجهة -----------------

  return (
    <div className="min-h-screen bg-black text-white p-6 font-sans">
      <div className="max-w-6xl mx-auto">
        {/* الرأس */}
        <header className="flex justify-between items-center mb-10 border-b border-zinc-800 pb-6">
          <h1 className="text-xl font-bold bg-gradient-to-r from-emerald-400 to-blue-500 bg-clip-text text-transparent">AuditPRO Edge v2</h1>
          <div className="flex items-center gap-4">
            <span className="px-3 py-1 bg-zinc-900 border border-zinc-800 rounded-full text-[10px] text-zinc-500 font-mono">STATUS: LOCAL_AI_ACTIVE</span>
            {analysis && (
              <button
                onClick={downloadReport}
                className="px-3 py-1 bg-zinc-800 hover:bg-zinc-700 text-xs rounded-lg transition"
              >
                ⬇️ Report
              </button>
            )}
          </div>
        </header>

        {/* بطاقات المعلومات السريعة */}
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

        {/* المحتوى الرئيسي */}
        <main className="grid md:grid-cols-12 gap-6">
          {/* العمود الأيسر: رفع الملف والتحليل */}
          <div className="md:col-span-7 space-y-6">
            <div className="bg-zinc-900 border border-zinc-800 rounded-2xl p-6 text-center border-dashed">
              <input type="file" onChange={(e) => setFile(e.target.files?.[0] || null)} className="hidden" id="file-up" />
              <label htmlFor="file-up" className="cursor-pointer block">
                <p className="text-zinc-500 text-sm">{file ? file.name : "📎 Select Legal PDF"}</p>
              </label>
              <button onClick={analyze} disabled={loading || !file} className="mt-6 w-full py-3 bg-emerald-600 hover:bg-emerald-500 text-white rounded-lg transition-all text-sm font-bold">
                {loading ? "⏳ Processing..." : "🚀 Run Analysis"}
              </button>
            </div>

            {/* عرض مقياس المخاطر والتحليل */}
            {analysis && (
              <div className="bg-zinc-900 border border-zinc-800 rounded-2xl p-6 animate-in fade-in duration-700">
                <div className="flex flex-col md:flex-row items-start md:items-center gap-6">
                  <RiskGauge score={analysis.score || analysis.risk_score || 50} />
                  <div className="flex-1">
                    <h3 className="text-sm font-bold mb-2">Analysis Results</h3>
                    <p className="text-zinc-400 text-sm leading-relaxed min-h-[60px]">
                      {typedSummary}
                      <span className="inline-block w-1.5 h-4 bg-emerald-500 ml-1 animate-pulse"></span>
                    </p>
                  </div>
                </div>
                
                <div className="grid grid-cols-2 gap-4 mt-6 border-t border-zinc-800 pt-6">
                  <div>
                    <h4 className="text-[10px] text-red-400 uppercase mb-2">⚠️ Risks</h4>
                    {analysis.risks?.map((r:any, i:number) => <p key={i} className="text-[11px] text-zinc-500 mb-1">• {r}</p>)}
                    {!analysis.risks?.length && <p className="text-[11px] text-zinc-600">None detected</p>}
                  </div>
                  <div>
                    <h4 className="text-[10px] text-emerald-400 uppercase mb-2">✅ Actions</h4>
                    {analysis.recommendations?.map((r:any, i:number) => <p key={i} className="text-[11px] text-zinc-500 mb-1">✓ {r}</p>)}
                    {!analysis.recommendations?.length && <p className="text-[11px] text-zinc-600">No recommendations</p>}
                  </div>
                </div>
                <div className="mt-4 text-right">
                  <span className="text-[10px] text-zinc-600">Source: {analysis.source || 'Unknown'}</span>
                </div>
              </div>
            )}

            {/* عرض التحليل المحدد من السجل */}
            {selectedHistory && !analysis && (
              <div className="bg-zinc-900 border border-zinc-800 rounded-2xl p-6 animate-in fade-in duration-700">
                <div className="flex justify-between items-start">
                  <h3 className="text-sm font-bold mb-2">📄 {selectedHistory.filename}</h3>
                  <button onClick={() => setSelectedHistory(null)} className="text-xs text-zinc-500 hover:text-white">✕</button>
                </div>
                <div className="flex flex-col md:flex-row items-start md:items-center gap-6">
                  <RiskGauge score={selectedHistory.risk_score || 50} />
                  <div className="flex-1">
                    <p className="text-zinc-400 text-sm leading-relaxed min-h-[60px]">
                      {typedSummary || selectedHistory.summary}
                      <span className="inline-block w-1.5 h-4 bg-emerald-500 ml-1 animate-pulse"></span>
                    </p>
                  </div>
                </div>
                <div className="text-right mt-2">
                  <span className="text-[10px] text-zinc-600">Latency: {selectedHistory.latency}s</span>
                </div>
              </div>
            )}
          </div>

          {/* العمود الأيمن: السجل والشات */}
          <div className="md:col-span-5 space-y-6">
            {/* سجل التحليلات السابقة */}
            <div className="bg-zinc-900/20 border border-zinc-800 rounded-2xl p-5">
              <h3 className="text-xs text-zinc-500 mb-4 uppercase">📋 Recent Audits</h3>
              <div className="space-y-2 max-h-60 overflow-y-auto pr-1">
                {history.map((h:any) => (
                  <div
                    key={h.id}
                    onClick={() => fetchHistoryDetail(h.id)}
                    className="p-3 border border-zinc-800 rounded-lg bg-black/40 hover:bg-zinc-800/40 cursor-pointer transition"
                  >
                    <p className="text-[11px] truncate text-zinc-300">{h.filename}</p>
                    <div className="flex justify-between items-center mt-1">
                      <span className={`text-[9px] px-2 py-0.5 rounded ${h.risk_score >= 70 ? 'bg-emerald-900/50 text-emerald-400' : h.risk_score >= 40 ? 'bg-yellow-900/50 text-yellow-400' : 'bg-red-900/50 text-red-400'}`}>
                        {h.risk_score}%
                      </span>
                      <span className="text-[9px] text-zinc-600">{new Date(h.date).toLocaleDateString()}</span>
                    </div>
                  </div>
                ))}
                {!history.length && <p className="text-[11px] text-zinc-600 text-center py-4">No audits yet</p>}
              </div>
            </div>

            {/* شات ذكي */}
            <div className="bg-zinc-900/20 border border-zinc-800 rounded-2xl p-4">
              <h3 className="text-xs text-zinc-500 mb-3 uppercase">💬 Chat with AI</h3>
              <div className="h-40 overflow-y-auto space-y-2 mb-3 pr-1 text-xs">
                {chatMessages.map((msg, idx) => (
                  <div key={idx} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                    <div className={`max-w-[85%] px-3 py-2 rounded-lg ${msg.role === 'user' ? 'bg-emerald-800/60 text-emerald-100' : 'bg-zinc-800/80 text-zinc-300'}`}>
                      {msg.content}
                    </div>
                  </div>
                ))}
                {chatLoading && (
                  <div className="flex justify-start">
                    <div className="bg-zinc-800/80 px-3 py-2 rounded-lg text-zinc-400">Typing...</div>
                  </div>
                )}
                <div ref={chatEndRef} />
              </div>
              <div className="flex gap-2">
                <input
                  type="text"
                  value={chatInput}
                  onChange={(e) => setChatInput(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && sendChatMessage()}
                  placeholder="Ask about the contract..."
                  className="flex-1 bg-black border border-zinc-800 rounded-lg px-3 py-2 text-xs text-white placeholder-zinc-600 focus:outline-none focus:border-emerald-500"
                />
                <button
                  onClick={sendChatMessage}
                  disabled={!chatInput.trim() || chatLoading}
                  className="px-4 py-2 bg-emerald-600 hover:bg-emerald-500 disabled:bg-zinc-700 text-white text-xs rounded-lg transition"
                >
                  Send
                </button>
              </div>
            </div>
          </div>
        </main>
      </div>
    </div>
  );
}