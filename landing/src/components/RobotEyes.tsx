import React from 'react';

interface RobotEyesProps {
  pupilPos: { x: number; y: number };
  isBlinking: boolean;
  isMobile: boolean;
}

export const RobotEyes: React.FC<RobotEyesProps> = ({ pupilPos, isBlinking, isMobile }) => {
  return (
    <div className="relative w-full h-full flex items-center justify-center">
      {/* Face Screen Container */}
      <div className="relative w-44 sm:w-52 h-24 sm:h-28 bg-gradient-to-b from-slate-950 via-slate-900 to-black rounded-3xl border border-cyan-500/40 p-3 shadow-[inset_0_0_25px_rgba(6,182,212,0.4)] flex items-center justify-between px-6 sm:px-8 overflow-hidden">
        
        {/* Glass Reflection Highlight */}
        <div className="absolute -top-12 left-0 right-0 h-20 bg-gradient-to-b from-white/20 to-transparent rounded-full transform -rotate-6 pointer-events-none" />

        {/* Left Eye Socket */}
        <div
          className={`relative w-12 sm:w-14 h-12 sm:h-14 rounded-full bg-slate-950 border-2 border-cyan-400/80 flex items-center justify-center shadow-[0_0_15px_rgba(6,182,212,0.6)] transition-transform duration-150 ${
            isBlinking ? 'scale-y-[0.08]' : 'scale-y-100'
          }`}
        >
          {/* Outer Cyan Ring */}
          <div className="absolute inset-0.5 rounded-full border border-cyan-300/40 animate-pulse" />
          
          {/* Left Eye Pupil */}
          <div
            className="w-7 sm:w-8 h-7 sm:h-8 rounded-full bg-gradient-to-tr from-cyan-500 via-sky-300 to-white flex items-center justify-center shadow-[0_0_20px_rgba(0,240,255,0.9)] transition-transform ease-out duration-75"
            style={{
              transform: isMobile
                ? 'translate3d(0px, 0px, 0px)'
                : `translate3d(${pupilPos.x}px, ${pupilPos.y}px, 0px)`,
            }}
          >
            {/* White Catchlight Specular Dot */}
            <div className="w-2.5 h-2.5 bg-white rounded-full translate-x-1 -translate-y-1 shadow-[0_0_8px_#ffffff]" />
          </div>
        </div>

        {/* Cute Blush Accent (Left) */}
        <div className="absolute left-3 bottom-2 w-4 h-1.5 rounded-full bg-cyan-400/30 blur-[2px]" />

        {/* Right Eye Socket */}
        <div
          className={`relative w-12 sm:w-14 h-12 sm:h-14 rounded-full bg-slate-950 border-2 border-cyan-400/80 flex items-center justify-center shadow-[0_0_15px_rgba(6,182,212,0.6)] transition-transform duration-150 ${
            isBlinking ? 'scale-y-[0.08]' : 'scale-y-100'
          }`}
        >
          {/* Outer Cyan Ring */}
          <div className="absolute inset-0.5 rounded-full border border-cyan-300/40 animate-pulse" />
          
          {/* Right Eye Pupil */}
          <div
            className="w-7 sm:w-8 h-7 sm:h-8 rounded-full bg-gradient-to-tr from-cyan-500 via-sky-300 to-white flex items-center justify-center shadow-[0_0_20px_rgba(0,240,255,0.9)] transition-transform ease-out duration-75"
            style={{
              transform: isMobile
                ? 'translate3d(0px, 0px, 0px)'
                : `translate3d(${pupilPos.x}px, ${pupilPos.y}px, 0px)`,
            }}
          >
            {/* White Catchlight Specular Dot */}
            <div className="w-2.5 h-2.5 bg-white rounded-full translate-x-1 -translate-y-1 shadow-[0_0_8px_#ffffff]" />
          </div>
        </div>

        {/* Cute Blush Accent (Right) */}
        <div className="absolute right-3 bottom-2 w-4 h-1.5 rounded-full bg-cyan-400/30 blur-[2px]" />

        {/* Screen Bottom LED Glow Strip */}
        <div className="absolute bottom-0 inset-x-8 h-[2px] bg-gradient-to-r from-cyan-500 via-purple-500 to-cyan-500 shadow-[0_0_10px_#00f0ff]" />
      </div>
    </div>
  );
};
