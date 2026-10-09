export const SYMBOLS = [
  { type: 'start_end', label: 'Start / End', defaultLabel: 'Start', preview: 'rounded-full bg-emerald-900/60 border-2 border-emerald-400' },
  { type: 'process', label: 'Process', defaultLabel: 'Process', preview: 'rounded-lg bg-blue-900/60 border-2 border-blue-400' },
  { type: 'input_output', label: 'Input / Output', defaultLabel: 'Input', preview: 'bg-purple-900/60 border-2 border-purple-400 skew-x-[-15deg]' },
  { type: 'decision', label: 'Decision', defaultLabel: 'condition?', preview: 'bg-yellow-900/60 border-2 border-yellow-400 rotate-45' },
  { type: 'document', label: 'Document', defaultLabel: 'Document', preview: 'rounded bg-cyan-900/60 border-2 border-cyan-400' },
  { type: 'predefined_process', label: 'Pre-defined Process', defaultLabel: 'Function', preview: 'bg-indigo-900/60 border-2 border-indigo-400' },
  { type: 'database', label: 'Database', defaultLabel: 'Database', preview: 'rounded bg-orange-900/60 border-2 border-orange-400' },
  { type: 'manual_input', label: 'Manual Input', defaultLabel: 'Enter value', preview: 'bg-rose-900/60 border-2 border-rose-400' },
  { type: 'connector', label: 'Connector', defaultLabel: 'A', preview: 'rounded-full bg-slate-800/60 border-2 border-slate-400' },
  { type: 'offpage', label: 'Off-page Connector', defaultLabel: 'A', preview: 'bg-teal-900/60 border-2 border-teal-400' },
  { type: 'delay', label: 'Delay', defaultLabel: 'Wait', preview: 'rounded-r-full bg-amber-900/60 border-2 border-amber-400' },
  { type: 'arrow', label: 'Arrow / Connector', defaultLabel: '→', preview: 'bg-slate-800/60 border-2 border-cyan-400' },
] as const;

export type SymbolType = (typeof SYMBOLS)[number]['type'];
