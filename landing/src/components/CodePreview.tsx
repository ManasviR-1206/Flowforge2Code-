import React, { useState } from 'react';

interface CodePreviewProps {
  parallaxX?: number;
  parallaxY?: number;
}

export const CodePreview: React.FC<CodePreviewProps> = ({ parallaxX = 0, parallaxY = 0 }) => {
  const [isRunning, setIsRunning] = useState(false);
  const [showOutput, setShowOutput] = useState(false);
  const [copied, setCopied] = useState(false);

  const handleRun = () => {
    setIsRunning(true);
    setShowOutput(false);
    setTimeout(() => {
      setIsRunning(false);
      setShowOutput(true);
    }, 600);
  };

  const handleCopy = () => {
    const code = `n = int(input("Enter n: "))\n\nif n > 0:\n    print("Positive")\nelse:\n    print("Negative")`;
    navigator.clipboard.writeText(code);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div
      className="relative z-10 w-full max-w-xs sm:max-w-sm transition-transform duration-200 ease-out"
      style={{
        transform: `translate3d(${parallaxX}px, ${parallaxY}px, 0px)`,
      }}
    >
      {/* Visual Story Badge Header */}
      <div className="flex items-center justify-center space-x-1.5 mb-2 font-mono text-[10px] text-cyan-300">
        <span className="px-2 py-0.5 rounded bg-cyan-950/70 border border-cyan-500/30">FLOWCHART</span>
        <span className="text-purple-400 font-bold">➔</span>
        <span className="px-2 py-0.5 rounded bg-purple-950/70 border border-purple-500/30 font-bold text-purple-300">AI ENGINE</span>
        <span className="text-purple-400 font-bold">➔</span>
        <span className="px-2 py-0.5 rounded bg-emerald-950/70 border border-emerald-500/30 text-emerald-300">PYTHON</span>
      </div>

      {/* Main Glass Code Card */}
      <div className="relative rounded-2xl glass-panel border border-purple-500/30 p-3.5 sm:p-4 shadow-[0_0_35px_rgba(168,85,247,0.25)] overflow-hidden">
        
        {/* Card Header Bar */}
        <div className="flex items-center justify-between border-b border-white/10 pb-2 mb-3">
          <div className="flex items-center space-x-1.5">
            <div className="w-2.5 h-2.5 rounded-full bg-red-500/80" />
            <div className="w-2.5 h-2.5 rounded-full bg-yellow-500/80" />
            <div className="w-2.5 h-2.5 rounded-full bg-green-500/80" />
            <span className="text-[11px] font-mono text-gray-400 ml-1">solution.py</span>
          </div>

          <div className="flex items-center space-x-2">
            {/* AI Generated Badge */}
            <span className="px-2 py-0.5 rounded-full bg-emerald-950/80 border border-emerald-400/50 text-[9px] font-mono text-emerald-300 flex items-center gap-1">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
              AI GENERATED
            </span>

            {/* Copy Button */}
            <button
              onClick={handleCopy}
              className="text-gray-400 hover:text-white transition-colors text-[10px] font-mono"
            >
              {copied ? '✓ Copied' : 'Copy'}
            </button>
          </div>
        </div>

        {/* Syntax Highlighted Code Display */}
        <pre className="font-mono text-[11px] sm:text-xs text-gray-200 leading-normal overflow-x-auto space-y-0.5">
          <code>
            <div>
              <span className="text-purple-400 font-semibold">n</span>{' '}
              <span className="text-cyan-300">=</span>{' '}
              <span className="text-yellow-300">int</span>
              <span className="text-gray-400">(</span>
              <span className="text-yellow-300">input</span>
              <span className="text-gray-400">(</span>
              <span className="text-emerald-300">"Enter n: "</span>
              <span className="text-gray-400">))</span>
            </div>
            <div>
              <span className="text-purple-400 font-semibold">if</span>{' '}
              <span className="text-purple-400">n</span>{' '}
              <span className="text-cyan-300">&gt;</span>{' '}
              <span className="text-amber-300">0</span>
              <span className="text-cyan-300">:</span>
            </div>
            <div className="pl-3">
              <span className="text-yellow-300">print</span>
              <span className="text-gray-400">(</span>
              <span className="text-emerald-300">"Positive"</span>
              <span className="text-gray-400">)</span>
            </div>
            <div>
              <span className="text-purple-400 font-semibold">else</span>
              <span className="text-cyan-300">:</span>
            </div>
            <div className="pl-3">
              <span className="text-yellow-300">print</span>
              <span className="text-gray-400">(</span>
              <span className="text-emerald-300">"Negative"</span>
              <span className="text-gray-400">)</span>
            </div>
          </code>
        </pre>

        {/* Interactive Run Simulation Area */}
        <div className="mt-3 pt-2.5 border-t border-white/10 flex items-center justify-between">
          <button
            onClick={handleRun}
            disabled={isRunning}
            className="px-3 py-1.5 rounded-lg bg-gradient-to-r from-cyan-500 to-purple-600 hover:from-cyan-400 hover:to-purple-500 text-white font-heading text-[11px] font-bold transition-all shadow-[0_0_15px_rgba(6,182,212,0.4)] flex items-center gap-1.5"
          >
            {isRunning ? (
              <>
                <svg className="w-3 h-3 animate-spin text-white" viewBox="0 0 24 24" fill="none">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                </svg>
                Executing...
              </>
            ) : (
              <>
                <svg className="w-3 h-3 fill-current" viewBox="0 0 24 24">
                  <path d="M8 5v14l11-7z" />
                </svg>
                Run Code
              </>
            )}
          </button>

          <span className="text-[10px] font-mono text-gray-400">Python 3.10</span>
        </div>

        {/* Interactive Output Box */}
        {showOutput && (
          <div className="mt-2 p-2 rounded-lg bg-slate-950/90 border border-emerald-500/40 font-mono text-[10px] animate-fadeIn">
            <div className="text-emerald-300">Enter n: 5 ➔ <strong>Positive</strong></div>
            <div className="text-[9px] text-gray-500">✓ Executed in 0.04s</div>
          </div>
        )}
      </div>
    </div>
  );
};
