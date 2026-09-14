import { useState, useEffect } from 'react';

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
    <div className="bg-white p-6 rounded shadow max-w-2xl mx-auto space-y-8">
      
      {/* Media Providers */}
      <div>
        <h2 className="text-2xl font-bold mb-6">Stock Media Providers</h2>
        <div className="space-y-6">
          <div className="border p-4 rounded">
            <div className="flex justify-between items-center mb-2">
              <h3 className="font-semibold text-lg">Pexels API Key</h3>
              <span className={`px-2 py-1 text-xs rounded ${status.pexels === 'Configured' ? 'bg-green-100 text-green-700' : 'bg-gray-100'}`}>
                {status.pexels || 'Loading...'}
              </span>
            </div>
            <div className="flex gap-2">
              <input type="password" value={pexels} onChange={e => setPexels(e.target.value)} placeholder="Enter Pexels Key" className="border p-2 rounded flex-1" />
              <button onClick={saveMedia} className="bg-blue-600 text-white px-4 py-2 rounded">Save</button>
              <button onClick={() => remove('pexels')} className="bg-red-100 text-red-600 px-4 py-2 rounded">Clear</button>
            </div>
          </div>

          <div className="border p-4 rounded">
            <div className="flex justify-between items-center mb-2">
              <h3 className="font-semibold text-lg">Pixabay API Key</h3>
              <span className={`px-2 py-1 text-xs rounded ${status.pixabay === 'Configured' ? 'bg-green-100 text-green-700' : 'bg-gray-100'}`}>
                {status.pixabay || 'Loading...'}
              </span>
            </div>
            <div className="flex gap-2">
              <input type="password" value={pixabay} onChange={e => setPixabay(e.target.value)} placeholder="Enter Pixabay Key" className="border p-2 rounded flex-1" />
              <button onClick={saveMedia} className="bg-blue-600 text-white px-4 py-2 rounded">Save</button>
              <button onClick={() => remove('pixabay')} className="bg-red-100 text-red-600 px-4 py-2 rounded">Clear</button>
            </div>
          </div>

          <div className="border p-4 rounded bg-gray-50">
            <h3 className="font-semibold text-lg mb-2">Openverse & Wikimedia</h3>
            <p className="text-sm text-gray-600">These providers are fully free and require no keys. They are always active.</p>
          </div>
        </div>
      </div>

      <hr />

      {/* Optional LLM */}
      <div>
        <h2 className="text-2xl font-bold mb-2">Optional AI Model</h2>
        <p className="text-sm text-gray-500 mb-6">
          For smarter visual search query extraction. If skipped, standard fast NLP (spaCy + YAKE) is used instead. Your key is never shared or logged.
        </p>

        <div className="border p-4 rounded bg-indigo-50 border-indigo-100">
          <div className="flex justify-between items-center mb-4">
            <h3 className="font-semibold text-lg text-indigo-900">LLM Configuration</h3>
            <span className={`px-2 py-1 text-xs rounded ${status.llm_api_key === 'Configured' ? 'bg-green-100 text-green-700' : 'bg-gray-200 text-gray-600'}`}>
              {status.llm_api_key || 'Loading...'}
            </span>
          </div>

          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium mb-1">Provider</label>
              <select value={llmProvider} onChange={e => setLlmProvider(e.target.value)} className="w-full border p-2 rounded focus:ring-2 focus:ring-indigo-500 focus:outline-none">
                <option value="">-- Select Provider --</option>
                <option value="openai">OpenAI</option>
                <option value="openrouter">OpenRouter</option>
                <option value="groq">Groq</option>
                <option value="ollama">Ollama (Local)</option>
              </select>
            </div>
            
            <div>
              <label className="block text-sm font-medium mb-1">API Key</label>
              <input 
                type="password" 
                value={llmApiKey} 
                onChange={e => setLlmApiKey(e.target.value)} 
                placeholder={status.llm_api_key === 'Configured' ? '******** (configured)' : 'Enter API Key (Optional for Ollama)'}
                className="w-full border p-2 rounded focus:ring-2 focus:ring-indigo-500 focus:outline-none" 
              />
            </div>

            <div className="flex gap-4">
              <div className="flex-1">
                <label className="block text-sm font-medium mb-1">Model Name (Optional)</label>
                <input 
                  type="text" 
                  value={llmModel} 
                  onChange={e => setLlmModel(e.target.value)} 
                  placeholder="e.g. gpt-4o-mini"
                  className="w-full border p-2 rounded focus:ring-2 focus:ring-indigo-500 focus:outline-none" 
                />
              </div>
              <div className="flex-1">
                <label className="block text-sm font-medium mb-1">Base URL (Optional)</label>
                <input 
                  type="text" 
                  value={llmBaseUrl} 
                  onChange={e => setLlmBaseUrl(e.target.value)} 
                  placeholder="Custom API endpoint"
                  className="w-full border p-2 rounded focus:ring-2 focus:ring-indigo-500 focus:outline-none" 
                />
              </div>
            </div>

            <div className="flex gap-2 pt-2">
              <button onClick={saveLlm} className="bg-indigo-600 text-white px-6 py-2 rounded font-medium hover:bg-indigo-700">Save LLM Settings</button>
              <button onClick={() => remove('llm')} className="bg-gray-200 text-gray-700 px-6 py-2 rounded font-medium hover:bg-gray-300">Clear</button>
            </div>
          </div>
        </div>
      </div>

    </div>
  );
}