import { useEffect, useState } from 'react';
import { Handle, Position, NodeResizer } from 'reactflow';

const nodeStyle = {
  base: 'relative flex items-center justify-center text-center font-bold text-xs transition-all cursor-default',
  selected: 'ring-2 ring-cyan-400 ring-offset-1',
  error: 'ring-2 ring-red-500 ring-offset-1',
};

export const EditableLabel = ({ value, onChange }: { value: string; onChange: (v: string) => void }) => {
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(value);
  useEffect(() => { setDraft(value); }, [value]);
  const commit = () => {
    setEditing(false);
    if (draft !== value) onChange(draft);
  };
  return editing ? (
    <input
      autoFocus
      className="bg-transparent border-b border-cyan-400 text-center outline-none text-xs font-bold w-full min-w-[4rem]"
      value={draft}
      onChange={e => setDraft(e.target.value)}
      onBlur={commit}
      onKeyDown={e => { if (e.key === 'Enter') commit(); if (e.key === 'Escape') setEditing(false); }}
      onClick={e => e.stopPropagation()}
    />
  ) : (
    <span onDoubleClick={() => setEditing(true)} className="cursor-text select-none px-1 leading-tight">{value}</span>
  );
};

const handleStyle = (color: string, border: string) => ({ background: color, border: `2px solid ${border}`, width: 10, height: 10 });

export const StartEndNode = ({ id, data, selected }: any) => (
  <div className={`${nodeStyle.base} ${selected ? nodeStyle.selected : ''} ${data?.hasError ? nodeStyle.error : ''} bg-gradient-to-br from-emerald-900/80 to-teal-900/80 border-2 border-emerald-400 text-emerald-300 rounded-full px-5 py-2.5 min-w-[110px] shadow-[0_0_12px_rgba(52,211,153,0.3)]`}>
    <Handle type="target" position={Position.Top} style={handleStyle('#34d399', '#064e3b')} />
    <EditableLabel value={data?.label || 'Start'} onChange={v => data?.onLabelChange?.(id, v)} />
    <Handle type="source" position={Position.Bottom} style={handleStyle('#34d399', '#064e3b')} />
  </div>
);

export const ProcessNode = ({ id, data, selected }: any) => (
  <div className={`${nodeStyle.base} ${selected ? nodeStyle.selected : ''} ${data?.hasError ? nodeStyle.error : ''} bg-gradient-to-br from-blue-900/80 to-indigo-900/80 border-2 border-blue-400 text-blue-200 rounded-lg px-5 py-3 min-w-[130px] shadow-[0_0_12px_rgba(59,130,246,0.25)]`}>
    <NodeResizer isVisible={selected} minWidth={110} minHeight={40} color="#22d3ee" />
    <Handle type="target" position={Position.Top} style={handleStyle('#60a5fa', '#1e3a8a')} />
    <EditableLabel value={data?.label || 'Process'} onChange={v => data?.onLabelChange?.(id, v)} />
    <Handle type="source" position={Position.Bottom} style={handleStyle('#60a5fa', '#1e3a8a')} />
  </div>
);

export const InputOutputNode = ({ id, data, selected }: any) => (
  <div className={`${nodeStyle.base} ${selected ? nodeStyle.selected : ''} ${data?.hasError ? nodeStyle.error : ''} relative bg-gradient-to-br from-purple-900/80 to-violet-900/80 border-2 border-purple-400 text-purple-200 min-w-[130px] shadow-[0_0_12px_rgba(168,85,247,0.25)]`}
    style={{ clipPath: 'polygon(12% 0%, 100% 0%, 88% 100%, 0% 100%)', padding: '10px 24px' }}>
    <Handle type="target" position={Position.Top} style={{ ...handleStyle('#c084fc', '#4c1d95'), left: '50%' }} />
    <EditableLabel value={data?.label || 'Input/Output'} onChange={v => data?.onLabelChange?.(id, v)} />
    <Handle type="source" position={Position.Bottom} style={{ ...handleStyle('#c084fc', '#4c1d95'), left: '50%' }} />
  </div>
);

