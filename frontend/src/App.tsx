import { useState } from 'react';
import { Settings, Video } from 'lucide-react';
import SettingsView from './SettingsView';
import CreatorView from './CreatorView';
import EditorView from './EditorView';

export default function App() {
  const [view, setView] = useState<'home' | 'settings' | 'editor'>('home');
  const [jobId, setJobId] = useState<string | null>(null);
  
  return (
    <div className="min-h-screen flex flex-col font-sans">
      <header className="bg-white shadow-sm px-6 py-4 flex justify-between items-center">
        <h1 className="text-xl font-bold text-blue-600 flex items-center gap-2 cursor-pointer" onClick={() => setView('home')}>
          <Video className="w-6 h-6" /> OpenReel
        </h1>
        <nav className="flex gap-4">
          <button onClick={() => setView('home')} className={`px-3 py-1 rounded ${view === 'home' ? 'bg-blue-100 text-blue-700' : 'text-gray-600 hover:bg-gray-100'}`}>Creator</button>
          {jobId && <button onClick={() => setView('editor')} className={`px-3 py-1 rounded ${view === 'editor' ? 'bg-blue-100 text-blue-700' : 'text-gray-600 hover:bg-gray-100'}`}>Editor</button>}
          <button onClick={() => setView('settings')} className={`px-3 py-1 rounded flex items-center gap-2 ${view === 'settings' ? 'bg-blue-100 text-blue-700' : 'text-gray-600 hover:bg-gray-100'}`}>
            <Settings className="w-4 h-4" /> Settings
          </button>
        </nav>
      </header>

      <main className="flex-1 p-6 max-w-5xl mx-auto w-full">
        {view === 'settings' && <SettingsView />}
        {view === 'home' && <CreatorView onJobCreated={(id) => { setJobId(id); setView('editor'); }} />}
        {view === 'editor' && jobId && <EditorView jobId={jobId} />}
      </main>
    </div>
  );
}
