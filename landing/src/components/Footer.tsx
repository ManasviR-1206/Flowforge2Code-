import React from 'react';
import { useNavigate } from 'react-router-dom';

export const Footer: React.FC = () => {
  const navigate = useNavigate();
  return (
    <footer id="about" className="relative border-t border-white/10 py-12 px-4 sm:px-6 lg:px-8 bg-slate-950/80 backdrop-blur-md z-10">
      <div className="max-w-7xl mx-auto flex flex-col md:flex-row justify-between items-center space-y-6 md:space-y-0">
        
        {/* Logo & Tagline */}
        <div className="flex flex-col items-center md:items-start space-y-2">
          <div className="flex items-center space-x-3">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-cyan-500 to-purple-600 p-[1px]">
              <div className="w-full h-full bg-slate-950 rounded-[7px] flex items-center justify-center">
                <svg className="w-4 h-4 text-cyan-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <ellipse cx="12" cy="5" rx="5" ry="3" />
                  <rect x="7" y="11" width="10" height="4" rx="1" />
                </svg>
              </div>
            </div>
            <span className="font-heading text-lg font-bold text-white">
              FlowForge <span className="text-cyan-400">AI</span>
            </span>
          </div>
          <p className="text-xs text-gray-400">
            Team 5 | Flowchart to Executable Code Engine
          </p>
        </div>

        {/* Links */}
        <div className="flex space-x-6 text-xs text-gray-400 font-mono">
          <a href="#hero" className="hover:text-cyan-400 transition-colors">Home</a>
          <a href="#features" className="hover:text-cyan-400 transition-colors">Features</a>
          <a href="#how-it-works" className="hover:text-cyan-400 transition-colors">How It Works</a>
          <button onClick={() => navigate('/workspace')} className="hover:text-cyan-400 transition-colors">Workspace</button>
        </div>

        {/* Copyright */}
        <div className="text-xs text-gray-400">
          © {new Date().getFullYear()} FlowForge AI. All rights reserved.
        </div>
      </div>
    </footer>
  );
};
