import { useState, useEffect } from 'react';
import ReactFlow, {
  Background,
  Handle,
  Position,
  ReactFlowProvider,
  useReactFlow,
} from 'reactflow';
import 'reactflow/dist/style.css';

// --- Custom Editable Nodes ---

const StartEndNode = ({ id, data }: { id: string; data: any }) => {
  const [editing, setEditing] = useState(false);
  const [label, setLabel] = useState(data.label || 'Start');

  useEffect(() => {
    setLabel(data.label);
  }, [data.label]);

  const handleBlur = () => {
    setEditing(false);
    if (data.onLabelChange) {
      data.onLabelChange(id, label);
    }
  };

  return (
    <div className="bg-[#fce7f3] border-2 border-[#f472b6] text-[#db2777] font-bold px-6 py-2.5 rounded-full text-sm shadow-sm min-w-[110px] text-center transition-all hover:shadow-md group relative">
      <Handle type="target" position={Position.Top} className="!w-2.5 !h-2.5 !bg-[#ec4899] !border-white" />
      {editing ? (
        <input
          type="text"
          value={label}
          onChange={(e) => setLabel(e.target.value)}
          onBlur={handleBlur}
          onKeyDown={(e) => e.key === 'Enter' && handleBlur()}
          autoFocus
          className="bg-white/80 border border-[#f472b6] text-[#db2777] rounded px-1 text-center font-bold text-xs w-full focus:outline-none"
        />
      ) : (
        <span onDoubleClick={() => setEditing(true)} className="cursor-pointer select-none">
          {label}
        </span>
      )}
      <Handle type="source" position={Position.Bottom} className="!w-2.5 !h-2.5 !bg-[#ec4899] !border-white" />
    </div>
  );
};

const ProcessNode = ({ id, data }: { id: string; data: any }) => {
  const [editing, setEditing] = useState(false);
  const [label, setLabel] = useState(data.label || 'Process');

  useEffect(() => {
    setLabel(data.label);
  }, [data.label]);

  const handleBlur = () => {
    setEditing(false);
    if (data.onLabelChange) {
      data.onLabelChange(id, label);
    }
  };

  return (
    <div className="bg-[#eff6ff] border-2 border-[#60a5fa] text-[#1d4ed8] font-bold px-6 py-3 rounded-xl text-sm shadow-sm min-w-[130px] text-center transition-all hover:shadow-md group relative">
      <Handle type="target" position={Position.Top} className="!w-2.5 !h-2.5 !bg-[#3b82f6] !border-white" />
      {editing ? (
        <input
          type="text"
          value={label}
          onChange={(e) => setLabel(e.target.value)}
          onBlur={handleBlur}
          onKeyDown={(e) => e.key === 'Enter' && handleBlur()}
          autoFocus
          className="bg-white/80 border border-[#60a5fa] text-[#1d4ed8] rounded px-1 text-center font-bold text-xs w-full focus:outline-none"
        />
      ) : (
        <span onDoubleClick={() => setEditing(true)} className="cursor-pointer select-none">
          {label}
        </span>
      )}
      <Handle type="source" position={Position.Bottom} className="!w-2.5 !h-2.5 !bg-[#3b82f6] !border-white" />
    </div>
  );
};

const InputOutputNode = ({ id, data }: { id: string; data: any }) => {
  const [editing, setEditing] = useState(false);
  const [label, setLabel] = useState(data.label || 'Input');

  useEffect(() => {
    setLabel(data.label);
  }, [data.label]);

  const handleBlur = () => {
    setEditing(false);
    if (data.onLabelChange) {
      data.onLabelChange(id, label);
    }
  };

  return (
    <div className="relative min-w-[130px] text-center group">
      <div className="absolute inset-0 bg-[#f0fdf4] border-2 border-[#4ade80] skew-x-[-15deg] rounded-lg shadow-sm group-hover:shadow-md transition-all" />
      <div className="relative px-6 py-3 font-bold text-[#15803d] text-sm z-10">
        {editing ? (
          <input
            type="text"
            value={label}
            onChange={(e) => setLabel(e.target.value)}
            onBlur={handleBlur}
            onKeyDown={(e) => e.key === 'Enter' && handleBlur()}
            autoFocus
            className="bg-white/90 border border-[#4ade80] text-[#15803d] rounded px-1 text-center font-bold text-xs w-full focus:outline-none"
          />
        ) : (
          <span onDoubleClick={() => setEditing(true)} className="cursor-pointer select-none">
            {label}
          </span>
        )}
      </div>
      <Handle type="target" position={Position.Top} className="!w-2.5 !h-2.5 !bg-[#22c55e] !border-white z-20" />
      <Handle type="source" position={Position.Bottom} className="!w-2.5 !h-2.5 !bg-[#22c55e] !border-white z-20" />
    </div>
  );
};

