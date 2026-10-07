import React from 'react';
import { useNavigate } from 'react-router-dom';

interface MobileMenuProps {
  isOpen: boolean;
  onClose: () => void;
}

export const MobileMenu: React.FC<MobileMenuProps> = ({ isOpen, onClose }) => {
  const navigate = useNavigate();
  if (!isOpen) return null;

  const goToWorkspace = () => {
    onClose();
    navigate('/workspace');
  };

  return (
    <div className="fixed inset-0 z-40 bg-slate-950/95 backdrop-blur-xl flex flex-col justify-center items-center px-6 pt-20 pb-10 transition-all duration-300 md:hidden">
      <nav className="flex flex-col items-center space-y-8 text-center text-lg font-heading">
        <a href="#hero" onClick={onClose} className="text-white hover:text-cyan-400 transition-colors">Home</a>
        <a href="#features" onClick={onClose} className="text-gray-300 hover:text-cyan-400 transition-colors">Features</a>
        <a href="#how-it-works" onClick={onClose} className="text-gray-300 hover:text-cyan-400 transition-colors">How It Works</a>
        <a href="#about" onClick={onClose} className="text-gray-300 hover:text-cyan-400 transition-colors">About</a>

        <div className="pt-6 w-full max-w-xs">
          <button
            onClick={goToWorkspace}
            className="block w-full py-3 px-6 rounded-full bg-white text-black font-semibold text-center hover:bg-cyan-400 transition-all shadow-[0_0_25px_rgba(0,240,255,0.4)]"
          >
            Try FlowForge AI →
          </button>
        </div>
      </nav>
    </div>
  );
};
