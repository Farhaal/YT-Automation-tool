import { useState } from 'react';
import { Settings, Video, Wand2, Film } from 'lucide-react';
import SettingsView from './SettingsView';
import CreatorView from './CreatorView';
import EditorView from './EditorView';

export default function App() {
  const [view, setView] = useState<'home' | 'settings' | 'editor'>('home');
  const [jobId, setJobId] = useState<string | null>(null);

  return (
    <div className="flex h-screen w-full bg-background text-foreground overflow-hidden">
      {/* Sidebar Navigation */}
      <aside className="w-64 border-r bg-card flex flex-col justify-between flex-shrink-0 z-10">
        <div>
          <div className="h-16 flex items-center px-6 border-b">
            <div className="flex items-center gap-2 cursor-pointer group" onClick={() => setView('home')}>
              <div className="bg-primary p-1.5 rounded-lg group-hover:scale-105 transition-transform">
                <Video className="w-5 h-5 text-primary-foreground" />
              </div>
              <h1 className="text-xl font-bold tracking-tight">OpenReel</h1>
            </div>
          </div>
          <nav className="p-4 space-y-1.5">
            <button
              onClick={() => setView('home')}
              className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                view === 'home' ? 'bg-primary/10 text-primary' : 'text-muted-foreground hover:bg-muted hover:text-foreground'
              }`}
            >
              <Wand2 className="w-5 h-5" />
              Create
            </button>
            {jobId && (
              <button
                onClick={() => setView('editor')}
                className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                  view === 'editor' ? 'bg-primary/10 text-primary' : 'text-muted-foreground hover:bg-muted hover:text-foreground'
                }`}
              >
                <Film className="w-5 h-5" />
                Editor
              </button>
            )}
          </nav>
        </div>
        <div className="p-4 border-t">
          <button
            onClick={() => setView('settings')}
            className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors ${
              view === 'settings' ? 'bg-primary/10 text-primary' : 'text-muted-foreground hover:bg-muted hover:text-foreground'
            }`}
          >
            <Settings className="w-5 h-5" />
            Settings
          </button>
        </div>
      </aside>

      {/* Main Content Area */}
      <main className="flex-1 h-full overflow-y-auto relative">
        <div className="max-w-6xl mx-auto p-6 md:p-8 min-h-full">
          {view === 'settings' && <SettingsView />}
          {view === 'home' && (
            <CreatorView 
              onJobCreated={(id) => { 
                setJobId(id); 
                setView('editor'); 
              }} 
            />
          )}
          {view === 'editor' && jobId && <EditorView jobId={jobId} />}
        </div>
      </main>
    </div>
  );
}
