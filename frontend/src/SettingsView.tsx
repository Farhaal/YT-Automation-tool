import { useState, useEffect } from 'react';
import { Key, Bot, Trash2 } from 'lucide-react';
import { Card, Button, Badge, Input, useToast } from './ui';

export default function SettingsView() {
  const [status, setStatus] = useState<any>({});
  
  const [pexels, setPexels] = useState('');
  const [pixabay, setPixabay] = useState('');
  
  const [llmProvider, setLlmProvider] = useState('');
  const [llmApiKey, setLlmApiKey] = useState('');
  const [llmModel, setLlmModel] = useState('');
  const [llmBaseUrl, setLlmBaseUrl] = useState('');

  const { toast } = useToast();

  const load = () => {
    fetch('http://localhost:8000/settings')
      .then(r => r.json())
      .then(data => {
        setStatus(data);
        if (data.llm_provider) setLlmProvider(data.llm_provider);
        if (data.llm_model) setLlmModel(data.llm_model);
        if (data.llm_base_url) setLlmBaseUrl(data.llm_base_url);
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
          llm_provider: llmProvider,
          llm_api_key: llmApiKey,
          llm_model: llmModel,
          llm_base_url: llmBaseUrl
        })
      });
      setLlmApiKey('');
      load();
      toast("LLM settings saved", "success");
    } catch {
      toast("Error saving LLM config", "error");
    }
  };

  const remove = async (provider: string) => {
    try {
      await fetch(`http://localhost:8000/settings/${provider}`, { method: 'DELETE' });
      if (provider === 'llm') {
        setLlmProvider('');
        setLlmModel('');
        setLlmBaseUrl('');
      }
      load();
      toast(`Cleared ${provider} config`, "success");
    } catch {
      toast("Error clearing config", "error");
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
            <h3 className="font-bold text-xl text-foreground">AI Model (Optional)</h3>
          </div>

          <Card className="p-5 space-y-5">
            <div className="flex justify-between items-center border-b pb-4">
              <div>
                <h4 className="font-semibold text-sm text-foreground">Topic-Aware Context</h4>
                <p className="text-xs text-muted-foreground mt-1 max-w-[240px]">Overrides the default NLP extractor for smarter visual queries.</p>
              </div>
              <Badge variant={status.llm_api_key === 'Configured' ? 'success' : 'default'}>
                {status.llm_api_key === 'Configured' ? 'Active' : 'Inactive'}
              </Badge>
            </div>

            <div className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-foreground mb-1.5">Provider</label>
                <select 
                  value={llmProvider} 
                  onChange={e => setLlmProvider(e.target.value)} 
                  className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-ring"
                >
                  <option value="">-- Select --</option>
                  <option value="openai">OpenAI</option>
                  <option value="openrouter">OpenRouter</option>
                  <option value="groq">Groq</option>
                  <option value="ollama">Ollama (Local)</option>
                </select>
              </div>
              
              <div>
                <label className="block text-xs font-semibold text-foreground mb-1.5">API Key</label>
                <Input 
                  type="password" 
                  value={llmApiKey} 
                  onChange={e => setLlmApiKey(e.target.value)} 
                  placeholder={status.llm_api_key === 'Configured' ? '********' : 'sk-... (Optional for Ollama)'}
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-semibold text-foreground mb-1.5">Model Override</label>
                  <Input 
                    type="text" 
                    value={llmModel} 
                    onChange={e => setLlmModel(e.target.value)} 
                    placeholder="e.g. gpt-4o-mini"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-foreground mb-1.5">Base URL</label>
                  <Input 
                    type="text" 
                    value={llmBaseUrl} 
                    onChange={e => setLlmBaseUrl(e.target.value)} 
                    placeholder="Custom endpoint"
                  />
                </div>
              </div>

              <div className="flex gap-2 pt-2">
                <Button onClick={saveLlm} className="flex-1">Save Configuration</Button>
                {status.llm_api_key === 'Configured' && (
                  <Button variant="ghost" onClick={() => remove('llm')} className="px-3 text-red-500 hover:text-red-600 border border-input">
                    <Trash2 className="w-4 h-4" />
                  </Button>
                )}
              </div>
            </div>
          </Card>
        </div>

      </div>
    </div>
  );
}