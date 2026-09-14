import { useState, useEffect, useRef } from 'react';
import { Loader2, RefreshCw, AlertTriangle, ArrowLeftRight, Download, MonitorPlay, Type, Image as ImageIcon, Sparkles } from 'lucide-react';
import { Button, Card, Badge, useToast, Input } from './ui';
import ProcessingView from './ProcessingView';

export default function EditorView({ jobId }: { jobId: string }) {
  const [job, setJob] = useState<any>(null);
  const [timeline, setTimeline] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [exportTarget, setExportTarget] = useState('resolve');
  
  const logsEndRef = useRef<HTMLDivElement>(null);
  const { toast } = useToast();

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
        setJob((prev: any) => {
          if (data.status === 'COMPLETED' || data.status === 'ERROR') clearInterval(interval);
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
    toast("Re-rendering draft...", "info");
    try {
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
      toast("Draft re-rendered successfully!", "success");
    } catch {
      toast("Error rendering draft", "error");
    }
    setLoading(false);
  };

  const renderFinal = async () => {
    setLoading(true);
    toast("Rendering final 1080p video...", "info");
    try {
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
      toast("Final render completed!", "success");
    } catch {
      toast("Error rendering final video", "error");
    }
    setLoading(false);
  };

  const exportProject = async () => {
    setExporting(true);
    toast("Preparing project bundle...", "info");
    try {
      await fetch(`http://localhost:8000/jobs/${jobId}/timeline`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(timeline)
      });
      const res = await fetch(`http://localhost:8000/jobs/${jobId}/export`, { 
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ target: exportTarget })
      });
      if (!res.ok) throw new Error("Export failed");
      const data = await res.json();
      const a = document.createElement('a');
      a.href = `http://localhost:8000/media?path=${encodeURIComponent(data.export_path)}`;
      a.download = `openreel_project_${jobId}.zip`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      toast("Export ready — downloading...", "success");
    } catch (e) {
      console.error(e);
      toast("Error exporting project bundle", "error");
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
      toast(`Swapped asset for scene ${idx + 1}`, "success");
    }
  };

  // Group captions into lines (chunk of 6 words)
  const getCaptionLines = () => {
    if (!timeline || !timeline.captions) return [];
    const lines = [];
    let currentLine = [];
    for (let i = 0; i < timeline.captions.length; i++) {
      currentLine.push({ ...timeline.captions[i], index: i });
      if (currentLine.length === 6 || i === timeline.captions.length - 1) {
        lines.push(currentLine);
        currentLine = [];
      }
    }
    return lines;
  };

  const handleLineChange = (lineIdx: number, newText: string, lines: any[]) => {
    const t = { ...timeline };
    const words = newText.split(' ').filter(w => w.length > 0);
    const targetLine = lines[lineIdx];
    
    // Map new words back to the original objects in timeline
    targetLine.forEach((cap: any, localIdx: number) => {
      const w = words[localIdx] || '';
      t.captions[cap.index].word = w;
    });
    
    // If they typed extra words, append to the last word object
    if (words.length > targetLine.length) {
      const extra = words.slice(targetLine.length).join(' ');
      t.captions[targetLine[targetLine.length - 1].index].word += ' ' + extra;
    }
    
    setTimeline(t);
  };

  if (!job) return (
    <div className="flex h-[80vh] items-center justify-center">
      <Loader2 className="w-10 h-10 animate-spin text-primary opacity-50" />
    </div>
  );

  if (job.status === 'PROCESSING' || job.status === 'PENDING') {
    return <ProcessingView job={job} logsEndRef={logsEndRef} />;
  }

  if (job.status === 'ERROR') {
    return (
      <div className="flex h-[80vh] items-center justify-center">
        <Card className="p-8 max-w-md w-full text-center space-y-6">
          <div className="w-16 h-16 bg-red-100 dark:bg-red-900/30 text-red-600 dark:text-red-400 rounded-full flex items-center justify-center mx-auto">
            <AlertTriangle className="w-8 h-8" />
          </div>
          <div>
            <h2 className="text-2xl font-bold text-foreground mb-2">Pipeline Failed</h2>
            <p className="text-sm text-muted-foreground">{job.error}</p>
          </div>
          <Button onClick={() => window.location.reload()} variant="primary" className="w-full">
            Reload App
          </Button>
        </Card>
      </div>
    );
  }

  if (!timeline) return (
    <div className="flex h-[80vh] items-center justify-center">
      <Loader2 className="w-10 h-10 animate-spin text-primary opacity-50" />
    </div>
  );

  const currentVideo = job.final_video_path || job.draft_video_path;
  const isFinal = !!job.final_video_path;

  // Derive aspect ratio from timeline config
  const res = timeline.resolution || [1920, 1080];
  let aspectClass = "aspect-video"; // 16:9
  if (res[0] < res[1]) aspectClass = "aspect-[9/16]"; // 9:16
  else if (res[0] === res[1]) aspectClass = "aspect-square"; // 1:1

  const captionLines = getCaptionLines();

  return (
    <div className="grid lg:grid-cols-12 gap-8 items-start animate-in fade-in slide-in-from-bottom-4 pt-2">
      
      {/* --- Player Pane --- */}
      <div className="lg:col-span-5 flex flex-col gap-6 sticky top-8">
        
        <div className="space-y-1.5 px-1">
          <p className="text-sm font-medium text-foreground">
            Preview your video below. For final edits and best quality, export to your editor. You can also render a finished video here (slower).
          </p>
        </div>

        <div className={`w-full bg-black rounded-xl overflow-hidden shadow-xl border border-gray-800 ${aspectClass} relative flex items-center justify-center`}>
          {currentVideo ? (
            <video 
              controls 
              src={`http://localhost:8000/media?path=${encodeURIComponent(currentVideo)}`} 
              className="w-full h-full object-contain"
            />
          ) : (
            <div className="text-muted-foreground flex flex-col items-center gap-2 p-6 text-center">
              <MonitorPlay className="w-10 h-10 opacity-50 mb-2" />
              <span className="font-medium text-sm">No preview rendered &mdash; review clips below, export to your editor, or render a preview.</span>
            </div>
          )}
          {isFinal && (
            <div className="absolute top-4 right-4">
              <Badge variant="success">Final Render</Badge>
            </div>
          )}
          {!isFinal && currentVideo && (
            <div className="absolute top-4 right-4">
              <Badge variant="warning">Draft Preview (Low Quality)</Badge>
            </div>
          )}
        </div>
        
        <Card className="p-5 space-y-5">
          {/* Export Action (Hero) */}
          <div className="space-y-3">
            <h4 className="text-sm font-semibold text-foreground tracking-tight">Recommended Workflow</h4>
            <div className="flex items-center gap-2">
              <select 
                value={exportTarget}
                onChange={e => setExportTarget(e.target.value)}
                className="rounded-lg border border-input bg-background px-3 h-10 text-sm outline-none focus:ring-2 focus:ring-ring font-medium"
              >
                <option value="resolve">DaVinci Resolve</option>
                <option value="premiere">Premiere Pro</option>
                <option value="capcut">CapCut</option>
              </select>
              <Button onClick={exportProject} isLoading={exporting} variant="primary" className="flex-1 gap-2 shadow-md">
                <Download className="w-4 h-4" /> Export to Editor
              </Button>
            </div>
          </div>
          
          <hr className="border-border" />

          {/* In-app actions */}
          <div className="space-y-3">
            <h4 className="text-sm font-semibold text-foreground tracking-tight">In-App Controls</h4>
            <div className="grid grid-cols-2 gap-3">
              <Button onClick={saveTimeline} isLoading={loading} variant="secondary" className="w-full gap-2 text-xs text-balance">
                <RefreshCw className="w-3.5 h-3.5" /> {currentVideo ? "Update Preview" : "Render Preview (needs GPU/CPU time)"}
              </Button>
              <div className="flex flex-col gap-1 w-full">
                <Button onClick={renderFinal} isLoading={loading} variant="ghost" className="w-full gap-2 text-xs border border-border">
                  <Sparkles className="w-3.5 h-3.5" /> Render Final Here (slower)
                </Button>
                <span className="text-[10px] text-muted-foreground text-center leading-tight">Optional. Uses your local machine.</span>
              </div>
            </div>
          </div>
        </Card>
      </div>

      {/* --- Editor Pane --- */}
      <div className="lg:col-span-7 space-y-8 pb-12">
        
        {/* Scenes Editor */}
        <div className="space-y-4">
          <div className="flex items-center gap-2 px-1">
            <ImageIcon className="w-5 h-5 text-primary" />
            <h3 className="font-bold text-xl text-foreground tracking-tight">Scenes & Assets</h3>
          </div>
          
          <div className="space-y-4">
            {timeline.scenes.map((s: any, idx: number) => (
              <Card key={s.id} className="p-5 overflow-hidden group hover:border-primary/50 transition-colors">
                <div className="flex justify-between items-start mb-3">
                  <div className="text-xs text-muted-foreground font-mono bg-muted px-2 py-1 rounded">
                    {s.start.toFixed(1)}s - {s.end.toFixed(1)}s
                  </div>
                  {s.backup_asset && (
                    <Button onClick={() => swapBackup(idx)} size="sm" variant="secondary" className="h-7 text-xs gap-1.5 rounded-full">
                      <ArrowLeftRight className="w-3 h-3 text-primary" /> Swap Alternate
                    </Button>
                  )}
                </div>
                
                <p className="text-sm font-medium text-foreground mb-4 pl-3 border-l-2 border-primary/40">
                  "{s.text}"
                </p>
                
                {s.asset ? (
                  <div className="space-y-3">
                    <div className="bg-black rounded-lg overflow-hidden border border-gray-800 aspect-video relative flex items-center justify-center">
                      {s.asset.type === 'video' ? (
                        <video 
                          src={`http://localhost:8000/media?path=${encodeURIComponent(s.asset.path)}`} 
                          controls 
                          className="w-full h-full object-contain"
                        />
                      ) : (
                        <img 
                          src={`http://localhost:8000/media?path=${encodeURIComponent(s.asset.path)}`} 
                          alt={`Scene ${idx + 1}`} 
                          className="w-full h-full object-contain"
                        />
                      )}
                    </div>
                    <div className="bg-accent/50 border rounded-lg p-3 text-sm flex justify-between items-center">
                      <div className="flex items-center gap-2">
                        <div className="w-2 h-2 rounded-full bg-green-500 shadow-[0_0_8px_rgba(34,197,94,0.6)]" />
                        <span className="font-semibold text-foreground">{s.asset.source}</span>
                        <span className="text-muted-foreground uppercase text-[10px] font-bold tracking-wider px-1.5 py-0.5 bg-background rounded">{s.asset.type}</span>
                      </div>
                      {s.asset.url && (
                        <a href={s.asset.url} target="_blank" rel="noreferrer" className="text-primary hover:underline font-medium text-xs">
                          View Source
                        </a>
                      )}
                    </div>
                  </div>
                ) : (
                  <div className="bg-red-50 dark:bg-red-900/10 border-red-200 dark:border-red-900/50 p-3 rounded-lg flex items-center gap-2 text-red-800 dark:text-red-400 text-sm font-medium">
                    <AlertTriangle className="w-4 h-4" /> Missing Asset (Black Fallback)
                  </div>
                )}
                
                <div className="mt-4 grid grid-cols-2 gap-4">
                  <div className="space-y-1.5">
                    <label className="text-[10px] uppercase font-bold tracking-wider text-muted-foreground">Motion</label>
                    <select 
                      value={s.motion || 'none'} 
                      onChange={(e) => {
                        const t = { ...timeline };
                        t.scenes[idx].motion = e.target.value;
                        setTimeline(t);
                      }}
                      className="w-full rounded-md border border-input bg-background px-3 py-1.5 text-sm outline-none focus:ring-2 focus:ring-ring"
                    >
                      <option value="none">None</option>
                      <option value="kenburns_in">Ken Burns In</option>
                      <option value="kenburns_out">Ken Burns Out</option>
                    </select>
                  </div>
                  <div className="space-y-1.5">
                    <label className="text-[10px] uppercase font-bold tracking-wider text-muted-foreground">Transition Out</label>
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
                      className="w-full rounded-md border border-input bg-background px-3 py-1.5 text-sm outline-none focus:ring-2 focus:ring-ring"
                    >
                      <option value="none">None Cut</option>
                      <option value="crossfade">Crossfade (0.4s)</option>
                    </select>
                  </div>
                </div>
              </Card>
            ))}
          </div>
        </div>

        {/* Captions Editor */}
        <div className="space-y-4">
          <div className="flex items-center gap-2 px-1">
            <Type className="w-5 h-5 text-primary" />
            <h3 className="font-bold text-xl text-foreground tracking-tight">Captions</h3>
          </div>
          <Card className="p-5">
            <p className="text-xs text-muted-foreground mb-4">Edit transcribed text. Timing remains locked to the audio track.</p>
            <div className="space-y-2">
              {captionLines.map((line: any[], lineIdx: number) => {
                const lineStr = line.map(c => c.word).join(' ').replace(/\s+/g, ' ').trim();
                return (
                  <Input 
                    key={lineIdx}
                    value={lineStr}
                    onChange={(e) => handleLineChange(lineIdx, e.target.value, captionLines)}
                    className="font-medium"
                  />
                );
              })}
            </div>
          </Card>
        </div>

        {/* Popups */}
        <div className="space-y-4">
          <div className="flex items-center justify-between px-1">
            <div className="flex items-center gap-2">
              <Sparkles className="w-5 h-5 text-primary" />
              <h3 className="font-bold text-xl text-foreground tracking-tight">Overlays</h3>
            </div>
            <Button size="sm" onClick={() => {
              const t = { ...timeline };
              if (!t.popups) t.popups = [];
              t.popups.push({ at: 0.0, duration: 2.0, type: 'text', text: 'CALLOUT', position: 'center', animation: 'fade' });
              setTimeline(t);
            }}>
              + Add Overlay
            </Button>
          </div>
          
          <Card className="p-5">
            {timeline.popups && timeline.popups.length > 0 ? (
              <div className="space-y-3">
                {timeline.popups.map((p: any, idx: number) => (
                  <div key={idx} className="flex flex-wrap items-center gap-3 bg-muted/50 border rounded-lg p-3">
                    <span className="font-mono text-xs bg-background border px-2 py-1 rounded text-muted-foreground">
                      {p.at.toFixed(1)}s
                    </span>
                    <select 
                      value={p.type} 
                      onChange={e => { const t = {...timeline}; t.popups[idx].type = e.target.value; setTimeline(t); }}
                      className="border border-input rounded-md p-1.5 bg-background text-sm outline-none focus:ring-2 focus:ring-ring"
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
                          className="border border-input rounded-md p-1.5 bg-background text-sm outline-none"
                        >
                          <option value="rectangle">Rectangle</option>
                          <option value="circle">Circle</option>
                        </select>
                        <select 
                          value={p.color || 'red'} 
                          onChange={e => { const t = {...timeline}; t.popups[idx].color = e.target.value; setTimeline(t); }}
                          className="border border-input rounded-md p-1.5 bg-background text-sm outline-none"
                        >
                          <option value="red">Red</option>
                          <option value="green">Green</option>
                          <option value="blue">Blue</option>
                        </select>
                      </>
                    ) : (
                      <Input 
                        value={p.type === 'text' ? (p.text || p.path || '') : p.path} 
                        onChange={e => { 
                          const t = {...timeline}; 
                          if (p.type === 'text') { t.popups[idx].text = e.target.value; }
                          else { t.popups[idx].path = e.target.value; }
                          setTimeline(t); 
                        }}
                        placeholder={p.type === 'text' ? "Callout Text" : "URL or path"}
                        className="flex-1 h-8"
                      />
                    )}
                    <select 
                      value={p.position || 'center'} 
                      onChange={e => { const t = {...timeline}; t.popups[idx].position = e.target.value; setTimeline(t); }}
                      className="border border-input rounded-md p-1.5 bg-background text-sm outline-none"
                    >
                      <option value="center">Center</option>
                      <option value="top">Top</option>
                      <option value="bottom">Bottom</option>
                    </select>
                    <button onClick={() => { const t = {...timeline}; t.popups.splice(idx,1); setTimeline(t); }} className="text-muted-foreground hover:text-red-500 p-1.5 ml-auto">
                      X
                    </button>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-sm text-muted-foreground text-center py-4">No popups added yet.</p>
            )}
          </Card>
        </div>
        
      </div>
    </div>
  );
}
