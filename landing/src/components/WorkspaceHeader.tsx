import React, { useState } from 'react';

interface HeaderProps {
  onNavigateHome?: () => void;
  activeTab?: string;
  setActiveTab?: (tab: string) => void;
}

export const WorkspaceHeader: React.FC<HeaderProps> = ({ onNavigateHome, setActiveTab }) => {
  const [profileOpen, setProfileOpen] = useState(false);

  return (
    <header className="h-16 bg-white border-b border-gray-100 flex items-center justify-between px-6 sticky top-0 z-30 w-full shadow-xs">
      {/* Brand & Tagline */}
      <div className="flex items-center gap-3">
        <a 
          href="/" 
          onClick={(e) => {
            if (onNavigateHome) {
              e.preventDefault();
              onNavigateHome();
            }
          }}
          className="flex items-center gap-3 group cursor-pointer"
        >
          <div className="w-10 h-10 bg-indigo-600 rounded-xl flex items-center justify-center shadow-md shadow-indigo-500/20 group-hover:bg-indigo-700 transition-colors">
            <svg className="w-5 h-5 text-white" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
              <path d="M7 11V7a5 5 0 0 1 10 0v4" />
              <rect x="3" y="11" width="18" height="10" rx="2" ry="2" />
              <path d="M12 15v2" />
            </svg>
          </div>
          <div>
            <h1 className="font-sans text-lg font-bold text-gray-900 leading-tight group-hover:text-indigo-600 transition-colors">
              FlowForge AI
            </h1>
            <p className="text-[11px] text-gray-500 font-medium">From Flowcharts to Functional Code</p>
          </div>
        </a>
      </div>

      {/* Top Center Nav Links matching screenshot */}
      <nav className="hidden md:flex items-center gap-8">
        <a href="/" className="text-sm font-semibold text-gray-600 hover:text-indigo-600 transition-colors">Home</a>
        <a href="/#features" className="text-sm font-semibold text-gray-600 hover:text-indigo-600 transition-colors">Features</a>
        <a href="/#how-it-works" className="text-sm font-semibold text-gray-600 hover:text-indigo-600 transition-colors">How It Works</a>
        <a href="/#about" className="text-sm font-semibold text-gray-600 hover:text-indigo-600 transition-colors">About</a>
      </nav>

      {/* Right User Profile Dropdown */}
      <div className="relative">
        <button 
          onClick={() => setProfileOpen(!profileOpen)}
          className="flex items-center gap-2.5 hover:bg-gray-50 p-1.5 px-2.5 rounded-xl transition-colors border border-transparent hover:border-gray-200"
        >
          <div className="w-8 h-8 rounded-full bg-indigo-600 text-white font-bold text-sm flex items-center justify-center shadow-sm">
            M
          </div>
          <span className="text-sm font-bold text-gray-700">Manasvi R</span>
          <svg className={`w-4 h-4 text-gray-500 transition-transform ${profileOpen ? 'rotate-180' : ''}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 9l-7 7-7-7" />
          </svg>
        </button>

        {profileOpen && (
          <div className="absolute right-0 mt-2 w-48 bg-white border border-gray-100 rounded-2xl shadow-xl py-2 z-50 text-sm">
            <div className="px-4 py-2 border-b border-gray-100">
              <p className="font-bold text-gray-800">Manasvi R</p>
              <p className="text-xs text-gray-500">test@flowforge.ai</p>
            </div>
            <button 
              onClick={() => { setActiveTab && setActiveTab('settings'); setProfileOpen(false); }}
              className="w-full text-left px-4 py-2 hover:bg-gray-50 text-gray-700 font-medium"
            >
              API Keys & Settings
            </button>
            <button 
              onClick={() => { setActiveTab && setActiveTab('projects'); setProfileOpen(false); }}
              className="w-full text-left px-4 py-2 hover:bg-gray-50 text-gray-700 font-medium"
            >
              Saved Projects
            </button>
            <div className="border-t border-gray-100 my-1" />
            <a href="/" className="block px-4 py-2 hover:bg-gray-50 text-red-600 font-medium">
              Back to Home
            </a>
          </div>
        )}
      </div>
    </header>
  );
};
