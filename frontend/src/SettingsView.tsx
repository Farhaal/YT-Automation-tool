import { useState, useEffect } from 'react';

export default function SettingsView() {
  const [status, setStatus] = useState<any>({});
  const [pexels, setPexels] = useState('');
  const [pixabay, setPixabay] = useState('');

  const load = () => {
    fetch('http://localhost:8000/settings')
      .then(r => r.json())
      .then(setStatus);
  };

  useEffect(() => { load(); }, []);

  const save = () => {
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

  const remove = (provider: string) => {
    fetch(`http://localhost:8000/settings/${provider}`, { method: 'DELETE' }).then(load);
  };

  return (
    <div className="bg-white p-6 rounded shadow max-w-2xl mx-auto">
      <h2 className="text-2xl font-bold mb-6">Provider Settings</h2>
      
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
            <button onClick={save} className="bg-blue-600 text-white px-4 py-2 rounded">Save</button>
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
            <button onClick={save} className="bg-blue-600 text-white px-4 py-2 rounded">Save</button>
            <button onClick={() => remove('pixabay')} className="bg-red-100 text-red-600 px-4 py-2 rounded">Clear</button>
          </div>
        </div>

        <div className="border p-4 rounded bg-gray-50">
          <h3 className="font-semibold text-lg mb-2">Openverse & Wikimedia</h3>
          <p className="text-sm text-gray-600">These providers are fully free and require no keys. They are always active.</p>
        </div>
      </div>
    </div>
  );
}
