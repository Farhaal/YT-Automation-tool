import { useState, useEffect } from 'react';
import { Key, Bot, Settings2, Trash2, CheckCircle2 } from 'lucide-react';

export default function SettingsView() {
  const [status, setStatus] = useState<any>({});
  
  // Media Keys
  const [pexels, setPexels] = useState('');
  const [pixabay, setPixabay] = useState('');
  
  // LLM Settings
  const [llmProvider, setLlmProvider] = useState('');
  const [llmApiKey, setLlmApiKey] = useState('');
  const [llmModel, setLlmModel] = useState('');
  const [llmBaseUrl, setLlmBaseUrl] = useState('');

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

  const saveMedia = () => {
    fetch('http://localhost:8000/settings', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ pexels_key: pexels, pixabay_key: pixabay })
    }).then(() => {
      setPexels('');
      setPixabay('');
      load();
    });
  };

  const saveLlm = () => {
    fetch('http://localhost:8000/settings', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ 
        llm_provider: llmProvider,
        llm_api_key: llmApiKey,
        llm_model: llmModel,
        llm_base_url: llmBaseUrl
      })
    }).then(() => {
      setLlmApiKey('');
      load();
    });
  };

  const remove = (provider: string) => {
    fetch(`http://localhost:8000/settings/${provider}`, { method: 'DELETE' }).then(() => {
      if (provider === 'llm') {
        setLlmProvider('');
        setLlmModel('');
        setLlmBaseUrl('');
      }
      load();
    });
  };

  return (
    <div className="space-y-8 animate-in fade-in slide-in-from-bottom-4">
      
      <div className="mb-8">
        <h2 className="text-3xl font-extrabold tracking-tight text-gray-900 mb-2">Settings</h2>
        <p className="text-gray-500">Configure your API keys and models locally.</p>
      </div>

      <div className="grid md:grid-cols-2 gap-8">
        
        {/* Media Providers */}
        <div className="space-y-6">
          <div className="flex items-center gap-2 pb-2 border-b border-gray-200">
            <Settings2 className="w-5 h-5 text-gray-400" />
            <h3 className="text-lg font-bold text-gray-900">Stock Media</h3>
          </div>

          <div className="bg-white border border-gray-200 rounded-xl p-5 shadow-sm space-y-4 transition-all hover:border-gray-300">
            <div className="flex justify-between items-center">
              <label className="text-sm font-semibold text-gray-900">Pexels API Key</label>
              {status.pexels === 'Configured' ? (
                <span className="flex items-center gap-1 text-[11px] font-medium tracking-wide uppercase text-green-700 bg-green-50 px-2 py-0.5 rounded-full"><CheckCircle2 className="w-3 h-3" /> Active</span>
              ) : (
                <span className="text-[11px] font-medium tracking-wide uppercase text-gray-500 bg-gray-100 px-2 py-0.5 rounded-full">Missing</span>
              )}
            </div>
            <div className="flex gap-2">
              <input type="password" value={pexels} onChange={e => setPexels(e.target.value)} placeholder="********" className="border border-gray-200 p-2.5 rounded-lg flex-1 text-sm bg-gray-50 focus:bg-white focus:outline-none focus:ring-2 focus:ring-black transition-colors" />
              <button onClick={saveMedia} className="bg-black text-white px-4 py-2.5 rounded-lg font-medium text-sm hover:bg-gray-800 transition-colors">Save</button>
              {status.pexels === 'Configured' && <button onClick={() => remove('pexels')} className="bg-white border border-gray-200 text-gray-500 hover:text-red-600 hover:bg-red-50 p-2.5 rounded-lg transition-colors"><Trash2 className="w-4 h-4" /></button>}
            </div>
          </div>

          <div className="bg-white border border-gray-200 rounded-xl p-5 shadow-sm space-y-4 transition-all hover:border-gray-300">
            <div className="flex justify-between items-center">
              <label className="text-sm font-semibold text-gray-900">Pixabay API Key</label>
              {status.pixabay === 'Configured' ? (
                <span className="flex items-center gap-1 text-[11px] font-medium tracking-wide uppercase text-green-700 bg-green-50 px-2 py-0.5 rounded-full"><CheckCircle2 className="w-3 h-3" /> Active</span>
              ) : (
                <span className="text-[11px] font-medium tracking-wide uppercase text-gray-500 bg-gray-100 px-2 py-0.5 rounded-full">Missing</span>
              )}
            </div>
            <div className="flex gap-2">
              <input type="password" value={pixabay} onChange={e => setPixabay(e.target.value)} placeholder="********" className="border border-gray-200 p-2.5 rounded-lg flex-1 text-sm bg-gray-50 focus:bg-white focus:outline-none focus:ring-2 focus:ring-black transition-colors" />
              <button onClick={saveMedia} className="bg-black text-white px-4 py-2.5 rounded-lg font-medium text-sm hover:bg-gray-800 transition-colors">Save</button>
              {status.pixabay === 'Configured' && <button onClick={() => remove('pixabay')} className="bg-white border border-gray-200 text-gray-500 hover:text-red-600 hover:bg-red-50 p-2.5 rounded-lg transition-colors"><Trash2 className="w-4 h-4" /></button>}
            </div>
          </div>

          <div className="p-4 rounded-xl bg-gray-50 border border-gray-100 flex items-start gap-3">
            <div className="mt-0.5 bg-gray-200 p-1.5 rounded-md"><Key className="w-4 h-4 text-gray-600" /></div>
            <div>
              <h3 className="font-semibold text-sm text-gray-900 mb-1">Openverse & Wikimedia</h3>
              <p className="text-xs text-gray-500 leading-relaxed">These providers are fully free and require no keys. They are always active as fallbacks.</p>
            </div>
          </div>
        </div>

        {/* Optional LLM */}
        <div className="space-y-6">
          <div className="flex items-center gap-2 pb-2 border-b border-gray-200">
            <Bot className="w-5 h-5 text-gray-400" />
            <h3 className="text-lg font-bold text-gray-900">Optional AI Model</h3>
          </div>

          <div className="bg-white border border-gray-200 rounded-xl p-5 shadow-sm space-y-5 transition-all hover:border-gray-300">
            <div className="flex justify-between items-center border-b border-gray-100 pb-4">
              <div>
                <h3 className="font-semibold text-sm text-gray-900">LLM Configuration</h3>
                <p className="text-xs text-gray-500 mt-1 max-w-[250px]">Enables smart topic-aware visual queries. Overrides default spaCy+YAKE.</p>
              </div>
              {status.llm_api_key === 'Configured' ? (
                <span className="flex items-center gap-1 text-[11px] font-medium tracking-wide uppercase text-blue-700 bg-blue-50 px-2 py-0.5 rounded-full"><CheckCircle2 className="w-3 h-3" /> Active</span>
              ) : (
                <span className="text-[11px] font-medium tracking-wide uppercase text-gray-500 bg-gray-100 px-2 py-0.5 rounded-full">Inactive</span>
              )}
            </div>

            <div className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-gray-700 mb-1.5">Provider</label>
                <select value={llmProvider} onChange={e => setLlmProvider(e.target.value)} className="w-full border border-gray-200 rounded-lg p-2.5 text-sm bg-gray-50 focus:bg-white focus:outline-none focus:ring-2 focus:ring-black transition-colors cursor-pointer">
                  <option value="">-- Select Provider --</option>
                  <option value="openai">OpenAI</option>
                  <option value="openrouter">OpenRouter</option>
                  <option value="groq">Groq</option>
                  <option value="ollama">Ollama (Local)</option>
                </select>
              </div>
              
              <div>
                <label className="block text-xs font-semibold text-gray-700 mb-1.5">API Key</label>
                <input 
                  type="password" 
                  value={llmApiKey} 
                  onChange={e => setLlmApiKey(e.target.value)} 
                  placeholder={status.llm_api_key === 'Configured' ? '******** (configured)' : 'sk-... (Optional for Ollama)'}
                  className="w-full border border-gray-200 rounded-lg p-2.5 text-sm bg-gray-50 focus:bg-white focus:outline-none focus:ring-2 focus:ring-black transition-colors" 
                />
              </div>

              <div className="flex gap-3">
                <div className="flex-1">
                  <label className="block text-xs font-semibold text-gray-700 mb-1.5">Model Override</label>
                  <input 
                    type="text" 
                    value={llmModel} 
                    onChange={e => setLlmModel(e.target.value)} 
                    placeholder="e.g. gpt-4o-mini"
                    className="w-full border border-gray-200 rounded-lg p-2.5 text-sm bg-gray-50 focus:bg-white focus:outline-none focus:ring-2 focus:ring-black transition-colors" 
                  />
                </div>
                <div className="flex-1">
                  <label className="block text-xs font-semibold text-gray-700 mb-1.5">Base URL</label>
                  <input 
                    type="text" 
                    value={llmBaseUrl} 
                    onChange={e => setLlmBaseUrl(e.target.value)} 
                    placeholder="Custom endpoint"
                    className="w-full border border-gray-200 rounded-lg p-2.5 text-sm bg-gray-50 focus:bg-white focus:outline-none focus:ring-2 focus:ring-black transition-colors" 
                  />
                </div>
              </div>

              <div className="flex gap-2 pt-3">
                <button onClick={saveLlm} className="bg-black text-white px-5 py-2.5 rounded-lg font-medium text-sm flex-1 hover:bg-gray-800 transition-colors">Save LLM Configuration</button>
                {status.llm_api_key === 'Configured' && <button onClick={() => remove('llm')} className="bg-white border border-gray-200 text-gray-500 hover:text-red-600 hover:bg-red-50 p-2.5 rounded-lg transition-colors"><Trash2 className="w-4 h-4" /></button>}
              </div>
            </div>
          </div>
        </div>

      </div>
    </div>
  );
}