import { useState, useRef } from 'react';
import { Upload, FileText, MonitorPlay, Sparkles, AudioLines } from 'lucide-react';
import { Button, Card, SegmentedControl, useToast } from './ui';

export default function CreatorView({ onJobCreated }: { onJobCreated: (id: string) => void }) {
  const [script, setScript] = useState('');
  const [aspectRatio, setAspectRatio] = useState('landscape');
  const [enableMotion, setEnableMotion] = useState('true');
  const [loading, setLoading] = useState(false);
  const [dragActive, setDragActive] = useState(false);
  const fileInput = useRef<HTMLInputElement>(null);
  const { toast } = useToast();

  const handleScriptSubmit = async () => {
    if (!script.trim()) return;
    setLoading(true);
    toast("Starting script generation...", "info");
    try {
      const res = await fetch('http://localhost:8000/generate/script', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          script, 
          aspect_ratio: aspectRatio, 
          enable_motion: enableMotion === 'true' 
        })
      });
      if (!res.ok) throw new Error("Backend returned error");
      const data = await res.json();
      toast("Job created successfully!", "success");
      onJobCreated(data.job_id);
    } catch (err) {
      console.error(err);
      toast("Failed to start job from script.", "error");
    } finally {
      setLoading(false);
    }
  };

  const processAudioFile = async (file: File) => {
    setLoading(true);
    toast(`Uploading ${file.name}...`, "info");
    const fd = new FormData();
    fd.append('audio_file', file);
    fd.append('aspect_ratio', aspectRatio);
    fd.append('enable_motion', enableMotion);
    try {
      const res = await fetch('http://localhost:8000/generate/audio', {
        method: 'POST',
        body: fd
      });
      if (!res.ok) throw new Error("Upload failed");
      const data = await res.json();
      toast("Audio uploaded, job created!", "success");
      onJobCreated(data.job_id);
    } catch (err) {
      console.error(err);
      toast("Failed to start job from audio.", "error");
    } finally {
      setLoading(false);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragActive(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      processAudioFile(e.dataTransfer.files[0]);
    }
  };

  return (
    <div className="max-w-5xl mx-auto space-y-10 animate-in fade-in slide-in-from-bottom-4 duration-500 pb-12">
      
      {/* Hero */}
      <div className="space-y-4 pt-4">
        <h2 className="text-4xl font-extrabold tracking-tight text-foreground">Create a New Project</h2>
        <p className="text-muted-foreground max-w-2xl text-lg">
          Upload a voiceover or paste a script, and our engine will source visuals, sync captions, and assemble a complete timeline.
        </p>
      </div>

      {/* Global Settings */}
      <Card className="p-6">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-6">
          <div className="flex items-center gap-3">
            <div className="bg-primary/10 p-2.5 rounded-xl">
              <MonitorPlay className="w-6 h-6 text-primary" />
            </div>
            <div>
              <h3 className="font-semibold text-lg text-foreground">Project Settings</h3>
              <p className="text-sm text-muted-foreground">Applies to both audio and script generation</p>
            </div>
          </div>
          
          <div className="flex flex-wrap items-center gap-4">
            <div className="space-y-1.5">
              <label className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">Format</label>
              <SegmentedControl 
                value={aspectRatio}
                onChange={setAspectRatio}
                options={[
                  { label: '16:9 (YouTube)', value: 'landscape' },
                  { label: '9:16 (Shorts)', value: 'portrait' },
                  { label: '1:1 (Square)', value: 'square' }
                ]}
              />
            </div>
            <div className="space-y-1.5">
              <label className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">Ken Burns</label>
              <SegmentedControl 
                value={enableMotion}
                onChange={setEnableMotion}
                options={[
                  { label: 'Enabled', value: 'true' },
                  { label: 'Disabled', value: 'false' }
                ]}
              />
            </div>
          </div>
        </div>
      </Card>

      {/* Inputs */}
      <div className="grid md:grid-cols-2 gap-6">
        
        {/* Dropzone */}
        <Card className={`relative overflow-hidden transition-all duration-300 flex flex-col min-h-[400px] ${dragActive ? 'ring-2 ring-primary border-primary' : 'hover:border-primary/50'}`}>
          <div className="p-6 border-b bg-muted/30">
            <div className="flex items-center gap-3">
              <AudioLines className="w-5 h-5 text-primary" />
              <h3 className="font-bold text-lg text-foreground">From Audio</h3>
            </div>
            <p className="text-sm text-muted-foreground mt-1">Upload a voiceover (MP3/WAV)</p>
          </div>
          
          <div 
            className={`flex-1 flex flex-col items-center justify-center p-8 text-center transition-colors ${dragActive ? 'bg-primary/5' : ''}`}
            onDragOver={(e) => { e.preventDefault(); setDragActive(true); }}
            onDragLeave={() => setDragActive(false)}
            onDrop={handleDrop}
          >
            <div className="w-16 h-16 bg-primary/10 rounded-full flex items-center justify-center text-primary mb-4">
              <Upload className="w-8 h-8" />
            </div>
            <h4 className="text-lg font-semibold mb-2 text-foreground">Drag & Drop Audio</h4>
            <p className="text-sm text-muted-foreground mb-8 max-w-[250px]">
              We'll transcribe the audio for perfect word-level timing.
            </p>
            <input 
              type="file" 
              ref={fileInput} 
              onChange={(e) => e.target.files?.[0] && processAudioFile(e.target.files[0])} 
              accept="audio/*" 
              className="hidden" 
            />
            <Button 
              onClick={() => fileInput.current?.click()} 
              isLoading={loading}
              size="lg"
            >
              Browse Files
            </Button>
          </div>
        </Card>

        {/* Script */}
        <Card className="flex flex-col min-h-[400px] hover:border-primary/50 transition-colors">
          <div className="p-6 border-b bg-muted/30">
            <div className="flex items-center gap-3">
              <FileText className="w-5 h-5 text-primary" />
              <h3 className="font-bold text-lg text-foreground">From Script</h3>
            </div>
            <p className="text-sm text-muted-foreground mt-1">Paste text for AI Voiceover</p>
          </div>
          
          <div className="p-6 flex-1 flex flex-col gap-4">
            <textarea 
              value={script} 
              onChange={e => setScript(e.target.value)} 
              placeholder="Start writing your script here... Our TTS engine will synthesize a natural voiceover."
              className="flex-1 w-full rounded-xl border border-input bg-background px-4 py-4 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring resize-none transition-shadow"
            />
            <Button 
              onClick={handleScriptSubmit} 
              disabled={!script.trim()}
              isLoading={loading}
              size="lg"
              className="w-full flex items-center gap-2"
            >
              <Sparkles className="w-4 h-4" />
              Generate Video
            </Button>
          </div>
        </Card>

      </div>
    </div>
  );
}
