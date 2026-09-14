import { useState, useRef } from 'react';
import { Upload, FileText, Loader, MonitorPlay } from 'lucide-react';

export default function CreatorView({ onJobCreated }: { onJobCreated: (id: string) => void }) {
  const [script, setScript] = useState('');
  const [aspectRatio, setAspectRatio] = useState('landscape');
  const [loading, setLoading] = useState(false);
  const fileInput = useRef<HTMLInputElement>(null);

  const handleScriptSubmit = async () => {
    setLoading(true);
    const res = await fetch('http://localhost:8000/generate/script', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ script, aspect_ratio: aspectRatio })
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
    const res = await fetch('http://localhost:8000/generate/audio', {
      method: 'POST',
      body: fd
    });
    const data = await res.json();
    setLoading(false);
    onJobCreated(data.job_id);
  };

  return (
    <div className="space-y-6">
      <div className="bg-white p-4 rounded shadow flex items-center justify-between border-l-4 border-indigo-500">
        <div className="flex items-center gap-3">
          <MonitorPlay className="w-6 h-6 text-indigo-500" />
          <h2 className="text-lg font-bold">Video Format</h2>
        </div>
        <select 
          value={aspectRatio}
          onChange={e => setAspectRatio(e.target.value)}
          className="border border-gray-300 rounded px-4 py-2 font-medium bg-gray-50 focus:outline-none focus:ring-2 focus:ring-indigo-500"
        >
          <option value="landscape">16:9 YouTube (Landscape)</option>
          <option value="portrait">9:16 Shorts (Portrait)</option>
          <option value="square">1:1 Square</option>
        </select>
      </div>

      <div className="grid md:grid-cols-2 gap-8">
        <div className="bg-white p-6 rounded shadow flex flex-col items-center justify-center min-h-[300px] border-2 border-dashed border-gray-300">
          <Upload className="w-12 h-12 text-blue-500 mb-4" />
          <h2 className="text-xl font-bold mb-2">Upload Narration Audio</h2>
          <p className="text-gray-500 text-center mb-6">Start with real audio. We'll transcribe it for perfect timing.</p>
          <input type="file" ref={fileInput} onChange={handleFileUpload} accept="audio/*" className="hidden" />
          <button disabled={loading} onClick={() => fileInput.current?.click()} className="bg-blue-600 text-white px-6 py-2 rounded font-medium hover:bg-blue-700 disabled:opacity-50">
            Select Audio File
          </button>
        </div>

        <div className="bg-white p-6 rounded shadow flex flex-col min-h-[300px]">
          <div className="flex items-center gap-2 mb-4">
            <FileText className="text-green-500" />
            <h2 className="text-xl font-bold">Or generate from Script</h2>
          </div>
          <textarea 
            value={script} 
            onChange={e => setScript(e.target.value)} 
            placeholder="Paste your script here... We will generate TTS audio first, then transcribe it for timing."
            className="flex-1 border rounded p-3 mb-4 resize-none focus:outline-none focus:ring-2 focus:ring-green-500"
          />
          <button disabled={loading || !script.trim()} onClick={handleScriptSubmit} className="bg-green-600 text-white px-6 py-2 rounded font-medium hover:bg-green-700 disabled:opacity-50 self-end flex items-center gap-2">
            {loading ? <Loader className="animate-spin w-4 h-4" /> : null}
            Generate
          </button>
        </div>
      </div>
    </div>
  );
}
