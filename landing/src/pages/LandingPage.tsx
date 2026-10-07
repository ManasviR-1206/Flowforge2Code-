import React from 'react';
import { Navbar } from '../components/Navbar';
import { Hero } from '../components/Hero';
import { FeaturesSection } from '../components/FeaturesSection';
import { HowItWorksSection } from '../components/HowItWorksSection';
import { Footer } from '../components/Footer';
import { ParticleBackground } from '../components/ParticleBackground';

export const LandingPage: React.FC = () => {
  return (
    <div className="relative min-h-screen bg-space-950 text-white font-body selection:bg-cyan-500 selection:text-black overflow-x-hidden">
      
      {/* Deep Space Glowing Ambient Spotlight Gradients */}
      <div className="fixed top-0 left-1/2 -translate-x-1/2 w-[1000px] h-[600px] bg-gradient-to-b from-cyan-500/15 via-purple-600/10 to-transparent rounded-full blur-[160px] pointer-events-none z-0" />
      <div className="fixed top-1/3 left-1/4 w-[500px] h-[500px] bg-cyan-600/10 rounded-full blur-[140px] pointer-events-none z-0" />
      <div className="fixed top-1/2 right-1/4 w-[600px] h-[600px] bg-purple-600/10 rounded-full blur-[160px] pointer-events-none z-0" />

      {/* Cybernetic Grid Overlay */}
      <div 
        className="fixed inset-0 z-0 pointer-events-none opacity-15"
        style={{
          backgroundImage: `
            linear-gradient(to right, rgba(6, 182, 212, 0.15) 1px, transparent 1px),
            linear-gradient(to bottom, rgba(6, 182, 212, 0.15) 1px, transparent 1px)
          `,
          backgroundSize: '80px 80px',
        }}
      />

      {/* Starry Particle Layer */}
      <ParticleBackground />

      {/* Foreground Content */}
      <div className="relative z-10">
        <Navbar />
        <main>
          <Hero />
          <FeaturesSection />
          <HowItWorksSection />
        </main>
        <Footer />
      </div>
    </div>
  );
};
