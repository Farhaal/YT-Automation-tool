import { useState, useRef } from 'react';
import { Upload, FileText, Loader, MonitorPlay, Sparkles } from 'lucide-react';

export default function CreatorView({ onJobCreated }: { onJobCreated: (id: string) => void }) {
  const [script, setScript] = useState('');
  const [aspectRatio, setAspectRatio] = useState('landscape');
  const [enableMotion, setEnableMotion] = useState(true);
  const [loading, setLoading] = useState(false);
  const fileInput = useRef<HTMLInputElement>(null);

  const handleScriptSubmit = async () => {
    setLoading(true);
    const res = await fetch('http://localhost:8000/generate/script', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ script, aspect_ratio: aspectRatio, enable_motion: enableMotion })
    });
    const data = await res.json();
    setLoading(false);
    onJobCreated(data.job_id);
  };

  const handleFileUpload = async (e: any) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setLoading(true);
    const fd = new FormData();
    fd.append('audio_file', file);
    fd.append('aspect_ratio', aspectRatio);
    fd.append('enable_motion', String(enableMotion));
    try {
      const res = await fetch('http://localhost:8000/generate/audio', {
        method: 'POST',
        body: fd
      });
      const data = await res.json();
      onJobCreated(data.job_id);
    } catch (err) {
      console.error(err);
      alert("Failed to start job from audio. Please ensure backend is running.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-500">
      
      <div className="text-center space-y-3 mb-10 mt-6">
        <h2 className="text-3xl font-extrabold tracking-tight text-gray-900">Create a New Project</h2>
        <p className="text-gray-500 max-w-2xl mx-auto">Upload an audio recording or paste a text script, and we will automatically source assets, sync captions, and assemble a timeline for you.</p>
      </div>

      <div className="bg-white p-5 rounded-xl shadow-sm border border-gray-200 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="bg-blue-50 p-2 rounded-lg">
            <MonitorPlay className="w-5 h-5 text-blue-600" />
          </div>
          <h3 className="text-base font-semibold text-gray-900">Project Settings</h3>
        </div>
        <div className="flex flex-col sm:flex-row items-start sm:items-center gap-6">
          <label className="flex items-center gap-2 text-sm font-medium text-gray-600 cursor-pointer group">
            <input 
              type="checkbox" 
              checked={enableMotion} 
              onChange={e => setEnableMotion(e.target.checked)}
              className="w-4 h-4 text-black rounded border-gray-300 focus:ring-black transition-colors"
            />
            <span className="group-hover:text-black transition-colors">Enable Ken Burns motion</span>
          </label>
          <select 
            value={aspectRatio}
            onChange={e => setAspectRatio(e.target.value)}
            className="border border-gray-200 rounded-md px-3 py-1.5 text-sm font-medium bg-gray-50 hover:bg-gray-100 focus:outline-none focus:ring-2 focus:ring-black transition-all cursor-pointer"
          >
            <option value="landscape">16:9 YouTube (Landscape)</option>
            <option value="portrait">9:16 Shorts (Portrait)</option>
            <option value="square">1:1 Square</option>
          </select>
        </div>
      </div>

      <div className="grid md:grid-cols-2 gap-6">
        <div className="bg-white p-8 rounded-xl shadow-sm border border-gray-200 flex flex-col items-center justify-center min-h-[340px] relative group hover:border-blue-400 transition-colors">
          <div className="absolute inset-0 bg-gradient-to-b from-transparent to-blue-50/50 rounded-xl opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none"></div>
          <div className="bg-blue-50 p-4 rounded-full mb-5 text-blue-600 group-hover:scale-110 transition-transform">
            <Upload className="w-8 h-8" />
          </div>
          <h3 className="text-xl font-bold text-gray-900 mb-2">Upload Audio</h3>
          <p className="text-gray-500 text-center mb-8 text-sm max-w-[240px]">We'll transcribe it with Whisper for perfect word-level timing.</p>
          <input type="file" ref={fileInput} onChange={handleFileUpload} accept="audio/*" className="hidden" />
          <button disabled={loading} onClick={() => fileInput.current?.click()} className="bg-black text-white px-6 py-2.5 rounded-lg font-medium hover:bg-gray-800 disabled:opacity-50 transition-all shadow-sm active:scale-95 flex items-center gap-2 relative z-10">
            {loading ? <Loader className="animate-spin w-4 h-4" /> : null}
            Select Audio File
          </button>
        </div>

        <div className="bg-white p-8 rounded-xl shadow-sm border border-gray-200 flex flex-col min-h-[340px] relative group hover:border-green-400 transition-colors">
          <div className="absolute inset-0 bg-gradient-to-b from-transparent to-green-50/50 rounded-xl opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none"></div>
          
          <div className="flex items-center gap-3 mb-4 relative z-10">
            <div className="bg-green-50 p-2 rounded-lg text-green-600">
              <FileText className="w-5 h-5" />
            </div>
            <h3 className="text-xl font-bold text-gray-900">From Script</h3>
          </div>
          
          <textarea 
            value={script} 
            onChange={e => setScript(e.target.value)} 
            placeholder="Paste your text script here... We will generate AI voiceover first."
            className="flex-1 border border-gray-200 rounded-lg p-4 mb-5 resize-none focus:outline-none focus:ring-2 focus:ring-black text-sm bg-gray-50 focus:bg-white transition-all relative z-10"
          />
          <button disabled={loading || !script.trim()} onClick={handleScriptSubmit} className="bg-black text-white px-6 py-2.5 rounded-lg font-medium hover:bg-gray-800 disabled:opacity-50 self-end flex items-center gap-2 transition-all shadow-sm active:scale-95 relative z-10">
            {loading ? <Loader className="animate-spin w-4 h-4" /> : <Sparkles className="w-4 h-4" />}
            Generate Video
          </button>
        </div>
      </div>
    </div>
  );
}
