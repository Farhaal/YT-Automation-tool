import { useState, useEffect } from 'react';
import { Card } from "./ui";
import { Input } from "./ui";
import { Button } from "./ui";
import { Badge } from "./ui";
import { Key, Bot, Trash2, ArrowUp, ArrowDown, Activity } from "lucide-react";
import { useToast } from "./ui";

const PROVIDER_NAMES: Record<string, string> = {
  gemini: "Google (Gemini)",
  openai: "OpenAI",
  openrouter: "OpenRouter",
  groq: "Groq",
  ollama: "Ollama (Local)"
};

export default function SettingsView() {
  const [status, setStatus] = useState<any>({});
  const [pexels, setPexels] = useState('');
  const [pixabay, setPixabay] = useState('');
  
  const [llmProviders, setLlmProviders] = useState<any[]>([]);
  const [enableVisualVerification, setEnableVisualVerification] = useState(false);
  const [visionModel, setVisionModel] = useState('');

  const [testStatus, setTestStatus] = useState<Record<string, any>>({});

  const { toast } = useToast();

  const load = () => {
    fetch('http://localhost:8000/settings')
      .then(r => r.json())
      .then(data => {
        setStatus(data);
        if (data.llm_providers) {
          // Merge with default providers to ensure all cards exist
          const loaded = data.llm_providers;
          const loadedNames = loaded.map((p: any) => p.provider);
          const defaults = [
            { provider: "gemini", model: "gemini-2.0-flash", api_key: "", enabled: false, status: "Not configured" },
            { provider: "openai", model: "gpt-4o-mini", api_key: "", enabled: false, status: "Not configured" },
            { provider: "openrouter", model: "", api_key: "", enabled: false, status: "Not configured" },
            { provider: "groq", model: "llama3-8b-8192", api_key: "", enabled: false, status: "Not configured" },
            { provider: "ollama", model: "llama3", api_key: "", enabled: false, status: "Not configured" }
          ];
          const merged = [...loaded];
          defaults.forEach(d => {
            if (!loadedNames.includes(d.provider)) {
              merged.push(d);
            }
          });
          setLlmProviders(merged);
        }
        if (data.enable_visual_verification !== undefined) setEnableVisualVerification(data.enable_visual_verification);
        if (data.vision_model) setVisionModel(data.vision_model);
      });
  };

  useEffect(() => { load(); }, []);

  const saveMedia = async () => {
    try {
      await fetch('http://localhost:8000/settings', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ pexels_key: pexels, pixabay_key: pixabay })
      });
      setPexels('');
      setPixabay('');
      load();
      toast("Media settings saved", "success");
    } catch {
      toast("Error saving settings", "error");
    }
  };

  const saveLlm = async () => {
    try {
      await fetch('http://localhost:8000/settings', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          llm_providers: llmProviders.map(p => ({
            provider: p.provider,
            api_key: p.api_key || undefined,
            model: p.model,
            enabled: p.enabled
          })),
          enable_visual_verification: enableVisualVerification,
          vision_model: visionModel
        })
      });
      // Clear inputted keys
      setLlmProviders(prev => prev.map(p => ({...p, api_key: ""})));
      load();
      toast("LLM settings saved", "success");
    } catch {
      toast("Error saving LLM config", "error");
    }
  };

  const remove = async (provider: string) => {
    try {
      await fetch("http://localhost:8000/settings/" + provider, { method: 'DELETE' });
      load();
      toast("Cleared config", "success");
    } catch {
      toast("Error clearing config", "error");
    }
  };

  const moveProvider = (index: number, dir: number) => {
    if (index + dir < 0 || index + dir >= llmProviders.length) return;
    const newProviders = [...llmProviders];
    const temp = newProviders[index];
    newProviders[index] = newProviders[index + dir];
    newProviders[index + dir] = temp;
    setLlmProviders(newProviders);
  };

  const testLlm = async (index: number) => {
    const p = llmProviders[index];
    setTestStatus(prev => ({...prev, [p.provider]: { loading: true }}));
    try {
      const res = await fetch('http://localhost:8000/settings/test-llm', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ provider: p.provider, api_key: p.api_key || undefined, model: p.model })
      });
      const data = await res.json();
      if (data.ok) {
        setTestStatus(prev => ({...prev, [p.provider]: { ok: true }}));
      } else {
        setTestStatus(prev => ({...prev, [p.provider]: { ok: false, msg: data.message, status: data.status }}));
      }
    } catch (e: any) {
      setTestStatus(prev => ({...prev, [p.provider]: { ok: false, msg: e.message }}));
    }
  };

  return (
    <div className="max-w-4xl mx-auto space-y-8 animate-in fade-in slide-in-from-bottom-4 pt-4 pb-12">
      
      <div>
        <h2 className="text-3xl font-extrabold tracking-tight text-foreground mb-2">Settings</h2>
        <p className="text-muted-foreground">Manage your local integration keys and models.</p>
      </div>

      <div className="grid md:grid-cols-2 gap-8">
        
        {/* Media */}
        <div className="space-y-4">
          <div className="flex items-center gap-2 px-1">
            <Key className="w-5 h-5 text-primary" />
            <h3 className="font-bold text-xl text-foreground">Stock Media</h3>
          </div>

          <Card className="p-5 space-y-5">
            <div>
              <div className="flex justify-between items-center mb-2">
                <label className="text-sm font-semibold text-foreground">Pexels API Key</label>
                <Badge variant={status.pexels === 'Configured' ? 'success' : 'default'}>
                  {status.pexels === 'Configured' ? 'Active' : 'Missing'}
                </Badge>
              </div>
              <div className="flex gap-2">
                <Input 
                  type="password" 
                  value={pexels} 
                  onChange={e => setPexels(e.target.value)} 
                  placeholder={status.pexels === 'Configured' ? "********" : "Enter Key"} 
                />
                <Button onClick={saveMedia}>Save</Button>
                {status.pexels === 'Configured' && (
                  <Button variant="ghost" onClick={() => remove('pexels')} className="px-3 text-red-500 hover:text-red-600">
                    <Trash2 className="w-4 h-4" />
                  </Button>
                )}
              </div>
            </div>

            <div>
              <div className="flex justify-between items-center mb-2">
                <label className="text-sm font-semibold text-foreground">Pixabay API Key</label>
                <Badge variant={status.pixabay === 'Configured' ? 'success' : 'default'}>
                  {status.pixabay === 'Configured' ? 'Active' : 'Missing'}
                </Badge>
              </div>
              <div className="flex gap-2">
                <Input 
                  type="password" 
                  value={pixabay} 
                  onChange={e => setPixabay(e.target.value)} 
                  placeholder={status.pixabay === 'Configured' ? "********" : "Enter Key"} 
                />
                <Button onClick={saveMedia}>Save</Button>
                {status.pixabay === 'Configured' && (
                  <Button variant="ghost" onClick={() => remove('pixabay')} className="px-3 text-red-500 hover:text-red-600">
                    <Trash2 className="w-4 h-4" />
                  </Button>
                )}
              </div>
            </div>

            <div className="bg-muted p-4 rounded-lg">
              <h4 className="text-sm font-semibold mb-1 text-foreground">Openverse & Wikimedia</h4>
              <p className="text-xs text-muted-foreground leading-relaxed">
                These providers are fully free and require no keys. They remain always active as fallbacks.
              </p>
            </div>
          </Card>
        </div>

        {/* LLM */}
        <div className="space-y-4">
          <div className="flex items-center gap-2 px-1">
            <Bot className="w-5 h-5 text-primary" />
            <h3 className="font-bold text-xl text-foreground">AI Providers (Multi-Failover)</h3>
          </div>
          
          <p className="text-xs text-muted-foreground px-1">
            The app tries enabled providers in order from top to bottom. It falls back on failure automatically.
          </p>

          <div className="space-y-4">
            {llmProviders.map((p, i) => (
              <Card key={p.provider} className="p-4 relative">
                <div className="flex items-center justify-between mb-3 border-b pb-2">
                  <div className="flex items-center gap-3">
                    <input 
                      type="checkbox" 
                      checked={p.enabled} 
                      onChange={e => {
                        const next = [...llmProviders];
                        next[i].enabled = e.target.checked;
                        setLlmProviders(next);
                      }}
                      className="rounded border-input text-primary focus:ring-primary w-4 h-4 cursor-pointer"
                    />
                    <h4 className="font-semibold text-sm text-foreground">{PROVIDER_NAMES[p.provider] || p.provider}</h4>
                    <span className="text-xs text-muted-foreground">Priority {i + 1}</span>
                  </div>
                  <div className="flex items-center gap-1">
                    <Button variant="ghost" size="sm" onClick={() => moveProvider(i, -1)} disabled={i === 0} className="h-6 w-6">
                      <ArrowUp className="w-4 h-4" />
                    </Button>
                    <Button variant="ghost" size="sm" onClick={() => moveProvider(i, 1)} disabled={i === llmProviders.length - 1} className="h-6 w-6">
                      <ArrowDown className="w-4 h-4" />
                    </Button>
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-3 mb-3">
                  <div>
                    <label className="block text-[10px] font-semibold text-foreground mb-1 uppercase tracking-wider">API Key</label>
                    <Input 
                      type="password" 
                      value={p.api_key || ''} 
                      onChange={e => {
                        const next = [...llmProviders];
                        next[i].api_key = e.target.value;
                        setLlmProviders(next);
                      }}
                      placeholder={p.status === 'Configured' ? '********' : (p.provider === 'ollama' ? 'Optional' : 'sk-...')}
                      className="h-8 text-xs"
                    />
                  </div>
                  <div>
                    <label className="block text-[10px] font-semibold text-foreground mb-1 uppercase tracking-wider">Model</label>
                    <Input 
                      type="text" 
                      value={p.model || ''} 
                      onChange={e => {
                        const next = [...llmProviders];
                        next[i].model = e.target.value;
                        setLlmProviders(next);
                      }}
                      placeholder="Model name"
                      className="h-8 text-xs"
                    />
                  </div>
                </div>
                
                <div className="flex items-center justify-between mt-2 pt-2 border-t border-muted">
                  <Button variant="secondary" size="sm" onClick={() => testLlm(i)} disabled={testStatus[p.provider]?.loading} className="h-7 text-xs px-3">
                    <Activity className="w-3 h-3 mr-1" /> Test
                  </Button>
                  <div className="text-xs">
                    {testStatus[p.provider]?.loading && <span className="text-muted-foreground animate-pulse">Testing...</span>}
                    {testStatus[p.provider]?.ok === true && <span className="text-green-500 font-medium">? Works</span>}
                    {testStatus[p.provider]?.ok === false && (
                      <span className="text-red-500">? {testStatus[p.provider].status ? "HTTP " + testStatus[p.provider].status : "Error"}: {testStatus[p.provider].msg}</span>
                    )}
                  </div>
                </div>
              </Card>
            ))}

            <Card className="p-4 mt-6">
              <h4 className="font-semibold text-sm text-foreground mb-3">Visual Verification</h4>
              <div className="space-y-4">
                <label className="flex items-center gap-2 text-sm text-foreground cursor-pointer">
                  <input 
                    type="checkbox" 
                    checked={enableVisualVerification} 
                    onChange={e => setEnableVisualVerification(e.target.checked)}
                    className="rounded border-input text-primary focus:ring-primary"
                  />
                  AI clip verification (accuracy)
                </label>

                {enableVisualVerification && (
                  <div>
                    <label className="block text-xs font-semibold text-foreground mb-1.5">Vision Model</label>
                    <Input 
                      type="text" 
                      value={visionModel} 
                      onChange={e => setVisionModel(e.target.value)} 
                      placeholder="e.g. google/gemini-2.0-flash-exp:free"
                      className="text-xs"
                    />
                  </div>
                )}
              </div>
            </Card>

            <div className="flex gap-2 pt-4">
              <Button onClick={saveLlm} className="flex-1">Save All LLM Settings</Button>
              <Button variant="secondary" onClick={() => remove('llm')} className="px-4 text-red-500 hover:text-red-600">
                Clear All
              </Button>
            </div>
          </div>
        </div>

      </div>
    </div>
  );
}
