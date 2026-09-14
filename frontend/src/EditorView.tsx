import { useState, useEffect } from 'react';
import { Loader, RefreshCw, AlertTriangle, ArrowLeftRight } from 'lucide-react';

export default function EditorView({ jobId }: { jobId: string }) {
  const [job, setJob] = useState<any>(null);
  const [timeline, setTimeline] = useState<any>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    fetch(`http://localhost:8000/jobs/${jobId}`).then(r => r.json()).then(setJob);

    const ws = new WebSocket(`ws://localhost:8000/jobs/${jobId}/ws`);
    ws.onmessage = (e) => {
      const data = JSON.parse(e.data);
      setJob(data);
      if (data.status === 'COMPLETED' && data.timeline_path) {
        loadTimeline();
      }
    };
    
    // Fallback polling
    const interval = setInterval(() => {
      fetch(`http://localhost:8000/jobs/${jobId}`).then(r => r.json()).then(data => {
        setJob(prev => {
          if (data.status === 'COMPLETED' || data.status === 'ERROR') {
             clearInterval(interval);
          }
          if (prev?.status === 'COMPLETED' || prev?.status === 'ERROR') return prev;
          if (data.status === 'COMPLETED' && data.timeline_path && prev?.status !== 'COMPLETED') {
            loadTimeline();
          }
          return data;
        });
      });
    }, 2000);

    return () => {
      ws.close();
      clearInterval(interval);
    };
  }, [jobId]);

  const loadTimeline = () => {
    fetch(`http://localhost:8000/jobs/${jobId}/timeline`)
      .then(r => r.json())
      .then(setTimeline);
  };

  const saveTimeline = async () => {
    setLoading(true);
    await fetch(`http://localhost:8000/jobs/${jobId}/timeline`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(timeline)
    });
    // Request re-render
    await fetch(`http://localhost:8000/jobs/${jobId}/render`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ draft_mode: true })
    });
    setLoading(false);
  };

  const renderFinal = async () => {
    setLoading(true);
    await fetch(`http://localhost:8000/jobs/${jobId}/timeline`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(timeline)
    });
    // Request final render
    await fetch(`http://localhost:8000/jobs/${jobId}/render`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ draft_mode: false })
    });
    setLoading(false);
  };

  const [exporting, setExporting] = React.useState(false);

  const exportProject = async () => {
    setExporting(true);
    try {
      await fetch(`http://localhost:8000/jobs/${jobId}/timeline`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(timeline)
      });
      const resp = await fetch(`http://localhost:8000/jobs/${jobId}/export`, {
        method: 'POST'
      });
      const data = await resp.json();
      if (data.export_path) {
        window.open(`http://localhost:8000/media?path=${encodeURIComponent(data.export_path)}`, '_blank');
      }
    } finally {
      setExporting(false);
    }
  };

  const swapBackup = (sceneIndex: number) => {
    const t = { ...timeline };
    const s = t.scenes[sceneIndex];
    if (s.backup_asset) {
      const temp = s.asset;
      s.asset = s.backup_asset;
      s.backup_asset = temp;
      setTimeline(t);
    }
  };

  const updateCaption = (idx: number, val: string) => {
    const t = { ...timeline };
    t.captions[idx].word = val;
    setTimeline(t);
  };

  if (!job) return <div className="p-8 text-center">Loading...</div>;

  if (job.status === 'PROCESSING' || job.status === 'PENDING') {
    return (
      <div className="bg-white p-12 rounded shadow text-center max-w-lg mx-auto mt-10">
        <Loader className="w-12 h-12 text-blue-500 animate-spin mx-auto mb-4" />
        <h2 className="text-2xl font-bold mb-2">Generating Video</h2>
        <p className="text-gray-600 mb-6">{job.stage}</p>
        <div className="w-full bg-gray-200 rounded-full h-2.5">
          <div className="bg-blue-600 h-2.5 rounded-full" style={{ width: `${job.progress}%` }}></div>
        </div>
      </div>
    );
  }

  if (job.status === 'ERROR') {
    return (
      <div className="bg-red-50 p-6 rounded border border-red-200">
        <AlertTriangle className="text-red-500 mb-2 w-8 h-8" />
        <h2 className="text-xl font-bold text-red-700">Error</h2>
        <p className="text-red-600">{job.error}</p>
      </div>
    );
  }

  if (!timeline) return <div className="p-8 text-center"><Loader className="w-8 h-8 animate-spin mx-auto text-blue-500" /></div>;

  const currentVideo = job.final_video_path || job.draft_video_path;

  return (
    <div className="grid lg:grid-cols-2 gap-6 items-start">
      <div className="bg-white rounded shadow flex flex-col overflow-hidden sticky top-6">
        <div className="bg-black aspect-[9/16] w-full max-h-[60vh] flex items-center justify-center relative">
          {currentVideo ? (
            <video controls src={`http://localhost:8000/media?path=${encodeURIComponent(currentVideo)}`} className="h-full object-contain" />
          ) : (
            <div className="text-white text-center">Video preview not available</div>
          )}
        </div>
        <div className="p-4 bg-gray-50 flex justify-between items-center border-t flex-wrap gap-2">
          <span className="font-semibold text-gray-700">
            {job.final_video_path ? "Final Preview" : "Draft Preview"}
          </span>
          <div className="flex gap-2">
            <button onClick={saveTimeline} disabled={loading} className="bg-blue-600 text-white px-4 py-2 rounded font-medium hover:bg-blue-700 flex items-center gap-2">
              {loading ? <Loader className="w-4 h-4 animate-spin" /> : <RefreshCw className="w-4 h-4" />}
              Re-render Draft
            </button>
            <button onClick={renderFinal} disabled={loading} className="bg-green-600 text-white px-4 py-2 rounded font-medium hover:bg-green-700 flex items-center gap-2">
              {loading ? <Loader className="w-4 h-4 animate-spin" /> : null}
              Render Final (1080p)
            </button>
            <button onClick={exportProject} disabled={exporting} className="bg-purple-600 text-white px-4 py-2 rounded font-medium hover:bg-purple-700 flex items-center gap-2">
              {exporting ? <Loader className="w-4 h-4 animate-spin" /> : null}
              Export for Editor
            </button>
          </div>
        </div>
      </div>

      <div className="space-y-6">
        <div className="bg-white p-4 rounded shadow">
          <h3 className="font-bold text-lg mb-4 border-b pb-2">Scenes</h3>
          <div className="space-y-4">
            {timeline.scenes.map((s: any, idx: number) => (
              <div key={s.id} className="border p-3 rounded bg-gray-50 flex flex-col gap-2">
                <div className="flex justify-between items-start">
                  <div className="text-sm text-gray-500 font-mono">[{s.start.toFixed(1)}s - {s.end.toFixed(1)}s]</div>
                  {s.backup_asset && (
                    <button onClick={() => swapBackup(idx)} className="text-xs bg-gray-200 hover:bg-gray-300 px-2 py-1 rounded flex items-center gap-1">
                      <ArrowLeftRight className="w-3 h-3" /> Swap Backup
                    </button>
                  )}
                </div>
                <div className="text-sm italic text-gray-700 border-l-4 pl-2 border-gray-300 mb-2">"{s.text}"</div>
                
                {s.asset ? (
                  <div className="bg-blue-50 border border-blue-100 p-2 rounded text-xs flex justify-between items-center">
                    <div>
                      <span className="font-semibold text-blue-800">{s.asset.source}</span>
                      <span className="text-blue-600 ml-2">({s.asset.type})</span>
                    </div>
                    {s.asset.url && <a href={s.asset.url} target="_blank" className="text-blue-500 underline">View Source</a>}
                  </div>
                ) : (
                  <div className="bg-red-50 border border-red-100 p-2 rounded text-xs text-red-700 flex items-center gap-2">
                    <AlertTriangle className="w-4 h-4" /> Missing Asset - Neutral Fallback Card will be rendered
                  </div>
                )}
                
                <div className="mt-2 grid grid-cols-2 gap-4 bg-white p-2 rounded border text-sm">
                  <div>
                    <label className="block text-gray-600 text-xs font-bold mb-1">Motion</label>
                    <select 
                      value={s.motion || 'none'} 
                      onChange={(e) => {
                        const t = { ...timeline };
                        t.scenes[idx].motion = e.target.value;
                        setTimeline(t);
                      }}
                      className="w-full border rounded p-1"
                    >
                      <option value="none">None</option>
                      <option value="kenburns_in">Ken Burns In</option>
                      <option value="kenburns_out">Ken Burns Out</option>
                    </select>
                  </div>
                  <div>
                    <label className="block text-gray-600 text-xs font-bold mb-1">Transition Out</label>
                    <select 
                      value={s.transition_out?.type || 'none'} 
                      onChange={(e) => {
                        const t = { ...timeline };
                        if (e.target.value === 'none') {
                          delete t.scenes[idx].transition_out;
                        } else {
                          t.scenes[idx].transition_out = { type: e.target.value, duration: 0.4 };
                        }
                        setTimeline(t);
                      }}
                      className="w-full border rounded p-1"
                    >
                      <option value="none">None</option>
                      <option value="crossfade">Crossfade</option>
                    </select>
                  </div>
                </div>
                
                <div className="mt-1">
                  <button 
                    onClick={() => {
                      const t = { ...timeline };
                      if (!t.popups) t.popups = [];
                      t.popups.push({ at: s.start, duration: Math.min(2.0, s.end - s.start), type: 'text', path: 'CALLOUT TEXT', position: 'center', animation: 'fade' });
                      setTimeline(t);
                    }}
                    className="text-xs bg-gray-200 hover:bg-gray-300 px-2 py-1 rounded"
                  >
                    + Add Popup Overlay
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
        
        {timeline.popups && timeline.popups.length > 0 && (
          <div className="bg-white p-4 rounded shadow mt-6">
            <h3 className="font-bold text-lg mb-4 border-b pb-2">Popups / Overlays</h3>
            <div className="space-y-2">
              {timeline.popups.map((p: any, idx: number) => (
                <div key={idx} className="flex gap-2 text-sm items-center border p-2 rounded flex-wrap">
                  <span className="font-mono text-gray-500 w-12">{p.at.toFixed(1)}s</span>
                  <select 
                    value={p.type} 
                    onChange={e => { const t = {...timeline}; t.popups[idx].type = e.target.value; setTimeline(t); }}
                    className="border rounded p-1"
                  >
                    <option value="text">Text</option>
                    <option value="image">Image</option>
                    <option value="shape">Shape</option>
                  </select>
                  
                  {p.type === 'shape' ? (
                    <>
                      <select 
                        value={p.shape || 'rectangle'} 
                        onChange={e => { const t = {...timeline}; t.popups[idx].shape = e.target.value; setTimeline(t); }}
                        className="border rounded p-1"
                      >
                        <option value="rectangle">Rectangle</option>
                        <option value="circle">Circle</option>
                      </select>
                      <select 
                        value={p.color || 'red'} 
                        onChange={e => { const t = {...timeline}; t.popups[idx].color = e.target.value; setTimeline(t); }}
                        className="border rounded p-1"
                      >
                        <option value="red">Red</option>
                        <option value="green">Green</option>
                        <option value="blue">Blue</option>
                        <option value="black">Black</option>
                        <option value="white">White</option>
                      </select>
                    </>
                  ) : (
                    <input 
                      type="text" 
                      value={p.type === 'text' ? (p.text || p.path || '') : p.path} 
                      onChange={e => { 
                        const t = {...timeline}; 
                        if (p.type === 'text') { t.popups[idx].text = e.target.value; }
                        else { t.popups[idx].path = e.target.value; }
                        setTimeline(t); 
                      }}
                      className="border rounded px-2 py-1 flex-1"
                      placeholder={p.type === 'text' ? "Text Callout" : "data/uploads/image.png"}
                    />
                  )}
                  <select 
                    value={p.position || 'center'} 
                    onChange={e => { const t = {...timeline}; t.popups[idx].position = e.target.value; setTimeline(t); }}
                    className="border rounded p-1"
                  >
                    <option value="center">Center</option>
                    <option value="top">Top</option>
                    <option value="bottom">Bottom</option>
                  </select>
                  <button onClick={() => { const t = {...timeline}; t.popups.splice(idx,1); setTimeline(t); }} className="text-red-500 font-bold px-2 hover:bg-red-50 rounded">X</button>
                </div>
              ))}
            </div>
          </div>
        )}

        <div className="bg-white p-4 rounded shadow">
          <h3 className="font-bold text-lg mb-4 border-b pb-2">Captions</h3>
          <div className="flex flex-wrap gap-2">
            {timeline.captions.map((c: any, idx: number) => (
              <input 
                key={idx}
                type="text"
                value={c.word}
                onChange={(e) => updateCaption(idx, e.target.value)}
                className="border rounded px-2 py-1 text-sm w-24 focus:ring-1 focus:ring-blue-500 focus:outline-none"
              />
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
