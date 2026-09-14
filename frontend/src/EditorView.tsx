import React, { useState, useEffect, useRef } from 'react';
import { Loader, RefreshCw, AlertTriangle, ArrowLeftRight, Download, MonitorPlay, Terminal, Settings2 } from 'lucide-react';

export default function EditorView({ jobId }: { jobId: string }) {
  const [job, setJob] = useState<any>(null);
  const [timeline, setTimeline] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [exporting, setExporting] = useState(false);
  
  const logsEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    fetch(`http://localhost:8000/jobs/${jobId}`).then(r => r.json()).then(setJob);

    const ws = new WebSocket(`ws://localhost:8000/jobs/${jobId}/ws`);
    ws.onmessage = (e) => {
      const data = JSON.parse(e.data);
      setJob(data);
      if (data.status === 'COMPLETED' && data.timeline_path && !timeline) {
        loadTimeline();
      }
    };
    
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

  useEffect(() => {
    if (logsEndRef.current) {
      logsEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [job?.logs]);

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
    await fetch(`http://localhost:8000/jobs/${jobId}/render`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ draft_mode: false })
    });
    setLoading(false);
  };

  const exportProject = async () => {
    setExporting(true);
    try {
      await fetch(`http://localhost:8000/jobs/${jobId}/timeline`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(timeline)
      });
      const res = await fetch(`http://localhost:8000/jobs/${jobId}/export`, { method: 'POST' });
      if (res.ok) {
        const blob = await res.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `openreel_project_${jobId}.zip`;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
      } else {
        alert("Export failed");
      }
    } catch (e) {
      console.error(e);
      alert("Error exporting");
    }
    setExporting(false);
  };

  const swapBackup = (idx: number) => {
    const t = { ...timeline };
    const scene = t.scenes[idx];
    if (scene.backup_asset) {
      const temp = scene.asset;
      scene.asset = scene.backup_asset;
      scene.backup_asset = temp;
      setTimeline(t);
    }
  };

  const updateCaption = (idx: number, val: string) => {
    const t = { ...timeline };
    t.captions[idx].word = val;
    setTimeline(t);
  };

  if (!job) return (
    <div className="flex h-64 items-center justify-center">
      <Loader className="w-8 h-8 animate-spin text-gray-400" />
    </div>
  );

  if (job.status === 'PROCESSING' || job.status === 'PENDING') {
    return (
      <div className="max-w-2xl mx-auto mt-8 animate-in fade-in slide-in-from-bottom-4">
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
          <div className="p-8 text-center border-b border-gray-100">
            <div className="bg-blue-50 w-16 h-16 rounded-full flex items-center justify-center mx-auto mb-6">
              <Loader className="w-8 h-8 text-blue-600 animate-spin" />
            </div>
            <h2 className="text-2xl font-bold tracking-tight text-gray-900 mb-2">Generating Video...</h2>
            <p className="text-gray-500 font-medium">{job.stage}</p>
            
            <div className="mt-8 relative">
              <div className="w-full bg-gray-100 rounded-full h-2 overflow-hidden">
                <div 
                  className="bg-black h-full rounded-full transition-all duration-500 ease-out" 
                  style={{ width: `${job.progress}%` }}
                ></div>
              </div>
              <div className="text-xs font-mono text-gray-400 mt-2 text-right">{job.progress.toFixed(0)}%</div>
            </div>
          </div>
          
          <div className="bg-[#1C1C1E] p-4 font-mono text-xs sm:text-sm h-64 overflow-y-auto">
            <div className="flex items-center gap-2 text-gray-400 mb-3 border-b border-gray-700 pb-2">
              <Terminal className="w-4 h-4" />
              <span>Terminal Output</span>
            </div>
            {job.logs && job.logs.length > 0 ? (
              <div className="space-y-1.5">
                {job.logs.map((log: string, i: number) => (
                  <div key={i} className="text-green-400">
                    <span className="text-gray-500 mr-2">[{new Date().toLocaleTimeString()}]</span>
                    {log}
                  </div>
                ))}
                <div ref={logsEndRef} />
              </div>
            ) : (
              <div className="text-gray-500">Initializing engine...</div>
            )}
          </div>
        </div>
      </div>
    );
  }

  if (job.status === 'ERROR') {
    return (
      <div className="bg-red-50 p-6 rounded-xl border border-red-200 flex flex-col items-center justify-center text-center mt-12 max-w-lg mx-auto">
        <AlertTriangle className="text-red-500 mb-4 w-12 h-12" />
        <h2 className="text-xl font-bold text-red-900 mb-2">Pipeline Failed</h2>
        <p className="text-red-700 bg-red-100/50 p-3 rounded w-full font-mono text-sm border border-red-200">{job.error}</p>
      </div>
    );
  }

  if (!timeline) return (
    <div className="flex h-64 items-center justify-center">
      <Loader className="w-8 h-8 animate-spin text-gray-400" />
    </div>
  );

  const currentVideo = job.final_video_path || job.draft_video_path;

  return (
    <div className="grid lg:grid-cols-12 gap-8 items-start animate-in fade-in slide-in-from-bottom-4">
      
      {/* Player Column */}
      <div className="lg:col-span-5 bg-white rounded-xl shadow-sm border border-gray-200 flex flex-col overflow-hidden sticky top-24">
        <div className="bg-[#111] aspect-[9/16] w-full max-h-[65vh] flex items-center justify-center relative">
          {currentVideo ? (
            <video 
              controls 
              src={`http://localhost:8000/media?path=${encodeURIComponent(currentVideo)}`} 
              className="h-full w-full object-contain" 
            />
          ) : (
            <div className="text-gray-500 flex flex-col items-center gap-2">
              <MonitorPlay className="w-8 h-8 opacity-50" />
              <span>Preview not available</span>
            </div>
          )}
        </div>
        
        <div className="p-5 bg-gray-50 flex flex-col gap-4 border-t border-gray-200">
          <div className="flex items-center justify-between">
            <span className="text-sm font-semibold text-gray-700 bg-gray-200/50 px-2.5 py-1 rounded-md">
              {job.final_video_path ? "✨ Final Quality" : "⚡ Draft Preview"}
            </span>
          </div>
          <div className="grid grid-cols-2 gap-2">
            <button 
              onClick={saveTimeline} 
              disabled={loading} 
              className="bg-white border border-gray-300 text-gray-700 px-3 py-2.5 rounded-lg text-sm font-medium hover:bg-gray-50 flex items-center justify-center gap-2 transition-colors disabled:opacity-50"
            >
              {loading ? <Loader className="w-4 h-4 animate-spin" /> : <RefreshCw className="w-4 h-4" />}
              Re-render Draft
            </button>
            <button 
              onClick={renderFinal} 
              disabled={loading} 
              className="bg-black text-white px-3 py-2.5 rounded-lg text-sm font-medium hover:bg-gray-800 flex items-center justify-center gap-2 transition-colors disabled:opacity-50"
            >
              {loading ? <Loader className="w-4 h-4 animate-spin" /> : <MonitorPlay className="w-4 h-4" />}
              Final (1080p)
            </button>
            <button 
              onClick={exportProject} 
              disabled={exporting} 
              className="col-span-2 bg-blue-50 text-blue-700 border border-blue-200 px-3 py-2.5 rounded-lg text-sm font-medium hover:bg-blue-100 flex items-center justify-center gap-2 transition-colors disabled:opacity-50"
            >
              {exporting ? <Loader className="w-4 h-4 animate-spin" /> : <Download className="w-4 h-4" />}
              Export Bundle (FCPXML + SRT + Media)
            </button>
          </div>
        </div>
      </div>

      {/* Editor Column */}
      <div className="lg:col-span-7 space-y-6">
        
        {/* Scenes Editor */}
        <div className="bg-white p-6 rounded-xl shadow-sm border border-gray-200">
          <div className="flex items-center gap-2 mb-6 border-b border-gray-100 pb-4">
            <Settings2 className="w-5 h-5 text-gray-500" />
            <h3 className="font-bold text-lg text-gray-900">Scene Sequence</h3>
          </div>
          
          <div className="space-y-4">
            {timeline.scenes.map((s: any, idx: number) => (
              <div key={s.id} className="border border-gray-200 p-4 rounded-xl bg-gray-50/50 flex flex-col gap-3 group hover:border-blue-200 transition-colors">
                <div className="flex justify-between items-start">
                  <div className="text-xs text-gray-500 font-mono bg-white border px-2 py-1 rounded">
                    [{s.start.toFixed(1)}s - {s.end.toFixed(1)}s]
                  </div>
                  {s.backup_asset && (
                    <button onClick={() => swapBackup(idx)} className="text-xs bg-white border shadow-sm hover:bg-gray-50 px-2 py-1.5 rounded-md flex items-center gap-1.5 transition-colors text-gray-700 font-medium">
                      <ArrowLeftRight className="w-3 h-3 text-blue-600" /> Swap Alternative
                    </button>
                  )}
                </div>
                
                <div className="text-sm italic text-gray-700 border-l-2 pl-3 border-gray-300 py-1">"{s.text}"</div>
                
                {s.asset ? (
                  <div className="bg-white border border-gray-200 p-2.5 rounded-lg text-xs flex justify-between items-center shadow-sm">
                    <div className="flex items-center gap-2">
                      <div className="w-2 h-2 rounded-full bg-green-500"></div>
                      <span className="font-semibold text-gray-900">{s.asset.source}</span>
                      <span className="text-gray-500 capitalize px-2 py-0.5 bg-gray-100 rounded text-[10px] font-mono tracking-wide">{s.asset.type}</span>
                    </div>
                    {s.asset.url && <a href={s.asset.url} target="_blank" rel="noreferrer" className="text-blue-600 hover:text-blue-800 hover:underline font-medium">View Source</a>}
                  </div>
                ) : (
                  <div className="bg-orange-50 border border-orange-200 p-3 rounded-lg text-xs text-orange-800 flex items-center gap-2 font-medium">
                    <AlertTriangle className="w-4 h-4 text-orange-500" /> Missing Asset - Black fallback card will be rendered
                  </div>
                )}
                
                <div className="mt-2 grid grid-cols-2 gap-3 bg-white p-3 rounded-lg border border-gray-200 shadow-sm">
                  <div>
                    <label className="block text-gray-500 text-[11px] uppercase tracking-wider font-bold mb-1.5">Motion</label>
                    <select 
                      value={s.motion || 'none'} 
                      onChange={(e) => {
                        const t = { ...timeline };
                        t.scenes[idx].motion = e.target.value;
                        setTimeline(t);
                      }}
                      className="w-full border border-gray-200 rounded-md p-1.5 text-sm bg-gray-50 focus:ring-1 focus:ring-black outline-none"
                    >
                      <option value="none">None</option>
                      <option value="kenburns_in">Ken Burns In</option>
                      <option value="kenburns_out">Ken Burns Out</option>
                    </select>
                  </div>
                  <div>
                    <label className="block text-gray-500 text-[11px] uppercase tracking-wider font-bold mb-1.5">Transition Out</label>
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
                      className="w-full border border-gray-200 rounded-md p-1.5 text-sm bg-gray-50 focus:ring-1 focus:ring-black outline-none"
                    >
                      <option value="none">None</option>
                      <option value="crossfade">Crossfade (0.4s)</option>
                    </select>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Captions Tweaker */}
        <div className="bg-white p-6 rounded-xl shadow-sm border border-gray-200">
          <h3 className="font-bold text-lg mb-4 border-b border-gray-100 pb-4">Subtitle Timing & Overrides</h3>
          <p className="text-xs text-gray-500 mb-4">Edit the transcribed words. Timing is locked to audio.</p>
          <div className="flex flex-wrap gap-2 p-4 bg-gray-50 border border-gray-200 rounded-xl">
            {timeline.captions.map((c: any, idx: number) => (
              <input 
                key={idx}
                type="text"
                value={c.word}
                onChange={(e) => updateCaption(idx, e.target.value)}
                className="border border-gray-200 rounded-md px-2 py-1.5 text-sm w-[4.5rem] text-center focus:ring-2 focus:ring-black focus:border-black outline-none transition-shadow shadow-sm bg-white"
              />
            ))}
          </div>
        </div>
        
        {/* Popups */}
        <div className="bg-white p-6 rounded-xl shadow-sm border border-gray-200">
          <div className="flex justify-between items-center mb-4 border-b border-gray-100 pb-4">
            <h3 className="font-bold text-lg text-gray-900">Popups & Overlays</h3>
            <button 
              onClick={() => {
                const t = { ...timeline };
                if (!t.popups) t.popups = [];
                t.popups.push({ at: 0.0, duration: 2.0, type: 'text', text: 'CALLOUT', position: 'center', animation: 'fade' });
                setTimeline(t);
              }}
              className="text-xs bg-gray-900 text-white hover:bg-gray-800 px-3 py-1.5 rounded-md font-medium transition-colors"
            >
              + Add Overlay
            </button>
          </div>
          
          {timeline.popups && timeline.popups.length > 0 ? (
            <div className="space-y-3">
              {timeline.popups.map((p: any, idx: number) => (
                <div key={idx} className="flex gap-3 text-sm items-center border border-gray-200 p-3 rounded-lg flex-wrap bg-gray-50/50">
                  <span className="font-mono text-xs bg-white border px-2 py-1 rounded text-gray-500 w-12 text-center">{p.at.toFixed(1)}s</span>
                  <select 
                    value={p.type} 
                    onChange={e => { const t = {...timeline}; t.popups[idx].type = e.target.value; setTimeline(t); }}
                    className="border border-gray-200 rounded-md p-1.5 bg-white text-xs font-medium outline-none focus:ring-1 focus:ring-black"
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
                        className="border border-gray-200 rounded-md p-1.5 bg-white text-xs outline-none"
                      >
                        <option value="rectangle">Rectangle</option>
                        <option value="circle">Circle</option>
                      </select>
                      <select 
                        value={p.color || 'red'} 
                        onChange={e => { const t = {...timeline}; t.popups[idx].color = e.target.value; setTimeline(t); }}
                        className="border border-gray-200 rounded-md p-1.5 bg-white text-xs outline-none"
                      >
                        <option value="red">Red</option>
                        <option value="green">Green</option>
                        <option value="blue">Blue</option>
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
                      className="border border-gray-200 rounded-md px-2 py-1.5 flex-1 bg-white text-xs outline-none focus:ring-1 focus:ring-black"
                      placeholder={p.type === 'text' ? "Callout Text" : "URL or path"}
                    />
                  )}
                  <select 
                    value={p.position || 'center'} 
                    onChange={e => { const t = {...timeline}; t.popups[idx].position = e.target.value; setTimeline(t); }}
                    className="border border-gray-200 rounded-md p-1.5 bg-white text-xs outline-none"
                  >
                    <option value="center">Center</option>
                    <option value="top">Top</option>
                    <option value="bottom">Bottom</option>
                  </select>
                  <button onClick={() => { const t = {...timeline}; t.popups.splice(idx,1); setTimeline(t); }} className="text-gray-400 hover:text-red-600 hover:bg-red-50 p-1.5 rounded-md transition-colors ml-auto">
                    <AlertTriangle className="w-4 h-4 hidden" /> {/* Just to keep lucide import valid if unused elsewhere, but I use it */}
                    X
                  </button>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-center py-6 text-sm text-gray-500">No popups added yet.</div>
          )}
        </div>
        
      </div>
    </div>
  );
}
