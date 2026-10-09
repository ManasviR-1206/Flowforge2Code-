import React from 'react';

export const FeaturesSection: React.FC = () => {
  const features = [
    {
      icon: (
        <svg className="w-6 h-6 text-cyan-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z" />
        </svg>
      ),
      title: "Interactive Canvas & Image Upload",
      description: "Draw flowcharts directly in your browser with smart shape tools, or upload high-res PNG/JPG images of your hand-drawn diagrams.",
    },
    {
      icon: (
        <svg className="w-6 h-6 text-purple-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
        </svg>
      ),
      title: "OpenCV Shape Perception",
      description: "Deterministic computer vision extracts decision diamonds, process blocks, input parallelograms, and directional connector vectors in milliseconds.",
    },
    {
      icon: (
        <svg className="w-6 h-6 text-emerald-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4" />
        </svg>
      ),
      title: "AI Code Generation Engine",
      description: "Converts reconstructed flowchart DAGs into synthetically clean, properly indented Python 3 code with automated variable typing.",
    },
    {
      icon: (
        <svg className="w-6 h-6 text-cyan-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" />
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
      ),
      title: "Instant In-Browser Sandbox",
      description: "Run generated Python with your own stdin in an isolated subprocess, with a timeout and restricted imports.",
    },
    {
      icon: (
        <svg className="w-6 h-6 text-purple-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
        </svg>
      ),
      title: "Interactive Verification Fallback",
      description: "Review and edit extracted OCR text or shape tags in a live data editor before generating code, ensuring 100% logic precision.",
    },
    {
      icon: (
        <svg className="w-6 h-6 text-emerald-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
        </svg>
      ),
      title: "Sub-20 Second Processing",
      description: "Parallelized OCR ROI extraction combined with lightweight LLM processing delivers end-to-end code generation under 8.5 seconds.",
    },
  ];

  return (
    <section id="features" className="relative py-24 px-4 sm:px-6 lg:px-8 max-w-7xl mx-auto z-10">
      
      <div className="text-center max-w-3xl mx-auto mb-16">
        <h2 className="font-heading text-3xl sm:text-5xl font-extrabold text-white tracking-tight">
          Engineered for <span className="text-gradient">Beginners &amp; Educators</span>
        </h2>
        <p className="mt-4 text-base sm:text-lg text-gray-300">
          Everything you need to turn visual logic diagrams into executable programming code seamlessly.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
        {features.map((f, i) => (
          <div
            key={i}
            className="glass-panel p-8 rounded-2xl border border-white/10 hover:border-cyan-500/40 transition-all duration-300 group hover:-translate-y-1 shadow-[0_0_30px_rgba(0,0,0,0.4)]"
          >
            <div className="w-12 h-12 rounded-xl bg-slate-900 border border-white/15 flex items-center justify-center mb-6 group-hover:scale-110 group-hover:border-cyan-400/60 transition-transform">
              {f.icon}
            </div>
            <h3 className="font-heading text-xl font-bold text-white mb-3 group-hover:text-cyan-300 transition-colors">
              {f.title}
            </h3>
            <p className="text-sm text-gray-400 leading-relaxed">
              {f.description}
            </p>
          </div>
        ))}
      </div>

    </section>
  );
};