export const DecisionNode = ({ id, data, selected }: any) => (
  <div className={`relative flex items-center justify-center ${selected ? 'ring-2 ring-cyan-400 ring-offset-1 rounded' : ''} ${data?.hasError ? 'ring-2 ring-red-500' : ''}`}
    style={{ width: 140, height: 90 }}>
    <Handle type="target" position={Position.Top} style={{ ...handleStyle('#fbbf24', '#78350f'), top: 2 }} />
    <svg width="140" height="90" className="absolute inset-0">
      <polygon points="70,4 136,45 70,86 4,45" fill="rgba(120,100,0,0.7)" stroke="#fbbf24" strokeWidth="2" filter="drop-shadow(0 0 6px rgba(251,191,36,0.4))" />
    </svg>
    <div className="relative z-10 text-yellow-200 font-bold text-[11px] text-center px-4 max-w-[120px] leading-tight">
      <EditableLabel value={data?.label || 'Decision?'} onChange={v => data?.onLabelChange?.(id, v)} />
    </div>
    <Handle type="source" position={Position.Left} id="yes" style={{ ...handleStyle('#fbbf24', '#78350f'), left: 2 }} />
    <Handle type="source" position={Position.Right} id="no" style={{ ...handleStyle('#fbbf24', '#78350f'), right: 2 }} />
    <Handle type="source" position={Position.Bottom} id="bottom" style={{ ...handleStyle('#fbbf24', '#78350f'), bottom: 2 }} />
    <span className="absolute left-[-22px] top-[38px] text-[9px] text-yellow-400 font-bold">Yes</span>
    <span className="absolute right-[-18px] top-[38px] text-[9px] text-red-400 font-bold">No</span>
  </div>
);

export const DocumentNode = ({ id, data, selected }: any) => (
  <div className={`${nodeStyle.base} ${selected ? nodeStyle.selected : ''} ${data?.hasError ? nodeStyle.error : ''} bg-gradient-to-br from-cyan-900/80 to-sky-900/80 border-2 border-cyan-400 text-cyan-200 min-w-[120px] shadow-[0_0_10px_rgba(6,182,212,0.2)]`}
    style={{ padding: '10px 16px', clipPath: 'polygon(0% 0%, 100% 0%, 100% 75%, 50% 100%, 0% 75%)' }}>
    <Handle type="target" position={Position.Top} style={handleStyle('#22d3ee', '#155e75')} />
    <EditableLabel value={data?.label || 'Document'} onChange={v => data?.onLabelChange?.(id, v)} />
    <Handle type="source" position={Position.Bottom} style={{ ...handleStyle('#22d3ee', '#155e75'), bottom: -2 }} />
  </div>
);

export const DatabaseNode = ({ id, data, selected }: any) => (
  <div className={`${nodeStyle.base} ${selected ? nodeStyle.selected : ''} ${data?.hasError ? nodeStyle.error : ''} bg-gradient-to-br from-orange-900/80 to-amber-900/80 border-2 border-orange-400 text-orange-200 min-w-[100px] shadow-[0_0_10px_rgba(251,146,60,0.2)]`}
    style={{ padding: '14px 16px', borderRadius: '50% 50% 8px 8px / 30% 30% 8px 8px' }}>
    <Handle type="target" position={Position.Top} style={handleStyle('#fb923c', '#7c2d12')} />
    <EditableLabel value={data?.label || 'Database'} onChange={v => data?.onLabelChange?.(id, v)} />
    <Handle type="source" position={Position.Bottom} style={handleStyle('#fb923c', '#7c2d12')} />
  </div>
);

export const ConnectorNode = ({ id, data, selected }: any) => (
  <div className={`${nodeStyle.base} ${selected ? nodeStyle.selected : ''} ${data?.hasError ? nodeStyle.error : ''} bg-gradient-to-br from-slate-800/80 to-gray-800/80 border-2 border-gray-400 text-gray-300 rounded-full shadow-[0_0_10px_rgba(148,163,184,0.2)]`}
    style={{ width: 60, height: 60, padding: 4 }}>
    <Handle type="target" position={Position.Top} style={handleStyle('#94a3b8', '#334155')} />
    <EditableLabel value={data?.label || 'A'} onChange={v => data?.onLabelChange?.(id, v)} />
    <Handle type="source" position={Position.Bottom} style={handleStyle('#94a3b8', '#334155')} />
  </div>
);

