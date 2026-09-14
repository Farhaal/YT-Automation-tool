import React from 'react';
import { Loader2, Terminal, CheckCircle2 } from 'lucide-react';
import { Card } from './ui';

export default function ProcessingView({ job, logsEndRef }: { job: any, logsEndRef: React.RefObject<HTMLDivElement | null> }) {
  
  const steps = [
    { key: "Synthesizing audio", label: "Synthesizing Audio" },
    { key: "Transcribing", label: "Transcribing" },
    { key: "Segmenting scenes", label: "Segmenting Scenes" },
    { key: "Finding assets", label: "Finding Assets" },
    { key: "Building timeline", label: "Building Timeline" },
    { key: "Rendering draft", label: "Rendering Video" }
  ];

  // Derive current step index based on job.stage
  const currentStepIndex = steps.findIndex(s => s.key === job.stage);
  
  return (
    <div className="max-w-4xl mx-auto space-y-8 animate-in fade-in slide-in-from-bottom-4 pt-8">
      
      <div className="text-center space-y-2">
        <h2 className="text-3xl font-extrabold tracking-tight text-foreground">Generating Video...</h2>
        <p className="text-muted-foreground">Please wait while our engine builds your project.</p>
      </div>

      <Card className="p-8">
        {/* Stepper */}
        <div className="relative mb-12">
          <div className="absolute top-1/2 left-0 w-full h-1 bg-muted -translate-y-1/2 rounded-full overflow-hidden">
            <div 
              className="h-full bg-primary transition-all duration-500 ease-out"
              style={{ width: `${job.progress}%` }}
            />
          </div>
          
          <div className="relative flex justify-between">
            {steps.map((step, idx) => {
              const isCompleted = currentStepIndex > idx || job.progress === 100;
              const isCurrent = currentStepIndex === idx;
              return (
                <div key={step.key} className="flex flex-col items-center gap-2 relative z-10 w-16">
                  <div className={`w-8 h-8 rounded-full flex items-center justify-center transition-colors duration-300 ${
                    isCompleted ? 'bg-primary text-primary-foreground' : 
                    isCurrent ? 'bg-primary text-primary-foreground ring-4 ring-primary/20' : 
                    'bg-muted text-muted-foreground border-2 border-background'
                  }`}>
                    {isCompleted ? <CheckCircle2 className="w-5 h-5" /> : (isCurrent ? <Loader2 className="w-4 h-4 animate-spin" /> : <div className="w-2.5 h-2.5 rounded-full bg-muted-foreground/30" />)}
                  </div>
                  <span className={`text-[10px] font-semibold uppercase tracking-wider text-center ${isCurrent ? 'text-primary' : 'text-muted-foreground'}`}>
                    {step.label}
                  </span>
                </div>
              );
            })}
          </div>
        </div>

        {/* Terminal */}
        <div className="bg-[#0D0D0D] rounded-xl overflow-hidden border border-gray-800 shadow-2xl">
          <div className="flex items-center gap-2 px-4 py-3 border-b border-gray-800 bg-[#161616]">
            <Terminal className="w-4 h-4 text-gray-500" />
            <span className="text-xs font-mono text-gray-400 font-semibold tracking-wide">SYSTEM_LOGS</span>
            <div className="ml-auto flex gap-1.5">
              <div className="w-2.5 h-2.5 rounded-full bg-red-500/50" />
              <div className="w-2.5 h-2.5 rounded-full bg-yellow-500/50" />
              <div className="w-2.5 h-2.5 rounded-full bg-green-500/50" />
            </div>
          </div>
          <div className="p-5 font-mono text-[13px] h-64 overflow-y-auto leading-relaxed">
            {job.logs && job.logs.length > 0 ? (
              <div className="space-y-1.5">
                {job.logs.map((log: string, i: number) => (
                  <div key={i} className="text-emerald-400 break-words">
                    <span className="text-gray-600 mr-3 select-none">[{new Date().toLocaleTimeString()}]</span>
                    {log}
                  </div>
                ))}
                {job.progress < 100 && (
                  <div className="text-gray-500 flex items-center gap-2 mt-4 animate-pulse">
                    <span className="w-2 h-4 bg-gray-500 block animate-bounce" /> Processing...
                  </div>
                )}
                <div ref={logsEndRef} />
              </div>
            ) : (
              <div className="text-gray-600 flex items-center gap-2">
                <span className="w-2 h-4 bg-gray-600 block animate-pulse" /> Initializing engine...
              </div>
            )}
          </div>
        </div>
      </Card>
    </div>
  );
}
