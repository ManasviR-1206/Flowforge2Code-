import { useState, useCallback, useEffect } from 'react';
import { WorkspaceHeader } from '../components/WorkspaceHeader';
import { Sidebar } from '../components/Sidebar';
import { FlowchartCanvas } from '../components/FlowchartCanvas';
import { ApiKeysSettingsView } from '../components/ApiKeysSettingsView';
import { SavedProjectsView } from '../components/SavedProjectsView';
import { UploadImageView } from '../components/UploadImageView';
import { DocsView } from '../components/DocsView';
import { FeedbackView } from '../components/FeedbackView';

import {
  addEdge,
  applyNodeChanges,
  applyEdgeChanges,
} from 'reactflow';
import type {
  Node,
  Edge,
  Connection,
  NodeChange,
  EdgeChange,
} from 'reactflow';
import { 
  Undo, 
  Redo, 
  Trash2, 
  Download, 
  ZoomIn, 
  Play, 
  Code2, 
  Copy, 
  Check, 
  Save, 
  Clock, 
  UploadCloud, 
  Pencil,
  FileCode,
  Layers,
  X
} from 'lucide-react';

// Default initial nodes matching image.png exactly
const initialNodes: Node[] = [
  { id: '1', type: 'start_end', position: { x: 230, y: 30 }, data: { label: 'Start' } },
  { id: '2', type: 'input_output', position: { x: 230, y: 130 }, data: { label: 'Input n' } },
  { id: '3', type: 'decision', position: { x: 230, y: 230 }, data: { label: 'n > 0?' } },
  { id: '4', type: 'process', position: { x: 110, y: 370 }, data: { label: 'Print "Positive"' } },
  { id: '5', type: 'process', position: { x: 340, y: 370 }, data: { label: 'Print "Negative"' } },
  { id: '6', type: 'start_end', position: { x: 230, y: 490 }, data: { label: 'End' } },
];

const initialEdges: Edge[] = [
  { id: 'e1-2', source: '1', target: '2', type: 'smoothstep', animated: true },
  { id: 'e2-3', source: '2', target: '3', type: 'smoothstep', animated: true },
  { id: 'e3-4', source: '3', sourceHandle: 'left', target: '4', type: 'smoothstep', label: 'Yes', animated: true },
  { id: 'e3-5', source: '3', sourceHandle: 'right', target: '5', type: 'smoothstep', label: 'No', animated: true },
  { id: 'e4-6', source: '4', target: '6', type: 'smoothstep', animated: true },
  { id: 'e5-6', source: '5', target: '6', type: 'smoothstep', animated: true },
];

let idCounter = 10;
const getId = () => `dndnode_${idCounter++}`;

