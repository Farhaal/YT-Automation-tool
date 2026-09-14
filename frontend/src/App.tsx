import { useState } from 'react';
import { Settings, Video, Wand2, Layout } from 'lucide-react';
import SettingsView from './SettingsView';
import CreatorView from './CreatorView';
import EditorView from './EditorView';

export default function App() {
  const [view, setView] = useState<'home' | 'settings' | 'editor'>('home');
  const [jobId, setJobId] = useState<string | null>(null);
  
  return (
    <div className="min-h-screen flex flex-col font-sans bg-[#FAFAFA] text-slate-900">
      <header className="bg-white border-b border-gray-200 px-6 py-4 flex justify-between items-center sticky top-0 z-50">
        <div className="flex items-center gap-2 cursor-pointer group" onClick={() => setView('home')}>
          <div className="bg-black p-1.5 rounded-md group-hover:scale-105 transition-transform">
            <Video className="w-5 h-5 text-white" />
          </div>
          <h1 className="text-xl font-bold tracking-tight">OpenReel</h1>
        </div>
        <nav className="flex gap-2">
          <button 
            onClick={() => setView('home')} 
            className={`px-3 py-1.5 rounded-md text-sm font-medium transition-colors flex items-center gap-2 ${view === 'home' ? 'bg-black text-white' : 'text-gray-600 hover:bg-gray-100 hover:text-black'}`}
          >
            <Wand2 className="w-4 h-4" /> Create
          </button>
          {jobId && (
            <button 
              onClick={() => setView('editor')} 
              className={`px-3 py-1.5 rounded-md text-sm font-medium transition-colors flex items-center gap-2 ${view === 'editor' ? 'bg-black text-white' : 'text-gray-600 hover:bg-gray-100 hover:text-black'}`}
            >
              <Layout className="w-4 h-4" /> Editor
            </button>
          )}
          <button 
            onClick={() => setView('settings')} 
            className={`px-3 py-1.5 rounded-md text-sm font-medium transition-colors flex items-center gap-2 ${view === 'settings' ? 'bg-black text-white' : 'text-gray-600 hover:bg-gray-100 hover:text-black'}`}
          >
            <Settings className="w-4 h-4" /> Settings
          </button>
        </nav>
      </header>

      <main className="flex-1 w-full flex flex-col pb-12">
        {view === 'settings' && <div className="max-w-5xl mx-auto w-full p-6 mt-6"><SettingsView /></div>}
        {view === 'home' && <div className="max-w-5xl mx-auto w-full p-6 mt-6"><CreatorView onJobCreated={(id) => { setJobId(id); setView('editor'); }} /></div>}
        {view === 'editor' && jobId && <EditorView jobId={jobId} />}
      </main>
    </div>
  );
}
