import React from 'react';
import { Robot } from './Robot';
import { FlowchartVisual } from './FlowchartVisual';
import { CodePreview } from './CodePreview';
import { useTypewriter } from '../hooks/useTypewriter';
import { useMouseParallax } from '../hooks/useMouseParallax';

export const Hero: React.FC = () => {
  const { displayedText } = useTypewriter("Draw it. Understand it. Generate it. Run it.", 38, 600);
  const parallax = useMouseParallax();

  return (
    <section id="hero" className="relative min-h-[calc(100vh-80px)] pt-20 pb-6 px-4 sm:px-6 lg:px-8 flex flex-col justify-start items-center overflow-hidden">
      
      {/* Background Radial Glow Spotlight */}
      <div className="absolute top-1/4 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[500px] h-[500px] bg-cyan-500/10 rounded-full blur-[120px] pointer-events-none z-0" />
      <div className="absolute top-1/3 left-1/2 -translate-x-1/2 w-[700px] h-[350px] bg-purple-600/10 rounded-full blur-[140px] pointer-events-none z-0" />

      {/* Main Hero Header Content (Compact Above-The-Fold Layout) */}
      <div className="relative z-10 max-w-4xl mx-auto text-center flex flex-col items-center">
        
        {/* Top Eyebrow Label */}
        <div className="inline-flex items-center space-x-2 px-2.5 py-0.5 rounded-full bg-cyan-950/60 border border-cyan-400/40 backdrop-blur-md shadow-[0_0_15px_rgba(6,182,212,0.3)] mb-2">
          <span className="w-1.5 h-1.5 rounded-full bg-cyan-400 animate-ping" />
          <span className="text-[10px] font-sans font-semibold tracking-wider text-cyan-300 uppercase">
            MEET YOUR AI FLOWCHART ENGINE
          </span>
        </div>

        {/* Centered Heading */}
        <h1 className="font-heading text-2xl sm:text-4xl lg:text-5xl font-extrabold text-white tracking-tight leading-tight max-w-3xl">
          Turn <span className="bg-gradient-to-r from-cyan-400 via-sky-300 to-purple-400 bg-clip-text text-transparent">Flowcharts</span> into <span className="bg-gradient-to-r from-purple-400 via-pink-400 to-cyan-400 bg-clip-text text-transparent">Working Code</span>
        </h1>

        {/* Typewriter Subheading */}
        <div className="mt-1 h-5 flex items-center justify-center font-mono text-xs sm:text-sm text-cyan-300">
          <span>{displayedText}</span>
          <span className="inline-block w-[2px] h-[1.1em] bg-white ml-1 animate-cursor-blink" />
        </div>

        {/* Highly Prominent CTA Button */}
        <div className="mt-4 flex items-center justify-center w-full">
          <a
            href="http://localhost:8501"
            target="_blank"
            rel="noopener noreferrer"
            className="px-8 py-3 rounded-full bg-white text-black font-heading font-extrabold text-sm sm:text-base hover:bg-cyan-300 hover:text-black transition-all duration-300 transform hover:scale-105 shadow-[0_0_30px_rgba(0,240,255,0.7),0_0_50px_rgba(168,85,247,0.4)] text-center tracking-wide flex items-center gap-2 group"
          >
            <span>Create Flowchart</span>
            <span className="group-hover:translate-x-1 transition-transform">→</span>
          </a>
        </div>
      </div>

      {/* Visual Composition: Robot Hero Centered with Orbiting Flowchart & Code Cards */}
      <div className="relative z-10 max-w-6xl mx-auto w-full mt-3 grid grid-cols-1 lg:grid-cols-3 gap-3 lg:gap-4 items-center justify-items-center">
        
        {/* Left: Flowchart Hologram */}
        <div className="w-full flex justify-center lg:justify-end order-2 lg:order-1">
          <FlowchartVisual parallaxX={parallax.flowchartX} parallaxY={parallax.flowchartY} />
        </div>

        {/* Center: The Robot Hero */}
        <div className="w-full flex justify-center order-1 lg:order-2">
          <Robot parallaxX={parallax.robotX} parallaxY={parallax.robotY} />
        </div>

        {/* Right: Code Preview Card */}
        <div className="w-full flex justify-center lg:justify-start order-3">
          <CodePreview parallaxX={parallax.codeX} parallaxY={parallax.codeY} />
        </div>

      </div>

    </section>
  );
};