export const WorkspacePage: React.FC = () => {
  const [activeTab, setActiveTab] = useState('dashboard');
  
  // Canvas State
  const [nodes, setNodes] = useState<Node[]>(initialNodes);
  const [edges, setEdges] = useState<Edge[]>(initialEdges);
  const [reactFlowInstance, setReactFlowInstance] = useState<any>(null);

  // Undo / Redo history state
  const [history, setHistory] = useState<{ nodes: Node[]; edges: Edge[] }[]>([]);
  const [redoStack, setRedoStack] = useState<{ nodes: Node[]; edges: Edge[] }[]>([]);

  // Generation & Execution State
  const [generatedCode, setGeneratedCode] = useState(
    '# Generated code from flowchart\nn = int(input("Enter n: "))\nif n > 0:\n    print("Positive")\nelse:\n    print("Negative")'
  );
  const [userInput, setUserInput] = useState('5');
  const [executionOutput, setExecutionOutput] = useState('Positive');
  const [logicJson, setLogicJson] = useState(
    JSON.stringify(
      [
        { type: "start", next: 2 },
        { type: "input", text: "n", next: 3 },
        { type: "decision", condition: "n > 0", yes: 4, no: 5 },
        { id: 4, type: "output", text: "Positive", next: 6 },
        { id: 5, type: "output", text: "Negative", next: 6 },
        { id: 6, type: "end" }
      ],
      null,
      2
    )
  );

  const [loadingCode, setLoadingCode] = useState(false);
  const [loadingRun, setLoadingRun] = useState(false);
  const [copiedCode, setCopiedCode] = useState(false);

  // Modal State for Save Project
  const [saveModalOpen, setSaveModalOpen] = useState(false);
  const [projectName, setProjectName] = useState('My Flowchart Project');
  const [savingProject, setSavingProject] = useState(false);
  const [saveMessage, setSaveMessage] = useState<string | null>(null);

  // History logs
  const [historyLogs, setHistoryLogs] = useState<{ id: string; time: string; code: string; output: string }[]>([
    {
      id: '1',
      time: new Date().toLocaleTimeString(),
      code: 'n = int(input("Enter n: "))\nif n > 0:\n    print("Positive")\nelse:\n    print("Negative")',
      output: 'Positive'
    }
  ]);

  // Label change callback for custom nodes
  const handleLabelChange = useCallback((nodeId: string, newLabel: string) => {
    setNodes((prevNodes) =>
      prevNodes.map((n) => (n.id === nodeId ? { ...n, data: { ...n.data, label: newLabel } } : n))
    );
  }, []);

  // Update nodes with callback
  useEffect(() => {
    setNodes((nds) =>
      nds.map((n) => ({
        ...n,
        data: {
          ...n.data,
          onLabelChange: handleLabelChange,
        },
      }))
    );
  }, [handleLabelChange]);

  // Push current state to undo history
  const saveSnapshot = useCallback(() => {
    setHistory((prev) => [...prev.slice(-20), { nodes, edges }]);
    setRedoStack([]);
  }, [nodes, edges]);

  const onNodesChange = useCallback((changes: NodeChange[]) => {
    setNodes((nds) => applyNodeChanges(changes, nds));
  }, []);

  const onEdgesChange = useCallback((changes: EdgeChange[]) => {
    setEdges((eds) => applyEdgeChanges(changes, eds));
  }, []);

  const onConnect = useCallback((params: Connection | Edge) => {
    saveSnapshot();
    setEdges((eds) => addEdge({ ...params, type: 'smoothstep', animated: true }, eds));
  }, [saveSnapshot]);

  const onDragOver = useCallback((event: React.DragEvent) => {
    event.preventDefault();
    event.dataTransfer.dropEffect = 'move';
  }, []);

  const onDrop = useCallback(
    (event: React.DragEvent) => {
      event.preventDefault();
      const type = event.dataTransfer.getData('application/reactflow');
      if (!type || !reactFlowInstance) return;

      saveSnapshot();
      const position = reactFlowInstance.screenToFlowPosition({
        x: event.clientX,
        y: event.clientY,
      });

      let label = 'Node';
      if (type === 'start_end') label = 'Start/End';
      if (type === 'process') label = 'Process Step';
      if (type === 'input_output') label = 'Input x';
      if (type === 'decision') label = 'x > 0?';

      const newNode: Node = {
        id: getId(),
        type,
        position,
        data: { label, onLabelChange: handleLabelChange },
      };
      setNodes((nds) => nds.concat(newNode));
    },
    [reactFlowInstance, handleLabelChange, saveSnapshot]
  );

  // Canvas Actions
  const handleUndo = () => {
    if (history.length === 0) return;
    const last = history[history.length - 1];
    setRedoStack((prev) => [...prev, { nodes, edges }]);
    setNodes(last.nodes);
    setEdges(last.edges);
    setHistory((prev) => prev.slice(0, -1));
  };

  const handleRedo = () => {
    if (redoStack.length === 0) return;
    const next = redoStack[redoStack.length - 1];
    setHistory((prev) => [...prev, { nodes, edges }]);
    setNodes(next.nodes);
    setEdges(next.edges);
    setRedoStack((prev) => prev.slice(0, -1));
  };

  const handleClear = () => {
    if (nodes.length === 0) return;
    saveSnapshot();
    setNodes([]);
    setEdges([]);
  };

  const handleDeleteSelected = () => {
    saveSnapshot();
    setNodes((nds) => nds.filter((n) => !n.selected));
    setEdges((eds) => eds.filter((e) => !e.selected));
  };

  const handleDownload = () => {
    const dataStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify({ nodes, edges, generatedCode }, null, 2));
    const downloadAnchor = document.createElement('a');
    downloadAnchor.setAttribute("href", dataStr);
    downloadAnchor.setAttribute("download", `${projectName.toLowerCase().replace(/\s+/g, '_')}_flowchart.json`);
    document.body.appendChild(downloadAnchor);
    downloadAnchor.click();
    downloadAnchor.remove();
  };

  const handleZoomReset = () => {
    if (reactFlowInstance) {
      reactFlowInstance.fitView({ padding: 0.2, duration: 400 });
    }
  };

  // Code Generation
  const handleGenerateCode = async () => {
    setLoadingCode(true);
    try {
      const blocks = nodes.map((n) => ({
        id: n.id,
        type: n.type,
        text: n.data.label,
        bbox: [0, 0, 0, 0],
      }));
      const connections = edges.map((e) => ({
        from: e.source,
        to: e.target,
        branch: e.label || (e.sourceHandle === 'left' ? 'Yes' : e.sourceHandle === 'right' ? 'No' : null),
      }));

      const userApiKey = localStorage.getItem('ff_gemini_key') || '';

      const res = await fetch('/api/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ blocks, connections, api_key: userApiKey }),
      });

      if (res.ok) {
        const data = await res.json();
        if (data.code) {
          setGeneratedCode(data.code);
          setLogicJson(JSON.stringify(data.ast, null, 2));
        }
      }
    } catch (err: any) {
      console.error(err);
    }
    setLoadingCode(false);
  };

  // Code Execution
  const handleRunCode = async () => {
    if (!generatedCode) return;
    setLoadingRun(true);
    setExecutionOutput('Running Python script...');
    try {
      const res = await fetch('/api/run', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ code: generatedCode, user_input: userInput }),
      });
      if (res.ok) {
        const data = await res.json();
        const out = data.output || 'Code executed successfully with no output.';
        setExecutionOutput(out);

        // Add to history log
        setHistoryLogs((prev) => [
          {
            id: String(Date.now()),
            time: new Date().toLocaleTimeString(),
            code: generatedCode,
            output: out,
          },
          ...prev,
        ]);
      }
    } catch (err: any) {
      setExecutionOutput(`Execution Error: ${err.message}`);
    }
    setLoadingRun(false);
  };

  const handleCopyCode = () => {
    navigator.clipboard.writeText(generatedCode);
    setCopiedCode(true);
    setTimeout(() => setCopiedCode(false), 2000);
  };

  // Save Project to Database
  const handleSaveProject = async () => {
    setSavingProject(true);
    setSaveMessage(null);
    try {
      const res = await fetch('/api/projects', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: projectName,
          nodes,
          edges,
          code: generatedCode,
        }),
      });

      if (res.ok) {
        setSaveMessage('Project saved successfully to database!');
        setTimeout(() => {
          setSaveModalOpen(false);
          setSaveMessage(null);
        }, 1500);
      }
    } catch (err: any) {
      setSaveMessage(`Save failed: ${err.message}`);
    }
    setSavingProject(false);
  };

  // Handle Load Saved Project from SavedProjectsView
  const handleLoadProject = (projectData: any) => {
    if (projectData.nodes && projectData.nodes.length > 0) {
      setNodes(projectData.nodes);
    }
    if (projectData.edges) {
      setEdges(projectData.edges);
    }
    if (projectData.generated_code) {
      setGeneratedCode(projectData.generated_code);
    }
    if (projectData.name) {
      setProjectName(projectData.name);
    }
    setActiveTab('dashboard');
  };

  // Import detected vision analysis flowchart
  const handleImportVisionFlowchart = (data: { blocks: any[]; connections: any[] }) => {
    saveSnapshot();
    const newNodes: Node[] = data.blocks.map((b, idx) => ({
      id: String(b.id || idx + 1),
      type: b.type === 'start' || b.type === 'end' ? 'start_end' : b.type,
      position: { x: 230, y: 50 + idx * 90 },
      data: { label: b.text || b.type, onLabelChange: handleLabelChange },
    }));

    const newEdges: Edge[] = data.connections.map((c, idx) => ({
      id: `cv_e_${idx}`,
      source: String(c.from),
      target: String(c.to),
      type: 'smoothstep',
      animated: true,
    }));

    setNodes(newNodes);
    setEdges(newEdges);
    setActiveTab('dashboard');
  };

  // Tab router dispatcher
  const renderTabContent = () => {
    switch (activeTab) {
      case 'settings':
        return <ApiKeysSettingsView />;
      case 'projects':
        return <SavedProjectsView onLoadProject={handleLoadProject} />;
      case 'upload':
        return <UploadImageView onAnalyzeSuccess={handleImportVisionFlowchart} />;
      case 'docs':
        return <DocsView />;
      case 'feedback':
        return <FeedbackView />;
      case 'history':
        return (
          <div className="max-w-4xl mx-auto p-6 space-y-6">
            <h2 className="text-2xl font-bold text-gray-900 flex items-center gap-2.5">
              <Clock className="w-6 h-6 text-indigo-600" />
              Execution & Generation History
            </h2>
            <div className="space-y-4">
              {historyLogs.map((log) => (
                <div key={log.id} className="bg-white rounded-2xl border border-gray-200 p-5 shadow-xs space-y-3">
                  <div className="flex items-center justify-between text-xs text-gray-500 font-semibold border-b border-gray-100 pb-2">
                    <span>Execution at {log.time}</span>
                    <span className="text-green-600 font-bold">● Status 200 OK</span>
                  </div>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div className="bg-gray-900 text-gray-100 p-3 rounded-xl font-mono text-xs overflow-x-auto">
                      <p className="text-gray-500 text-[10px] uppercase font-bold mb-1">Generated Code</p>
                      <pre>{log.code}</pre>
                    </div>
                    <div className="bg-gray-950 text-green-400 p-3 rounded-xl font-mono text-xs">
                      <p className="text-gray-500 text-[10px] uppercase font-bold mb-1">Output Result</p>
                      <pre>{log.output}</pre>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        );
      case 'create':
      case 'generate':
      case 'run':
      case 'dashboard':
      default:
        return (
          <div className="p-6 space-y-6 max-w-[1600px] mx-auto">
            {/* Top Banner Card matching reference screenshot */}
            <div className="relative overflow-hidden bg-gradient-to-r from-blue-50/90 via-indigo-50/70 to-purple-50/80 rounded-2xl border border-indigo-100/80 p-6 sm:p-8 flex flex-col md:flex-row items-center justify-between gap-6 shadow-xs">
              <div className="space-y-2 max-w-xl">
                <h2 className="text-2xl sm:text-3xl font-extrabold text-gray-900 tracking-tight">
                  Draw. Understand.{' '}
                  <span className="text-transparent bg-clip-text bg-gradient-to-r from-blue-600 to-indigo-600">
                    Generate.
                  </span>{' '}
                  <span className="text-transparent bg-clip-text bg-gradient-to-r from-purple-600 to-pink-600">
                    Run.
                  </span>
                </h2>
                <p className="text-sm font-medium text-gray-600">
                  Convert your flowcharts into clean Python code using AI.
                </p>
              </div>

              {/* Banner Right Graphic Illustration */}
              <div className="flex items-center gap-4 bg-white/80 backdrop-blur-sm p-3 px-5 rounded-2xl border border-indigo-100/60 shadow-sm shrink-0">
                {/* Flowchart Mini Box */}
                <div className="flex flex-col items-center gap-1.5 p-2 bg-indigo-50/50 rounded-xl border border-indigo-100">
                  <div className="w-8 h-4 bg-pink-100 border border-pink-400 rounded-full" />
                  <div className="w-0.5 h-2 bg-gray-400" />
                  <div className="w-8 h-4 bg-green-100 border border-green-400 skew-x-[-10deg]" />
                </div>
                {/* Arrow */}
                <div className="text-indigo-500 font-bold text-xl">➔</div>
                {/* Code Window Box */}
                <div className="w-24 h-14 bg-gray-900 rounded-xl p-2 flex flex-col justify-between shadow-md border border-gray-800">
                  <div className="flex items-center gap-1">
                    <div className="w-1.5 h-1.5 rounded-full bg-red-400" />
                    <div className="w-1.5 h-1.5 rounded-full bg-yellow-400" />
                    <div className="w-1.5 h-1.5 rounded-full bg-green-400" />
                  </div>
                  <div className="text-[10px] font-mono text-cyan-400 flex items-center justify-between">
                    <span>&lt;/&gt;</span>
                    <span className="text-xs">🐍</span>
                  </div>
                </div>
              </div>
            </div>

            {/* Main 3-Column Workspace Grid */}
            <div className="grid grid-cols-1 lg:grid-cols-[270px_1fr_390px] gap-6 items-start">
              
              {/* COLUMN 1: Flowchart Tools */}
              <div className="bg-white rounded-2xl border border-gray-200 shadow-sm flex flex-col h-[710px]">
                <div className="p-4 border-b border-gray-100 flex items-center justify-between">
                  <h3 className="font-bold text-gray-800 text-sm flex items-center gap-2">
                    <Layers className="w-4 h-4 text-indigo-500" />
                    Flowchart Tools
                  </h3>
                  <button className="text-gray-400 hover:text-gray-600 text-xs">▲</button>
                </div>

                <div className="p-4 flex-1 overflow-y-auto space-y-6">
                  <p className="text-xs text-gray-500">Drag and drop shapes to create your flowchart</p>

                  {/* Shapes */}
                  <div className="space-y-3">
                    {/* Start / End */}
                    <div
                      draggable
                      onDragStart={(e) => e.dataTransfer.setData('application/reactflow', 'start_end')}
                      className="flex items-center gap-3.5 p-2 rounded-xl border border-gray-100 hover:border-pink-200 hover:bg-pink-50/50 cursor-grab active:cursor-grabbing transition-all group"
                    >
                      <div className="w-14 h-7 bg-[#fce7f3] border-2 border-[#f472b6] rounded-full shadow-2xs shrink-0" />
                      <span className="text-xs font-bold text-gray-700 group-hover:text-pink-600 transition-colors">
                        Start / End
                      </span>
                    </div>

                    {/* Process */}
                    <div
                      draggable
                      onDragStart={(e) => e.dataTransfer.setData('application/reactflow', 'process')}
                      className="flex items-center gap-3.5 p-2 rounded-xl border border-gray-100 hover:border-blue-200 hover:bg-blue-50/50 cursor-grab active:cursor-grabbing transition-all group"
                    >
                      <div className="w-14 h-7 bg-[#eff6ff] border-2 border-[#60a5fa] rounded-lg shadow-2xs shrink-0" />
                      <span className="text-xs font-bold text-gray-700 group-hover:text-blue-600 transition-colors">
                        Process
                      </span>
                    </div>

                    {/* Input / Output */}
                    <div
                      draggable
                      onDragStart={(e) => e.dataTransfer.setData('application/reactflow', 'input_output')}
                      className="flex items-center gap-3.5 p-2 rounded-xl border border-gray-100 hover:border-green-200 hover:bg-green-50/50 cursor-grab active:cursor-grabbing transition-all group"
                    >
                      <div className="w-14 h-7 bg-[#f0fdf4] border-2 border-[#4ade80] skew-x-[-15deg] rounded shadow-2xs shrink-0 ml-1" />
                      <span className="text-xs font-bold text-gray-700 group-hover:text-green-600 transition-colors">
                        Input / Output
                      </span>
                    </div>

                    {/* Decision */}
                    <div
                      draggable
                      onDragStart={(e) => e.dataTransfer.setData('application/reactflow', 'decision')}
                      className="flex items-center gap-3.5 p-2 rounded-xl border border-gray-100 hover:border-yellow-200 hover:bg-yellow-50/50 cursor-grab active:cursor-grabbing transition-all group"
                    >
                      <div className="w-8 h-8 bg-[#fefce8] border-2 border-[#facc15] rotate-45 rounded shadow-2xs shrink-0 ml-3 mr-3 my-1" />
                      <span className="text-xs font-bold text-gray-700 group-hover:text-yellow-600 transition-colors">
                        Decision
                      </span>
                    </div>

                    {/* Arrow / Connector */}
                    <div className="flex items-center gap-3.5 p-2.5 rounded-xl border border-gray-100 bg-gray-50/50 text-gray-600">
                      <div className="w-14 text-center font-bold text-gray-400">➔</div>
                      <span className="text-xs font-bold text-gray-700">Arrow / Connector</span>
                    </div>
                  </div>

                  {/* Canvas Actions */}
                  <div className="border-t border-gray-100 pt-5 space-y-3">
                    <div className="flex items-center justify-between">
                      <h4 className="text-xs font-extrabold text-gray-800 uppercase tracking-wider">
                        Canvas Actions
                      </h4>
                      <button
                        onClick={() => setSaveModalOpen(true)}
                        className="text-xs text-indigo-600 font-bold hover:underline flex items-center gap-1"
                      >
                        <Save size={12} /> Save
                      </button>
                    </div>

                    <div className="grid grid-cols-2 gap-2">
                      <button
                        onClick={handleUndo}
                        disabled={history.length === 0}
                        className="flex items-center justify-center gap-1.5 py-2 px-3 bg-white border border-gray-200 rounded-xl text-xs font-semibold text-gray-700 hover:bg-gray-50 disabled:opacity-40 transition-all shadow-2xs"
                      >
                        <Undo size={14} /> Undo
                      </button>
                      <button
                        onClick={handleRedo}
                        disabled={redoStack.length === 0}
                        className="flex items-center justify-center gap-1.5 py-2 px-3 bg-white border border-gray-200 rounded-xl text-xs font-semibold text-gray-700 hover:bg-gray-50 disabled:opacity-40 transition-all shadow-2xs"
                      >
                        <Redo size={14} /> Redo
                      </button>
                      <button
                        onClick={handleClear}
                        className="flex items-center justify-center gap-1.5 py-2 px-3 bg-white border border-gray-200 rounded-xl text-xs font-semibold text-gray-700 hover:bg-red-50 hover:text-red-600 hover:border-red-200 transition-all shadow-2xs"
                      >
                        <Trash2 size={14} /> Clear
                      </button>
                      <button
                        onClick={handleDeleteSelected}
                        className="flex items-center justify-center gap-1.5 py-2 px-3 bg-white border border-gray-200 rounded-xl text-xs font-semibold text-gray-700 hover:bg-red-50 hover:text-red-600 hover:border-red-200 transition-all shadow-2xs"
                      >
                        <Trash2 size={14} /> Delete
                      </button>
                      <button
                        onClick={handleDownload}
                        className="flex items-center justify-center gap-1.5 py-2 px-3 bg-white border border-gray-200 rounded-xl text-xs font-semibold text-gray-700 hover:bg-gray-50 transition-all shadow-2xs"
                      >
                        <Download size={14} /> Download
                      </button>
                      <button
                        onClick={handleZoomReset}
                        className="flex items-center justify-center gap-1.5 py-2 px-3 bg-white border border-gray-200 rounded-xl text-xs font-semibold text-gray-700 hover:bg-gray-50 transition-all shadow-2xs"
                      >
                        <ZoomIn size={14} /> Zoom
                      </button>
                    </div>
                  </div>
                </div>
              </div>

              {/* COLUMN 2: Flowchart Canvas */}
              <div className="bg-white rounded-2xl border border-gray-200 shadow-sm flex flex-col h-[710px] overflow-hidden">
                <div className="p-4 border-b border-gray-100 flex items-center justify-between bg-white z-10">
                  <h3 className="font-bold text-gray-800 text-sm flex items-center gap-2">
                    <span className="w-5 h-5 rounded-lg bg-blue-100 text-blue-600 flex items-center justify-center text-xs">
                      ⬡
                    </span>
                    Flowchart Canvas
                  </h3>
                  <div className="flex gap-2">
                    <button className="flex items-center gap-1.5 px-3.5 py-1.5 bg-indigo-50 text-indigo-600 border border-indigo-100 rounded-xl text-xs font-bold hover:bg-indigo-100 transition-all">
                      <Pencil size={14} /> Draw
                    </button>
                    <button
                      onClick={() => setActiveTab('upload')}
                      className="flex items-center gap-1.5 px-3.5 py-1.5 bg-white text-gray-700 border border-gray-200 rounded-xl text-xs font-bold hover:bg-gray-50 transition-all"
                    >
                      <UploadCloud size={14} /> Upload
                    </button>
                  </div>
                </div>

                {/* Canvas Container */}
                <div className="flex-1 relative">
                  <FlowchartCanvas
                    nodes={nodes}
                    edges={edges}
                    onNodesChange={onNodesChange}
                    onEdgesChange={onEdgesChange}
                    onConnect={onConnect}
                    setReactFlowInstance={setReactFlowInstance}
                    onDrop={onDrop}
                    onDragOver={onDragOver}
                  />
                </div>
              </div>

              {/* COLUMN 3: Code & Execution Results */}
              <div className="flex flex-col gap-5">
                
                {/* Generated Python Code Card */}
                <div className="bg-white rounded-2xl border border-gray-200 shadow-sm flex flex-col overflow-hidden">
                  <div className="p-3.5 px-4 border-b border-gray-100 flex items-center justify-between bg-white">
                    <h3 className="font-bold text-gray-800 text-xs flex items-center gap-1.5">
                      <Code2 className="w-4 h-4 text-blue-600" />
                      Generated Python Code
                    </h3>
                    <div className="flex items-center gap-2">
                      <button
                        onClick={handleGenerateCode}
                        disabled={loadingCode}
                        className="px-2.5 py-1 bg-blue-50 border border-blue-200 text-blue-600 rounded-lg text-xs font-bold hover:bg-blue-100 disabled:opacity-50 transition-all"
                      >
                        {loadingCode ? 'Generating...' : 'Generate'}
                      </button>
                      <div className="flex items-center gap-1 bg-gray-50 border border-gray-200 rounded-lg px-2 py-0.5 text-xs text-gray-700 font-semibold">
                        <span>🐍</span>
                        <span>Python v</span>
                      </div>
                      <button
                        onClick={handleCopyCode}
                        className="p-1 text-gray-400 hover:text-gray-600 bg-gray-50 border border-gray-200 rounded-lg transition-colors"
                        title="Copy Code"
                      >
                        {copiedCode ? <Check size={14} className="text-green-600" /> : <Copy size={14} />}
                      </button>
                    </div>
                  </div>

                  <div className="p-4 bg-[#0d1117] text-gray-100 font-mono text-xs overflow-x-auto min-h-[170px] max-h-[210px] overflow-y-auto leading-relaxed select-text">
                    {generatedCode.split('\n').map((line, i) => (
                      <div key={i} className="flex">
                        <span className="w-6 inline-block text-gray-600 select-none mr-3 text-right">
                          {i + 1}
                        </span>
                        <span
                          className={
                            line.includes('#')
                              ? 'text-gray-500 italic'
                              : line.includes('input')
                              ? 'text-cyan-400'
                              : line.includes('print')
                              ? 'text-blue-300 font-semibold'
                              : line.includes('if') || line.includes('else')
                              ? 'text-pink-400 font-bold'
                              : 'text-gray-200'
                          }
                        >
                          {line}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Run Code Card */}
                <div className="bg-white rounded-2xl border border-gray-200 shadow-sm p-4 space-y-3">
                  <div className="flex items-center justify-between">
                    <h3 className="font-bold text-gray-800 text-xs flex items-center gap-2">
                      <div className="w-5 h-5 rounded-full bg-green-100 flex items-center justify-center text-green-600 text-xs">
                        ▶
                      </div>
                      Run Code
                    </h3>
                    <button
                      onClick={handleRunCode}
                      disabled={loadingRun}
                      className="flex items-center gap-1.5 px-4 py-1.5 bg-indigo-600 text-white rounded-xl text-xs font-bold hover:bg-indigo-700 transition-all shadow-xs disabled:opacity-50"
                    >
                      <Play size={12} className="fill-current" />
                      {loadingRun ? 'Running...' : 'Run'}
                    </button>
                  </div>

                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <label className="flex items-center gap-1 text-[11px] font-bold text-gray-600 mb-1">
                        Input
                      </label>
                      <input
                        type="text"
                        value={userInput}
                        onChange={(e) => setUserInput(e.target.value)}
                        placeholder="5"
                        className="w-full bg-white border border-gray-200 rounded-xl px-3 py-2 text-xs text-gray-800 font-mono focus:outline-none focus:border-blue-400 focus:ring-1 focus:ring-blue-400"
                      />
                    </div>
                    <div>
                      <label className="flex items-center gap-1 text-[11px] font-bold text-gray-600 mb-1">
                        Output
                      </label>
                      <div className="w-full bg-[#0d1117] border border-gray-800 rounded-xl px-3 py-2 text-xs text-green-400 font-mono min-h-[38px] flex items-center shadow-inner overflow-x-auto">
                        {executionOutput}
                      </div>
                    </div>
                  </div>
                </div>

                {/* Generated Logic (JSON) Card */}
                <div className="bg-white rounded-2xl border border-gray-200 shadow-sm flex flex-col h-[200px] overflow-hidden">
                  <div className="p-3 px-4 border-b border-gray-100 flex items-center justify-between bg-white">
                    <h3 className="font-bold text-gray-800 text-xs flex items-center gap-1.5">
                      <FileCode className="w-4 h-4 text-purple-500" />
                      Generated Logic (JSON)
                    </h3>
                    <button className="px-2.5 py-1 bg-gray-50 border border-gray-200 text-gray-600 rounded-lg text-[11px] font-semibold hover:bg-gray-100">
                      View JSON
                    </button>
                  </div>
                  <div className="p-3 bg-gray-50 flex-1 overflow-y-auto font-mono text-[11px] text-gray-600 leading-relaxed">
                    <pre className="whitespace-pre-wrap">
                      <code>{logicJson}</code>
                    </pre>
                  </div>
                </div>

              </div>
            </div>
          </div>
        );
    }
  };

  return (
    <div className="min-h-screen bg-[#f8fafc] flex flex-col font-sans antialiased text-gray-900">
      <WorkspaceHeader onNavigateHome={() => setActiveTab('dashboard')} setActiveTab={setActiveTab} />
      
      <div className="flex flex-1 relative">
        <Sidebar activeTab={activeTab} setActiveTab={setActiveTab} />
        <main className="flex-1 overflow-y-auto pb-12">
          {renderTabContent()}
        </main>
      </div>

      {/* Save Project Modal */}
      {saveModalOpen && (
        <div className="fixed inset-0 z-50 bg-black/40 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl border border-gray-200 shadow-2xl max-w-md w-full p-6 space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="font-bold text-gray-800 text-lg flex items-center gap-2">
                <Save className="w-5 h-5 text-indigo-600" /> Save Project
              </h3>
              <button onClick={() => setSaveModalOpen(false)} className="text-gray-400 hover:text-gray-600">
                <X size={20} />
              </button>
            </div>

            {saveMessage && (
              <div className={`p-3 rounded-xl text-xs font-semibold ${saveMessage.includes('successfully') ? 'bg-green-50 text-green-700' : 'bg-red-50 text-red-700'}`}>
                {saveMessage}
              </div>
            )}

            <div>
              <label className="block text-xs font-bold text-gray-700 mb-1.5">Project Title</label>
              <input
                type="text"
                value={projectName}
                onChange={(e) => setProjectName(e.target.value)}
                placeholder="My Flowchart Project"
                className="w-full bg-gray-50 border border-gray-200 rounded-xl p-2.5 text-sm text-gray-800 focus:outline-none focus:border-indigo-500 focus:bg-white"
              />
            </div>

            <div className="flex justify-end gap-2 pt-2">
              <button
                onClick={() => setSaveModalOpen(false)}
                className="px-4 py-2 bg-gray-100 text-gray-700 rounded-xl text-xs font-semibold hover:bg-gray-200"
              >
                Cancel
              </button>
              <button
                onClick={handleSaveProject}
                disabled={savingProject || !projectName.trim()}
                className="px-5 py-2 bg-indigo-600 text-white rounded-xl text-xs font-semibold hover:bg-indigo-700 disabled:opacity-50 shadow-sm"
              >
                {savingProject ? 'Saving...' : 'Save to Database'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