const DecisionNode = ({ id, data }: { id: string; data: any }) => {
  const [editing, setEditing] = useState(false);
  const [label, setLabel] = useState(data.label || 'Decision');

  useEffect(() => {
    setLabel(data.label);
  }, [data.label]);

  const handleBlur = () => {
    setEditing(false);
    if (data.onLabelChange) {
      data.onLabelChange(id, label);
    }
  };

  return (
    <div className="relative w-28 h-28 flex items-center justify-center group">
      <div className="absolute w-20 h-20 bg-[#fefce8] border-2 border-[#facc15] rotate-45 rounded-lg shadow-sm group-hover:shadow-md transition-all" />
      <div className="relative font-bold text-[#854d0e] text-xs text-center p-2 z-10 max-w-[85px]">
        {editing ? (
          <input
            type="text"
            value={label}
            onChange={(e) => setLabel(e.target.value)}
            onBlur={handleBlur}
            onKeyDown={(e) => e.key === 'Enter' && handleBlur()}
            autoFocus
            className="bg-white/90 border border-[#facc15] text-[#854d0e] rounded px-1 text-center font-bold text-xs w-full focus:outline-none"
          />
        ) : (
          <span onDoubleClick={() => setEditing(true)} className="cursor-pointer select-none">
            {label}
          </span>
        )}
      </div>
      <Handle type="target" position={Position.Top} className="!w-2.5 !h-2.5 !bg-[#eab308] !border-white z-20" />
      <Handle type="source" position={Position.Bottom} id="bottom" className="!w-2.5 !h-2.5 !bg-[#eab308] !border-white z-20" />
      <Handle type="source" position={Position.Left} id="left" className="!w-2.5 !h-2.5 !bg-[#eab308] !border-white z-20" />
      <Handle type="source" position={Position.Right} id="right" className="!w-2.5 !h-2.5 !bg-[#eab308] !border-white z-20" />
    </div>
  );
};

const nodeTypes = {
  start_end: StartEndNode,
  process: ProcessNode,
  input_output: InputOutputNode,
  decision: DecisionNode,
};

// Controls bar component inside canvas
const CustomCanvasControls = () => {
  const { zoomIn, zoomOut, fitView, getZoom } = useReactFlow();
  const [zoomPercent, setZoomPercent] = useState(100);

  useEffect(() => {
    const interval = setInterval(() => {
      try {
        setZoomPercent(Math.round(getZoom() * 100));
      } catch (e) {}
    }, 300);
    return () => clearInterval(interval);
  }, [getZoom]);

  return (
    <div className="absolute bottom-4 right-4 z-10 bg-white/90 backdrop-blur border border-gray-200 rounded-xl shadow-md p-1 flex items-center gap-1 text-gray-700 text-xs font-semibold select-none">
      <button
        onClick={() => zoomOut()}
        className="w-7 h-7 flex items-center justify-center hover:bg-gray-100 rounded-lg transition-colors font-bold text-base"
        title="Zoom Out"
      >
        −
      </button>
      <span className="px-2 font-mono text-gray-600 text-[11px] min-w-[40px] text-center">{zoomPercent}%</span>
      <button
        onClick={() => zoomIn()}
        className="w-7 h-7 flex items-center justify-center hover:bg-gray-100 rounded-lg transition-colors font-bold text-base"
        title="Zoom In"
      >
        +
      </button>
      <div className="w-[1px] h-4 bg-gray-200 mx-0.5" />
      <button
        onClick={() => fitView()}
        className="p-1.5 hover:bg-gray-100 rounded-lg transition-colors text-gray-600"
        title="Fit View"
      >
        <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <path d="M15 3h6v6M9 21H3v-6M21 3l-7 7M3 21l7-7" />
        </svg>
      </button>
    </div>
  );
};

export const FlowchartCanvasInner = ({
  nodes,
  edges,
  onNodesChange,
  onEdgesChange,
  onConnect,
  onDrop,
  onDragOver,
  setReactFlowInstance,
}: any) => {
  return (
    <div className="w-full h-full relative">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onConnect={onConnect}
        onInit={setReactFlowInstance}
        onDrop={onDrop}
        onDragOver={onDragOver}
        nodeTypes={nodeTypes}
        fitView
        className="bg-transparent"
        defaultEdgeOptions={{
          style: { strokeWidth: 2, stroke: '#94a3b8' },
          type: 'smoothstep',
          animated: true,
        }}
      >
        <Background color="#cbd5e1" gap={20} size={1.5} />
      </ReactFlow>
      <CustomCanvasControls />
    </div>
  );
};

export const FlowchartCanvas = (props: any) => (
  <ReactFlowProvider>
    <FlowchartCanvasInner {...props} />
  </ReactFlowProvider>
);
