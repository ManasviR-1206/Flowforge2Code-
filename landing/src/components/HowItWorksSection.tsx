import React from 'react';

export const HowItWorksSection: React.FC = () => {
  const steps = [
    {
      num: "01",
      title: "Draw or Upload",
      description: "Upload your flowchart image or draw custom shapes directly on our interactive sketch canvas.",
    },
    {
      num: "02",
      title: "AI & Computer Vision Parsing",
      description: "OpenCV isolates block contours while Tesseract OCR extracts decision conditions and instructions.",
    },
    {
      num: "03",
      title: "Logic Graph Reconstruction",
      description: "The engine constructs a structured AST graph defining execution sequence, branches, and loop cycles.",
    },
    {
      num: "04",
      title: "Code Generation & Execution",
      description: "Generates clean Python 3 code instantaneously with an interactive test runner to verify output.",
    },
  ];

  return (
    <section id="how-it-works" className="relative py-24 px-4 sm:px-6 lg:px-8 max-w-7xl mx-auto z-10">
      
      <div className="text-center max-w-3xl mx-auto mb-16">
        <div className="inline-flex items-center space-x-2 px-3 py-1 rounded-full bg-purple-950/60 border border-purple-400/40 mb-4">
          <span className="text-xs font-mono text-purple-300">SIMPLE 4-STEP PIPELINE</span>
        </div>
        <h2 className="font-heading text-3xl sm:text-5xl font-extrabold text-white tracking-tight">
          How <span className="text-gradient">FlowForge AI</span> Works
        </h2>
        <p className="mt-4 text-base sm:text-lg text-gray-300">
          Transforming visual diagrams to working software in under 10 seconds.
        </p>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-8">
        {steps.map((step, index) => (
          <div key={index} className="relative glass-panel p-6 rounded-2xl border border-white/10 flex flex-col justify-between">
            <div>
              <span className="font-mono text-4xl font-extrabold text-cyan-400/40 block mb-4">
                {step.num}
              </span>
              <h3 className="font-heading text-lg font-bold text-white mb-2">
                {step.title}
              </h3>
              <p className="text-xs text-gray-400 leading-relaxed">
                {step.description}
              </p>
            </div>

            {index < steps.length - 1 && (
              <div className="hidden lg:block absolute -right-4 top-1/2 -translate-y-1/2 z-20 text-cyan-400 font-bold text-xl">
                ➔
              </div>
            )}
          </div>
        ))}
      </div>

      {/* CTA Box */}
      <div className="mt-16 text-center">
        <div className="inline-block p-[1px] rounded-full bg-gradient-to-r from-cyan-500 via-purple-500 to-cyan-500 shadow-[0_0_40px_rgba(6,182,212,0.4)]">
          <a
            href="http://localhost:8501"
            target="_blank"
            rel="noopener noreferrer"
            className="block px-10 py-4 rounded-full bg-slate-950 text-white font-heading font-bold text-base hover:bg-cyan-400 hover:text-black transition-all"
          >
            Launch FlowForge AI Application →
          </a>
        </div>
      </div>

    </section>
  );
};
