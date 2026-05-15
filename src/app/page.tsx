"use client";
import { useState } from 'react';

export default function AIDashboard() {
  const [analysis, setAnalysis] = useState("");
  const [isUploading, setIsUploading] = useState(false);

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setIsUploading(true);
    setAnalysis("");

    const formData = new FormData();
    formData.append("file", file);

    try {
      const response = await fetch("http://localhost:8000/analyze-contract", {
        method: "POST",
        body: formData,
      });

      const reader = response.body?.getReader();
      const decoder = new TextDecoder();

      while (true) {
        const { value, done } = await reader!.read();
        if (done) break;
        const chunk = decoder.decode(value);
        // تنظيف بيانات SSE (data: ...)
        const cleanChunk = chunk.replace(/data: /g, "");
        setAnalysis((prev) => prev + cleanChunk);
      }
    } catch (error) {
      console.error("Error:", error);
    } finally {
      setIsUploading(false);
    }
  };

  return (
    <main className="min-h-screen bg-slate-950 text-slate-50 p-8">
      <div className="max-w-4xl mx-auto space-y-8">
        <header className="border-b border-slate-800 pb-4">
          <h1 className="text-2xl font-bold tracking-tight">AI Contract Analyzer <span className="text-blue-500">v1.0</span></h1>
          <p className="text-slate-400">Enterprise Security & Compliance Dashboard</p>
        </header>

        <div className="grid gap-6">
          {/* Upload Section */}
          <div className="bg-slate-900 border border-slate-800 p-6 rounded-xl">
            <h2 className="text-sm font-medium mb-4 uppercase tracking-widest text-slate-500">Upload Contract (PDF)</h2>
            <input 
              type="file" 
              accept=".pdf" 
              onChange={handleFileUpload}
              className="block w-full text-sm text-slate-500 file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-sm file:font-semibold file:bg-blue-600 file:text-white hover:file:bg-blue-700 cursor-pointer"
            />
          </div>

          {/* AI Analysis Terminal */}
          <div className="bg-black border border-slate-800 rounded-xl overflow-hidden font-mono text-sm">
            <div className="bg-slate-900 px-4 py-2 border-b border-slate-800 flex justify-between items-center">
              <span>Analysis Output</span>
              {isUploading && <span className="animate-pulse text-blue-400">Processing...</span>}
            </div>
            <div className="p-6 min-h-[300px] max-h-[500px] overflow-y-auto whitespace-pre-wrap leading-relaxed text-slate-300">
              {analysis || "Waiting for document upload..."}
            </div>
          </div>
        </div>
      </div>
    </main>
  );
}
