import React from 'react';
import { HelpCircle, BookOpen, Code2 } from 'lucide-react';

export const DocsView: React.FC = () => {
  return (
    <div className="max-w-4xl mx-auto p-6 space-y-8">
      <div>
        <h2 className="text-2xl font-bold text-gray-900 flex items-center gap-2.5">
          <HelpCircle className="w-6 h-6 text-indigo-600" />
          Help & Documentation
        </h2>
        <p className="text-sm text-gray-500 mt-1">
          Learn how to draw flowcharts, configure nodes, generate Python code, and execute programs.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="bg-white rounded-2xl border border-gray-200 p-6 space-y-4 shadow-xs">
          <h3 className="font-bold text-gray-800 text-base flex items-center gap-2">
            <BookOpen className="w-5 h-5 text-indigo-500" />
            Flowchart Shape Standard
          </h3>
          <ul className="space-y-3 text-xs text-gray-600">
            <li className="flex items-start gap-3">
              <span className="w-4 h-4 rounded-full bg-pink-400 mt-0.5 shrink-0" />
              <div>
                <strong className="text-gray-800">Start / End (Pink Oval):</strong> Represents the entry and exit points of the execution logic.
              </div>
            </li>
            <li className="flex items-start gap-3">
              <span className="w-4 h-4 rounded-md bg-blue-400 mt-0.5 shrink-0" />
              <div>
                <strong className="text-gray-800">Process (Blue Rectangle):</strong> Execution steps such as variable assignments (`count = 0`).
              </div>
            </li>
            <li className="flex items-start gap-3">
              <span className="w-4 h-4 rounded-sm bg-green-400 skew-x-[-15deg] mt-0.5 shrink-0" />
              <div>
                <strong className="text-gray-800">Input / Output (Green Parallelogram):</strong> Reading input (`Input n`) or printing results (`Print "Positive"`).
              </div>
            </li>
            <li className="flex items-start gap-3">
              <span className="w-4 h-4 rotate-45 bg-yellow-400 mt-0.5 shrink-0" />
              <div>
                <strong className="text-gray-800">Decision (Yellow Diamond):</strong> Conditionals with Yes/No branches (n &gt; 0?).
              </div>
            </li>
          </ul>
        </div>

        <div className="bg-white rounded-2xl border border-gray-200 p-6 space-y-4 shadow-xs">
          <h3 className="font-bold text-gray-800 text-base flex items-center gap-2">
            <Code2 className="w-5 h-5 text-indigo-500" />
            Python Code Generation Rules
          </h3>
          <div className="text-xs text-gray-600 space-y-2">
            <p>
              FlowForge AI converts connected nodes into an Abstract Syntax Tree (AST), which is compiled into standard Python 3.
            </p>
            <div className="bg-gray-900 text-gray-100 p-3 rounded-xl font-mono text-[11px] space-y-1">
              <div className="text-green-400"># Example Generated Code</div>
              <div>n = int(input("Enter n: "))</div>
              <div className="text-pink-400">if n &gt; 0:</div>
              <div className="pl-4 text-blue-300">print("Positive")</div>
              <div className="text-pink-400">else:</div>
              <div className="pl-4 text-blue-300">print("Negative")</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