export const PredefinedProcessNode = ({ id, data, selected }: any) => (
  <div className={`${nodeStyle.base} ${selected ? nodeStyle.selected : ''} ${data?.hasError ? nodeStyle.error : ''} bg-gradient-to-br from-indigo-900/80 to-blue-900/80 border-2 border-indigo-400 text-indigo-200 min-w-[130px] rounded`}
    style={{ padding: '10px 24px', boxShadow: 'inset 6px 0 0 #6366f1, inset -6px 0 0 #6366f1, 0 0 10px rgba(99,102,241,0.2)' }}>
    <Handle type="target" position={Position.Top} style={handleStyle('#818cf8', '#312e81')} />
    <EditableLabel value={data?.label || 'Function'} onChange={v => data?.onLabelChange?.(id, v)} />
    <Handle type="source" position={Position.Bottom} style={handleStyle('#818cf8', '#312e81')} />
  </div>
);

export const ManualInputNode = ({ id, data, selected }: any) => (
  <div className={`${nodeStyle.base} ${selected ? nodeStyle.selected : ''} ${data?.hasError ? nodeStyle.error : ''} bg-gradient-to-br from-rose-900/80 to-pink-900/80 border-2 border-rose-400 text-rose-200 min-w-[120px] shadow-[0_0_10px_rgba(244,63,94,0.2)]`}
    style={{ padding: '10px 20px', clipPath: 'polygon(15% 0%, 100% 0%, 100% 100%, 0% 100%)' }}>
    <Handle type="target" position={Position.Top} style={{ ...handleStyle('#fb7185', '#881337'), left: '60%' }} />
    <EditableLabel value={data?.label || 'Manual Input'} onChange={v => data?.onLabelChange?.(id, v)} />
    <Handle type="source" position={Position.Bottom} style={handleStyle('#fb7185', '#881337')} />
  </div>
);

export const OffpageNode = ({ id, data, selected }: any) => (
  <div className={`${nodeStyle.base} ${selected ? nodeStyle.selected : ''} ${data?.hasError ? nodeStyle.error : ''} bg-gradient-to-br from-teal-900/80 to-emerald-900/80 border-2 border-teal-400 text-teal-200 min-w-[90px]`}
    style={{ padding: '10px 16px 18px', clipPath: 'polygon(0 0, 100% 0, 100% 70%, 50% 100%, 0 70%)' }}>
    <Handle type="target" position={Position.Top} style={handleStyle('#2dd4bf', '#115e59')} />
    <EditableLabel value={data?.label || 'A'} onChange={v => data?.onLabelChange?.(id, v)} />
    <Handle type="source" position={Position.Bottom} style={handleStyle('#2dd4bf', '#115e59')} />
  </div>
);

export const DelayNode = ({ id, data, selected }: any) => (
  <div className={`${nodeStyle.base} ${selected ? nodeStyle.selected : ''} ${data?.hasError ? nodeStyle.error : ''} bg-gradient-to-br from-amber-900/80 to-yellow-900/80 border-2 border-amber-400 text-amber-200 min-w-[110px] shadow-[0_0_10px_rgba(251,191,36,0.2)]`}
    style={{ padding: '10px 20px', borderRadius: '8px 999px 999px 8px' }}>
    <Handle type="target" position={Position.Top} style={handleStyle('#fbbf24', '#78350f')} />
    <EditableLabel value={data?.label || 'Wait'} onChange={v => data?.onLabelChange?.(id, v)} />
    <Handle type="source" position={Position.Bottom} style={handleStyle('#fbbf24', '#78350f')} />
  </div>
);

export const ArrowNode = ({ id, data, selected }: any) => (
  <div className={`${nodeStyle.base} ${selected ? nodeStyle.selected : ''} ${data?.hasError ? nodeStyle.error : ''} bg-slate-800/80 border-2 border-cyan-400 text-cyan-200 min-w-[70px] rounded-md px-3 py-2`}>
    <Handle type="target" position={Position.Top} style={handleStyle('#22d3ee', '#155e75')} />
    <EditableLabel value={data?.label || '→'} onChange={v => data?.onLabelChange?.(id, v)} />
    <Handle type="source" position={Position.Bottom} style={handleStyle('#22d3ee', '#155e75')} />
  </div>
);

export const nodeTypes = {
  start_end: StartEndNode,
  process: ProcessNode,
  input_output: InputOutputNode,
  decision: DecisionNode,
  document: DocumentNode,
  database: DatabaseNode,
  connector: ConnectorNode,
  predefined_process: PredefinedProcessNode,
  manual_input: ManualInputNode,
  offpage: OffpageNode,
  delay: DelayNode,
  arrow: ArrowNode,
};
