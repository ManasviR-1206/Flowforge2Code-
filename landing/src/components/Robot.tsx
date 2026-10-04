import React, { useRef } from 'react';
import { RobotEyes } from './RobotEyes';
import { useRobotEyeTracking } from '../hooks/useRobotEyeTracking';

interface RobotProps {
  parallaxX?: number;
  parallaxY?: number;
}

export const Robot: React.FC<RobotProps> = ({ parallaxX = 0, parallaxY = 0 }) => {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const { pupilPos, isBlinking, isMobile } = useRobotEyeTracking(containerRef);

  return (
    <div
      ref={containerRef}
      className="relative z-10 flex flex-col items-center justify-center transition-transform duration-200 ease-out"
      style={{
        transform: `translate3d(${parallaxX}px, ${parallaxY}px, 0px)`,
      }}
    >
      {/* Background Soft Blue/Cyan Radial Aura Glow */}
      <div className="absolute w-72 sm:w-96 h-72 sm:h-96 bg-cyan-500/20 rounded-full blur-[90px] -z-10 animate-pulse-glow" />
      <div className="absolute w-60 sm:w-80 h-60 sm:h-80 bg-purple-600/15 rounded-full blur-[80px] -z-10" />

      {/* Main Floating Robot Container */}
      <div className="relative animate-float-slow flex flex-col items-center">
        
        {/* Antenna Top Pulsing Sphere */}
        <div className="relative flex flex-col items-center mb-1">
          <div className="w-3.5 h-3.5 rounded-full bg-cyan-400 shadow-[0_0_15px_#00f0ff] animate-ping opacity-75" />
          <div className="w-3 h-3 rounded-full bg-cyan-300 shadow-[0_0_12px_#00f0ff] -mt-3" />
          <div className="w-1 h-4 bg-gradient-to-b from-cyan-400 to-slate-400 rounded-full" />
        </div>

        {/* Head Shell */}
        <div className="relative w-60 sm:w-72 h-40 sm:h-48 bg-gradient-to-b from-slate-100 via-slate-200 to-slate-300 rounded-[48px] p-2.5 shadow-[0_15px_40px_rgba(0,0,0,0.6),0_0_30px_rgba(6,182,212,0.3)] border border-white/60 flex items-center justify-center">
          
          {/* Head Ear Lighting Accents */}
          <div className="absolute -left-3 top-1/2 -translate-y-1/2 w-4 h-10 bg-gradient-to-b from-cyan-400 to-purple-600 rounded-l-full shadow-[0_0_12px_#00f0ff]" />
          <div className="absolute -right-3 top-1/2 -translate-y-1/2 w-4 h-10 bg-gradient-to-b from-cyan-400 to-purple-600 rounded-r-full shadow-[0_0_12px_#00f0ff]" />

          {/* Interactive Screen & Eyes */}
          <RobotEyes pupilPos={pupilPos} isBlinking={isBlinking} isMobile={isMobile} />
        </div>

        {/* Neck Collar Node */}
        <div className="w-24 sm:w-28 h-3 bg-gradient-to-r from-slate-800 via-cyan-400 to-slate-800 rounded-full border border-cyan-300/40 shadow-[0_0_10px_#00f0ff] my-1 z-20" />

        {/* Robot Torso / Body */}
        <div className="relative w-52 sm:w-64 h-36 sm:h-44 bg-gradient-to-b from-slate-100 via-slate-200 to-slate-300 rounded-t-[40px] rounded-b-[24px] border border-white/60 p-4 shadow-[0_20px_50px_rgba(0,0,0,0.7),0_0_35px_rgba(6,182,212,0.25)] flex flex-col items-center justify-between">
          
          {/* Shoulder Joints */}
          <div className="absolute -left-4 top-2 w-7 h-14 bg-gradient-to-b from-slate-300 to-slate-400 rounded-l-2xl border border-white/40 shadow-md" />
          <div className="absolute -right-4 top-2 w-7 h-14 bg-gradient-to-b from-slate-300 to-slate-400 rounded-r-2xl border border-white/40 shadow-md" />

          {/* Chest Lightning Emblem */}
          <div className="w-12 h-12 rounded-full bg-slate-950 border border-cyan-400/50 flex items-center justify-center shadow-[0_0_20px_rgba(6,182,212,0.6)] mt-1">
            <svg className="w-6 h-6 text-cyan-300 drop-shadow-[0_0_8px_#00f0ff] animate-pulse" viewBox="0 0 24 24" fill="currentColor">
              <path d="M13 2L3 14h9l-1 8 10-12h-9l1-8z" />
            </svg>
          </div>

          {/* Core Status Bar */}
          <div className="w-32 h-2.5 rounded-full bg-slate-900 overflow-hidden border border-cyan-500/30 p-0.5 mb-2">
            <div className="w-full h-full bg-gradient-to-r from-cyan-400 via-sky-300 to-purple-500 rounded-full animate-pulse" />
          </div>
        </div>

        {/* Lower Magnetic Hover Base Glow */}
        <div className="w-40 sm:w-48 h-3 bg-gradient-to-r from-transparent via-cyan-400 to-transparent blur-[3px] shadow-[0_0_20px_#00f0ff] mt-2" />
      </div>
    </div>
  );
};
