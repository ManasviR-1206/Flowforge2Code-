import React from 'react';

interface FlowchartVisualProps {
  parallaxX?: number;
  parallaxY?: number;
}

export const FlowchartVisual: React.FC<FlowchartVisualProps> = ({ parallaxX = 0, parallaxY = 0 }) => {
  return (
    <div
      className="relative z-10 w-full max-w-xs sm:max-w-sm transition-transform duration-200 ease-out"
      style={{
        transform: `translate3d(${parallaxX}px, ${parallaxY}px, 0px)`,
      }}
    >
      {/* Hologram Floating Container */}
      <div className="relative p-3.5 sm:p-4 rounded-2xl glass-panel border border-cyan-500/30 shadow-[0_0_35px_rgba(6,182,212,0.2)] flex flex-col items-center space-y-2 font-mono text-xs">
        
        {/* Hologram Header Badge */}
        <div className="absolute -top-3 left-4 px-2.5 py-0.5 rounded-full bg-cyan-950/90 border border-cyan-400/50 text-[9px] uppercase tracking-wider text-cyan-300 font-sans flex items-center gap-1 shadow-[0_0_10px_rgba(6,182,212,0.4)]">
          <span className="w-1.5 h-1.5 rounded-full bg-cyan-400 animate-ping" />
          Flowchart Logic Hologram
        </div>

        {/* 1. START Node (Rounded Pill) */}
        <div className="w-28 py-1 rounded-full bg-cyan-950/60 border border-cyan-400/80 text-cyan-300 text-center font-semibold text-[11px] shadow-[0_0_10px_rgba(6,182,212,0.3)] animate-pulse">
          START
        </div>

        {/* Arrow 1 */}
        <div className="flex flex-col items-center text-cyan-400">
          <div className="w-0.5 h-3 bg-gradient-to-b from-cyan-400 to-sky-300" />
          <svg className="w-2.5 h-2.5 -mt-1 text-cyan-400 fill-current" viewBox="0 0 24 24">
            <path d="M12 21l-12-18h24z" />
          </svg>
        </div>

        {/* 2. INPUT Node (Parallelogram) */}
        <div className="w-36 py-1 px-3 bg-sky-950/50 border border-sky-400/70 text-sky-200 text-center font-mono transform -skew-x-12 text-[11px]">
          <span className="inline-block transform skew-x-12">INPUT n</span>
        </div>

        {/* Arrow 2 */}
        <div className="flex flex-col items-center text-sky-400">
          <div className="w-0.5 h-3 bg-gradient-to-b from-sky-400 to-purple-400" />
          <svg className="w-2.5 h-2.5 -mt-1 text-sky-400 fill-current" viewBox="0 0 24 24">
            <path d="M12 21l-12-18h24z" />
          </svg>
        </div>

        {/* 3. PROCESS Node (Rectangle) */}
        <div className="w-40 py-1.5 px-3 rounded-md bg-purple-950/50 border border-purple-400/70 text-purple-200 text-center text-[11px]">
          PROCESS: Check Sign
        </div>

        {/* Arrow 3 */}
        <div className="flex flex-col items-center text-purple-400">
          <div className="w-0.5 h-3 bg-gradient-to-b from-purple-400 to-fuchsia-400" />
          <svg className="w-2.5 h-2.5 -mt-1 text-purple-400 fill-current" viewBox="0 0 24 24">
            <path d="M12 21l-12-18h24z" />
          </svg>
        </div>

        {/* 4. DECISION Node (Diamond) */}
        <div className="relative w-16 h-16 flex items-center justify-center my-1">
          <div className="absolute inset-0 bg-fuchsia-950/60 border border-fuchsia-400/80 transform rotate-45 rounded-md shadow-[0_0_15px_rgba(232,121,249,0.4)]" />
          <span className="relative z-10 text-fuchsia-200 font-bold text-center text-[10px]">n &gt; 0?</span>
        </div>

        {/* Decision Branching Lines */}
        <div className="w-full flex justify-between px-2 pt-0.5 text-[10px]">
          <div className="flex flex-col items-center text-cyan-400">
            <span className="text-cyan-300 font-sans font-semibold mb-0.5">YES</span>
            <div className="w-0.5 h-3 bg-cyan-400" />
            <div className="mt-0.5 w-24 py-1 px-1 bg-cyan-950/70 border border-cyan-400/80 text-cyan-200 text-center transform -skew-x-6 text-[9px]">
              <span className="inline-block transform skew-x-6">Print "Positive"</span>
            </div>
          </div>

          <div className="flex flex-col items-center text-purple-400">
            <span className="text-purple-300 font-sans font-semibold mb-0.5">NO</span>
            <div className="w-0.5 h-3 bg-purple-400" />
            <div className="mt-0.5 w-24 py-1 px-1 bg-purple-950/70 border border-purple-400/80 text-purple-200 text-center transform -skew-x-6 text-[9px]">
              <span className="inline-block transform skew-x-6">Print "Negative"</span>
            </div>
          </div>
        </div>

        {/* Arrow Converge */}
        <div className="w-0.5 h-3 bg-gradient-to-b from-purple-400 via-cyan-400 to-emerald-400" />

        {/* 5. END Node (Rounded Pill) */}
        <div className="w-28 py-1 rounded-full bg-emerald-950/60 border border-emerald-400/80 text-emerald-300 text-center font-semibold text-[11px] shadow-[0_0_10px_rgba(52,211,153,0.3)]">
          END
        </div>
      </div>
    </div>
  );
};
