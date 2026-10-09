import React, { useState, useCallback, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import ReactFlow, {
  Background,
  MiniMap,
  ReactFlowProvider,
  addEdge,
  applyNodeChanges,
  applyEdgeChanges,
  useReactFlow,
  MarkerType,
} from 'reactflow';
import type { Node, Edge, Connection, NodeChange, EdgeChange } from 'reactflow';
import 'reactflow/dist/style.css';
import { toPng } from 'html-to-image';
import { nodeTypes } from '../flowchart/FlowNodes';
import { SYMBOLS } from '../flowchart/symbols';
import { apiJson, graphPayload } from '../flowchart/api';

const edgeLook = (label?: string) => {
  const color = label === 'Yes' ? '#34d399' : label === 'No' ? '#f87171' : '#94a3b8';
  return {
    type: 'smoothstep' as const,
    animated: true,
    markerEnd: { type: MarkerType.ArrowClosed, color },
    style: { stroke: color, strokeWidth: 2 },
    labelStyle: label ? { fill: color, fontWeight: 700, fontSize: 11 } : undefined,
    labelBgStyle: label ? { fill: '#030817', fillOpacity: 0.8 } : undefined,
  };
};

const mkEdge = (source: string, target: string, label?: string, sourceHandle?: string | null): Edge => ({
  id: `e_${source}_${target}_${sourceHandle || ''}_${Date.now()}`,
  source,
  target,
  sourceHandle: sourceHandle || undefined,
  label: label || '',
  ...edgeLook(label),
});

const nextNodeId = (nodes: Node[]) => {
  let max = 100;
  for (const n of nodes) {
    const m = String(n.id).match(/(\d+)$/);
    if (m) max = Math.max(max, parseInt(m[1], 10));
  }
  return `node_${max + 1}`;
};

const WorkspaceCanvas = ({
  nodes, edges, onNodesChange, onEdgesChange, onConnect, onReconnect,
  onDrop, onDragOver, setInstance, errorNodeIds, onNodeDragStop,
}: any) => {
  const { fitView } = useReactFlow();
  const styledNodes = nodes.map((n: Node) => ({
    ...n,
    data: { ...n.data, hasError: errorNodeIds?.includes(n.id) },
  }));
  return (
    <ReactFlow
      nodes={styledNodes}
      edges={edges}
      onNodesChange={onNodesChange}
      onEdgesChange={onEdgesChange}
      onConnect={onConnect}
      onReconnect={onReconnect}
      onNodeDragStop={onNodeDragStop}
      onInit={inst => { setInstance(inst); setTimeout(() => fitView({ padding: 0.15, duration: 300 }), 80); }}
      onDrop={onDrop}
      onDragOver={onDragOver}
      nodeTypes={nodeTypes}
      defaultEdgeOptions={{ type: 'smoothstep', animated: true, markerEnd: { type: MarkerType.ArrowClosed, color: '#94a3b8' }, style: { stroke: '#94a3b8', strokeWidth: 2 } }}
      fitView
      className="bg-transparent"
      deleteKeyCode={['Backspace', 'Delete']}
      multiSelectionKeyCode="Shift"
    >
      <Background color="#1e293b" gap={24} size={1.5} />
      <MiniMap style={{ background: '#0f172a', border: '1px solid #334155', borderRadius: 8 }}
        nodeColor={(n) => n.type === 'start_end' ? '#34d399' : n.type === 'decision' ? '#fbbf24' : n.type === 'input_output' ? '#c084fc' : '#60a5fa'} />
    </ReactFlow>
  );
};

const SyntaxLine = ({ line, num }: { line: string; num: number }) => {
  let cls = 'text-slate-300';
  if (line.trimStart().startsWith('#')) cls = 'text-slate-500 italic';
  else if (/\b(if|else|elif|while|for|in|not|and|or|return|def|class|import|from|break|continue|pass)\b/.test(line)) cls = 'text-pink-400';
  else if (/\binput\s*\(/.test(line)) cls = 'text-cyan-300';
  else if (/\bprint\s*\(/.test(line)) cls = 'text-green-300';
  return (
    <div className="flex hover:bg-white/5 rounded px-1">
      <span className="w-8 shrink-0 text-right text-slate-600 select-none mr-3 font-mono">{num}</span>
      <span className={`font-mono text-xs leading-relaxed ${cls}`}>{line || ' '}</span>
    </div>
  );
};

export const WorkspacePage: React.FC = () => {
  const navigate = useNavigate();
  const [nodes, setNodes] = useState<Node[]>([]);
  const [edges, setEdges] = useState<Edge[]>([]);
  const [rfInstance, setRfInstance] = useState<any>(null);
  const [history, setHistory] = useState<{ nodes: Node[]; edges: Edge[] }[]>([]);
  const [redoStack, setRedoStack] = useState<{ nodes: Node[]; edges: Edge[] }[]>([]);
  const [mode, setMode] = useState<'draw' | 'upload' | 'ai'>('draw');
  const [generatedCode, setGeneratedCode] = useState('');
  const [codeWarnings, setCodeWarnings] = useState<string[]>([]);
  const [loadingCode, setLoadingCode] = useState(false);
  const [copied, setCopied] = useState(false);
  const [userInput, setUserInput] = useState('');
  const [execStatus, setExecStatus] = useState<'idle' | 'success' | 'error'>('idle');
  const [execProgramOutput, setExecProgramOutput] = useState('');
  const [execErrorDetails, setExecErrorDetails] = useState('');
  const [loadingRun, setLoadingRun] = useState(false);
  const [debugIssues, setDebugIssues] = useState<any[]>([]);
  const [debugSummary, setDebugSummary] = useState('');
  const [loadingDebug, setLoadingDebug] = useState(false);
  const [errorNodeIds, setErrorNodeIds] = useState<string[]>([]);
  const [chatOpen, setChatOpen] = useState(true);
  const [chatMessages, setChatMessages] = useState<{ role: 'user' | 'aria'; text: string; patch?: any }[]>([
    { role: 'aria', text: 'Hi! Describe what you want to build.' },
  ]);
  const [chatInput, setChatInput] = useState('');
  const [loadingChat, setLoadingChat] = useState(false);
  const chatEndRef = useRef<HTMLDivElement>(null);
  const [uploadFile, setUploadFile] = useState<File | null>(null);
  const [uploadPreview, setUploadPreview] = useState<string | null>(null);
  const [loadingUpload, setLoadingUpload] = useState(false);
  const [uploadOverlay, setUploadOverlay] = useState<string | null>(null);
  const [uploadError, setUploadError] = useState('');
  const [aiPrompt, setAiPrompt] = useState('');
  const [loadingAiFlow, setLoadingAiFlow] = useState(false);
  const [aiError, setAiError] = useState('');
  const [symbolsOpen, setSymbolsOpen] = useState(() => typeof window !== 'undefined' && window.innerWidth >= 1024);
  const [rightOpen, setRightOpen] = useState(() => typeof window !== 'undefined' && window.innerWidth >= 1024);
  const [codeOpen, setCodeOpen] = useState(true);
  const [runOpen, setRunOpen] = useState(true);
  const [aiBanner, setAiBanner] = useState('');
  const [zoomPct, setZoomPct] = useState(100);
  const canvasWrapRef = useRef<HTMLDivElement>(null);
  const outputEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    fetch('/api/health').then(r => r.json()).then(d => {
      if (!d.ai_available) setAiBanner('AI generation is currently unavailable. Please configure the backend API key.');
    }).catch(() => {
      setAiBanner('Cannot reach the FlowForge API. Start the FastAPI backend on port 8000.');
    });
  }, []);

  const addLabelChange = useCallback((nid: string, newLabel: string) => {
    setNodes(prev => prev.map(n => n.id === nid ? { ...n, data: { ...n.data, label: newLabel } } : n));
  }, []);

  const snapshot = useCallback(() => {
    setHistory(h => [...h.slice(-40), { nodes, edges }]);
    setRedoStack([]);
  }, [nodes, edges]);

  const onNodesChange = useCallback((changes: NodeChange[]) => {
    if (changes.some(c => c.type === 'remove')) snapshot();
    setNodes(n => applyNodeChanges(changes, n));
  }, [snapshot]);
  const onEdgesChange = useCallback((changes: EdgeChange[]) => {
    if (changes.some(c => c.type === 'remove')) snapshot();
    setEdges(e => applyEdgeChanges(changes, e));
  }, [snapshot]);

  const onConnect = useCallback((params: Connection) => {
    snapshot();
    const handle = (params.sourceHandle || '').toLowerCase();
    const label = handle === 'yes' || handle === 'left' ? 'Yes' : handle === 'no' || handle === 'right' ? 'No' : '';
    setEdges(eds => addEdge(mkEdge(params.source!, params.target!, label, params.sourceHandle), eds));
  }, [snapshot]);

  const onReconnect = useCallback((oldEdge: Edge, params: Connection) => {
    snapshot();
    const handle = (params.sourceHandle || oldEdge.sourceHandle || '').toLowerCase();
    const label = handle === 'yes' || handle === 'left' ? 'Yes' : handle === 'no' || handle === 'right' ? 'No' : String(oldEdge.label || '');
    setEdges(eds => eds.map(e => e.id === oldEdge.id
      ? { ...mkEdge(params.source!, params.target!, label, params.sourceHandle || oldEdge.sourceHandle), id: oldEdge.id }
      : e));
  }, [snapshot]);

  const setEdgeBranch = (edgeId: string, label: string) => {
    snapshot();
    const handle = label === 'Yes' ? 'yes' : label === 'No' ? 'no' : undefined;
    setEdges(eds => eds.map(e => e.id === edgeId ? { ...e, label, sourceHandle: handle, ...edgeLook(label) } : e));
  };

  const onDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.dataTransfer.dropEffect = 'move';
  }, []);

  const defaultLabelFor = (type: string) => {
    if (type === 'start_end') {
      const hasStart = nodes.some(n => n.type === 'start_end' && String(n.data?.label || '').toLowerCase().includes('start'));
      return hasStart ? 'End' : 'Start';
    }
    return SYMBOLS.find(s => s.type === type)?.defaultLabel || type;
  };

  const addNode = (type: string, position?: { x: number; y: number }) => {
    snapshot();
    const newNode: Node = {
      id: nextNodeId(nodes),
      type,
      position: position || { x: 220 + Math.random() * 160, y: 80 + nodes.length * 70 },
      data: { label: defaultLabelFor(type), onLabelChange: addLabelChange },
    };
    setNodes(ns => [...ns, newNode]);
  };

  const onDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    const type = e.dataTransfer.getData('application/reactflow');
    if (!type || !rfInstance) return;
    const pos = rfInstance.screenToFlowPosition({ x: e.clientX, y: e.clientY });
    addNode(type, pos);
  }, [rfInstance, nodes, snapshot, addLabelChange]);

  const handleUndo = () => {
    if (!history.length) return;
    const prev = history[history.length - 1];
    setRedoStack(r => [...r, { nodes, edges }]);
    setNodes(prev.nodes); setEdges(prev.edges);
    setHistory(h => h.slice(0, -1));
  };
  const handleRedo = () => {
    if (!redoStack.length) return;
    const next = redoStack[redoStack.length - 1];
    setHistory(h => [...h, { nodes, edges }]);
    setNodes(next.nodes); setEdges(next.edges);
    setRedoStack(r => r.slice(0, -1));
  };
  const handleClear = () => {
    snapshot();
    setNodes([]); setEdges([]);
    setGeneratedCode(''); setExecStatus('idle'); setExecProgramOutput(''); setExecErrorDetails(''); setDebugIssues([]); setDebugSummary(''); setErrorNodeIds([]);
  };
  const handleDeleteSelected = () => {
    snapshot();
    const ids = new Set(nodes.filter(n => n.selected).map(n => n.id));
    const eids = new Set(edges.filter(e => e.selected).map(e => e.id));
    setNodes(ns => ns.filter(n => !ids.has(n.id)));
    setEdges(es => es.filter(e => !eids.has(e.id) && !ids.has(e.source) && !ids.has(e.target)));
  };
  const handleDuplicate = () => {
    const selected = nodes.filter(n => n.selected);
    if (!selected.length) return;
    snapshot();
    const idMap: Record<string, string> = {};
    let working = [...nodes];
    const copies: Node[] = selected.map(n => {
      const id = nextNodeId(working);
      working = [...working, { ...n, id }];
      idMap[n.id] = id;
      return { ...n, id, selected: true, position: { x: n.position.x + 40, y: n.position.y + 40 }, data: { ...n.data, onLabelChange: addLabelChange } };
    });
    setNodes(ns => [...ns.map(n => ({ ...n, selected: false })), ...copies]);
    const newEdges = edges.filter(e => idMap[e.source] && idMap[e.target]).map(e => ({
      ...e, id: `e_${idMap[e.source]}_${idMap[e.target]}_${e.sourceHandle || ''}`, source: idMap[e.source], target: idMap[e.target],
    }));
    if (newEdges.length) setEdges(es => es.concat(newEdges));
  };

  const loadFlowchart = useCallback((newNodes: Node[], newEdges: Edge[]) => {
    snapshot();
    const enriched = newNodes.map(n => ({ ...n, data: { ...(n.data || {}), onLabelChange: addLabelChange } }));
    const enrichedEdges = newEdges.map(e => {
      const lbl = String(e.label || '');
      return { ...e, ...edgeLook(lbl), label: lbl };
    });
    setNodes(enriched);
    setEdges(enrichedEdges);
    setGeneratedCode('');
    setExecStatus('idle');
    setExecProgramOutput('');
    setExecErrorDetails('');
    setDebugIssues([]);
    setDebugSummary('');
    setErrorNodeIds([]);
    setTimeout(() => rfInstance?.fitView({ padding: 0.12, duration: 400 }), 160);
  }, [addLabelChange, snapshot, rfInstance]);

  const applyPatch = (patch: any) => {
    if (!patch) return;
    if (patch.action === 'replace' && patch.nodes) {
      loadFlowchart(patch.nodes, patch.edges || []);
    } else if ((patch.action === 'add_nodes' || patch.action === 'add') && (patch.new_nodes || patch.nodes)) {
      snapshot();
      const extra = (patch.new_nodes || patch.nodes || []).map((n: Node) => ({ ...n, data: { ...n.data, onLabelChange: addLabelChange } }));
      setNodes(prev => [...prev, ...extra]);
      if (patch.new_edges || patch.edges) setEdges(prev => [...prev, ...(patch.new_edges || patch.edges)]);
    } else if (patch.action === 'update_node' && patch.node_id) {
      snapshot();
      setNodes(prev => prev.map(n => n.id === patch.node_id ? { ...n, data: { ...n.data, ...patch.data } } : n));
    }
  };

  const handleFileChange = (f: File | null) => {
    setUploadFile(f);
    setUploadError('');
    setUploadOverlay(null);
    if (f) setUploadPreview(URL.createObjectURL(f));
  };

  const handleAnalyzeImage = async (useSample = false) => {
    setLoadingUpload(true);
    setUploadError('');
    try {
      const fd = new FormData();
      fd.append('mode', useSample ? 'sample' : 'upload');
      if (!useSample && uploadFile) fd.append('file', uploadFile);
      const res = await fetch('/api/analyze', { method: 'POST', body: fd });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(typeof data.detail === 'string' ? data.detail : 'Analysis failed');
      setUploadOverlay(data.overlay_image || null);
      if (data.nodes?.length) {
        loadFlowchart(data.nodes, data.edges || []);
        setMode('draw');
        addAria(`Detected ${data.nodes.length} flowchart symbols and loaded them onto the canvas.${data.warning ? ' ' + data.warning : ''} You can edit labels, then generate Python.`);
      } else {
        setUploadError('No flowchart symbols detected. Try a clearer PNG/JPG with distinct shapes.');
      }
    } catch (e: any) {
      setUploadError(e.message || 'Image analysis failed.');
    }
    setLoadingUpload(false);
  };

  const handleGenerateFlowchart = async (promptText?: string) => {
    const prompt = (promptText || aiPrompt).trim();
    if (!prompt) return;
    setLoadingAiFlow(true);
    setAiError('');
    try {
      const data = await apiJson('/api/generate-flowchart', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ prompt }),
      });
      loadFlowchart(data.nodes, data.edges);
      setMode('draw');
      addAria(`Generated a flowchart for "${prompt}" with ${data.nodes.length} nodes. Edit it, then generate Python from the graph.`);
      setAiPrompt('');
    } catch (e: any) {
      setAiError(e.message || 'Failed to generate flowchart');
    }
    setLoadingAiFlow(false);
  };

  const handleGenerateCode = async () => {
    if (!nodes.length) {
      setCodeWarnings(['Canvas is empty. Create a flowchart first.']);
      return;
    }
    setLoadingCode(true);
    try {
      const data = await apiJson('/api/generate-code', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(graphPayload(nodes, edges)),
      });
      setGeneratedCode(data.code || '');
      setCodeWarnings(data.warnings || []);
    } catch (e: any) {
      setCodeWarnings([e.message]);
    }
    setLoadingCode(false);
  };

  const handleCopyCode = async () => {
    if (!generatedCode) return;
    try {
      await navigator.clipboard.writeText(generatedCode);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      const ta = document.createElement('textarea');
      ta.value = generatedCode;
      document.body.appendChild(ta);
      ta.select();
      document.execCommand('copy');
      document.body.removeChild(ta);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const handleDownloadCode = () => {
    if (!generatedCode) return;
    const blob = new Blob([generatedCode], { type: 'text/plain' });
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = 'flowforge_generated.py';
    document.body.appendChild(a);
    a.click();
    a.remove();
  };

  const handleExportImage = async () => {
    const el = canvasWrapRef.current?.querySelector('.react-flow__viewport') as HTMLElement | null;
    if (!el) return;
    try {
      const url = await toPng(el, { backgroundColor: '#030817', cacheBust: true });
      const a = document.createElement('a');
      a.href = url;
      a.download = 'flowforge_flowchart.png';
      a.click();
    } catch (e: any) {
      addAria(`Could not export image: ${e.message}`);
    }
  };

  const handleRunCode = async () => {
    if (!generatedCode) return;
    setLoadingRun(true);
    setRunOpen(true);
    setExecStatus('idle');
    setExecProgramOutput('');
    setExecErrorDetails('');
    setTimeout(() => outputEndRef.current?.scrollIntoView({ behavior: 'smooth' }), 50);
    try {
      const data = await apiJson('/api/execute', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ code: generatedCode, user_input: userInput }),
      });
      const status = data.status === 'error' ? 'error' : data.success ? 'success' : 'idle';
      const programOutput = typeof data.program_output === 'string' ? data.program_output : (typeof data.output === 'string' ? data.output : '');
      const errorDetails = typeof data.error_details === 'string' ? data.error_details : '';
      setExecStatus(status);
      setExecProgramOutput(programOutput);
      setExecErrorDetails(errorDetails);
      setTimeout(() => outputEndRef.current?.scrollIntoView({ behavior: 'smooth' }), 80);
    } catch (e: any) {
      setExecStatus('error');
      setExecProgramOutput('');
      setExecErrorDetails(e.message || 'Execution error');
      setTimeout(() => outputEndRef.current?.scrollIntoView({ behavior: 'smooth' }), 80);
    }
    setLoadingRun(false);
  };

  const handleDebug = async () => {
    setLoadingDebug(true);
    setDebugIssues([]);
    setErrorNodeIds([]);
    try {
      const data = await apiJson('/api/debug', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(graphPayload(nodes, edges)),
      });
      setDebugIssues(data.issues || []);
      setDebugSummary(data.summary || '');
      const errIds = (data.issues || []).filter((i: any) => i.node_id).map((i: any) => String(i.node_id));
      setErrorNodeIds(errIds);
      if (data.issues?.length) {
        addAria(`Debugger found ${data.issues.length} issue(s):\n\n${data.issues.map((i: any) => `• ${i.message}`).join('\n')}\n\nAffected nodes are highlighted on the canvas.`);
      } else {
        addAria('✓ Flowchart valid. You can generate Python code.');
      }
    } catch (e: any) {
      setDebugSummary(`Debug failed: ${e.message}`);
    }
    setLoadingDebug(false);
  };

  const handleAutoFix = async () => {
    setLoadingDebug(true);
    try {
      const data = await apiJson('/api/debug/fix', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ...graphPayload(nodes, edges), issues: debugIssues }),
      });
      loadFlowchart(data.nodes, data.edges);
      setDebugIssues([]); setDebugSummary(''); setErrorNodeIds([]);
      addAria('Applied automatic fixes. Run Check Flowchart again to confirm.');
    } catch (e: any) {
      addAria(`Auto-fix failed: ${e.message}`);
    }
    setLoadingDebug(false);
  };

  const addAria = (text: string, patch?: any) => {
    setChatMessages(m => [...m, { role: 'aria', text, patch }]);
    setTimeout(() => chatEndRef.current?.scrollIntoView({ behavior: 'smooth' }), 80);
  };

  const handleSendChat = async (msg?: string) => {
    const text = (msg || chatInput).trim();
    if (!text) return;
    setChatInput('');
    setChatMessages(m => [...m, { role: 'user', text }]);
    setLoadingChat(true);
    try {
      const data = await apiJson('/api/chat', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: text, ...graphPayload(nodes, edges) }),
      });
      addAria(data.reply || '(No reply)', data.patch);
      if (data.patch) applyPatch(data.patch);
      if (data.trigger === 'fix_flowchart') await handleAutoFix();
      if (data.trigger === 'generate_code' || data.code) {
        if (data.code) {
          setGeneratedCode(data.code);
          setCodeWarnings(data.warnings || []);
        } else {
          await handleGenerateCode();
        }
      }
    } catch (e: any) {
      addAria(e.message || 'Chat failed.');
    }
    setLoadingChat(false);
  };

  const handleSave = () => {
    localStorage.setItem('flowforge_project', JSON.stringify({
      nodes: graphPayload(nodes, edges).nodes,
      edges: graphPayload(nodes, edges).edges,
      generatedCode,
      savedAt: new Date().toISOString(),
    }));
    addAria('Project saved in this browser (local storage).');
  };
  const handleLoad = () => {
    try {
      const raw = localStorage.getItem('flowforge_project');
      if (!raw) { addAria('No saved project found.'); return; }
      const proj = JSON.parse(raw);
      loadFlowchart(proj.nodes || [], proj.edges || []);
      if (proj.generatedCode) setGeneratedCode(proj.generatedCode);
      addAria('Project loaded.');
    } catch {
      addAria('Failed to load the saved project.');
    }
  };
  const handleExportJSON = () => {
    const blob = new Blob([JSON.stringify({ ...graphPayload(nodes, edges), generatedCode }, null, 2)], { type: 'application/json' });
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = 'flowforge_export.json';
    a.click();
  };

  const setZoom = (pct: number) => {
    const z = Math.max(0.2, Math.min(2.5, pct / 100));
    setZoomPct(Math.round(z * 100));
    rfInstance?.zoomTo?.(z);
  };

  const selectedNode = nodes.find(n => n.selected);
  const selectedEdge = edges.find(e => e.selected);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [chatMessages]);

  useEffect(() => {
    setNodes(prev => {
      let changed = false;
      const next = prev.map(n => {
        if (n.data?.onLabelChange === addLabelChange) return n;
        changed = true;
        return { ...n, data: { ...n.data, onLabelChange: addLabelChange } };
      });
      return changed ? next : prev;
    });
  }, [nodes, addLabelChange]);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const t = e.target as HTMLElement | null;
      const typing = t && (t.tagName === 'INPUT' || t.tagName === 'TEXTAREA' || t.isContentEditable);
      if (typing) return;
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'z') {
        e.preventDefault();
        if (e.shiftKey) handleRedo();
        else handleUndo();
      } else if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'y') {
        e.preventDefault();
        handleRedo();
      }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  });

  const toolBtn = 'px-2 py-1.5 rounded-lg text-[11px] font-semibold text-slate-300 hover:text-white hover:bg-slate-800 disabled:opacity-30 transition-all border border-transparent hover:border-slate-700';

  return (
    <div className="h-[100dvh] flex flex-col font-sans antialiased overflow-hidden" style={{ background: '#030817', color: '#fff' }}>
      <header className="h-14 flex items-center justify-between px-3 sm:px-6 border-b border-white/10 bg-slate-950/80 backdrop-blur-md sticky top-0 z-50 shrink-0">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-cyan-500 to-violet-600 flex items-center justify-center shadow-[0_0_14px_rgba(6,182,212,0.5)]">
            <svg className="w-4 h-4 text-white" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5"><ellipse cx="12" cy="5" rx="5" ry="3"/><rect x="7" y="11" width="10" height="4" rx="1"/><polygon points="12,18 7,22 17,22"/><path d="M12 8v3M12 15v3"/></svg>
          </div>
          <span className="font-bold text-white text-sm hidden sm:block">FlowForge <span className="text-cyan-400">AI</span></span>
        </div>
        <nav className="hidden md:flex items-center gap-5 text-xs font-medium text-slate-400">
          <button onClick={() => navigate('/')} className="hover:text-cyan-400">Home</button>
          <button onClick={() => navigate('/#features')} className="hover:text-cyan-400">Features</button>
          <button onClick={() => navigate('/#how-it-works')} className="hover:text-cyan-400">How It Works</button>
          <button onClick={() => navigate('/#about')} className="hover:text-cyan-400">About</button>
        </nav>
        <div className="flex items-center gap-1.5 flex-wrap justify-end">
          <button onClick={() => { setSymbolsOpen(s => !s); }} className="lg:hidden px-2 py-1.5 text-[11px] font-semibold bg-slate-800 border border-slate-700 rounded-lg">Symbols</button>
          <button onClick={() => setRightOpen(s => !s)} className="lg:hidden px-2 py-1.5 text-[11px] font-semibold bg-slate-800 border border-slate-700 rounded-lg">ARIA / Code</button>
          <button onClick={handleSave} className="px-2.5 py-1.5 text-[11px] font-semibold bg-slate-800 border border-slate-700 hover:border-cyan-500 rounded-lg">Save</button>
          <button onClick={handleLoad} className="px-2.5 py-1.5 text-[11px] font-semibold bg-slate-800 border border-slate-700 hover:border-cyan-500 rounded-lg">Load</button>
          <button onClick={handleExportImage} className="hidden sm:inline-flex px-2.5 py-1.5 text-[11px] font-semibold bg-slate-800 border border-slate-700 hover:border-cyan-500 rounded-lg">Export Image</button>
          <button onClick={handleExportJSON} className="hidden sm:inline-flex px-2.5 py-1.5 text-[11px] font-semibold bg-slate-800 border border-slate-700 hover:border-cyan-500 rounded-lg">Export JSON</button>
          <button onClick={() => navigate('/')} className="px-2.5 py-1.5 text-[11px] font-bold bg-white/10 border border-white/20 rounded-lg">← Home</button>
        </div>
      </header>

      {aiBanner && (
        <div className="px-4 py-2 text-xs bg-amber-950/80 border-b border-amber-700/50 text-amber-200">{aiBanner} Manual drawing, debugger structure checks, and code execution still work.</div>
      )}

      <div className="flex flex-1 overflow-hidden relative">
        {(symbolsOpen || rightOpen) && (
          <button type="button" aria-label="Close panels" onClick={() => { setSymbolsOpen(false); setRightOpen(false); }}
            className="lg:hidden absolute inset-0 z-20 bg-black/50" />
        )}
        <aside className={`${symbolsOpen ? 'flex' : 'hidden'} lg:flex absolute lg:static z-30 inset-y-0 left-0 w-56 shrink-0 flex-col border-r border-white/10 bg-slate-950/95 lg:bg-slate-950/60 overflow-y-auto`}>
          <div className="p-3 border-b border-white/10 flex items-center justify-between">
            <span className="text-xs font-bold text-cyan-400 uppercase tracking-wider">Flowchart Symbols</span>
            <button onClick={() => setSymbolsOpen(false)} className="text-slate-500 hover:text-white text-xs">✕</button>
          </div>
          <div className="p-3 space-y-1 flex-1">
            <p className="text-[10px] text-slate-500 mb-2">Drag onto the canvas or click + to add</p>
            {SYMBOLS.map(sym => (
              <div key={sym.type} draggable
                onDragStart={e => e.dataTransfer.setData('application/reactflow', sym.type)}
                className="flex items-center gap-2 p-2 rounded-lg border border-transparent hover:border-cyan-500/40 hover:bg-cyan-500/5 cursor-grab active:cursor-grabbing group">
                <div className={`w-9 h-5 shrink-0 ${sym.preview}`} />
                <span className="text-[11px] font-semibold text-slate-400 group-hover:text-cyan-300 leading-tight">{sym.label}</span>
                <button onClick={() => addNode(sym.type)} className="ml-auto text-cyan-400 text-sm shrink-0 px-1" title="Click to add">+</button>
              </div>
            ))}
          </div>
          {selectedNode && (
            <div className="p-3 border-t border-white/10 space-y-2">
              <p className="text-[10px] font-bold text-slate-400 uppercase">Node properties</p>
              <p className="text-[10px] text-slate-500">id: {selectedNode.id} · {selectedNode.type}</p>
              <input
                value={selectedNode.data?.label || ''}
                onChange={e => addLabelChange(selectedNode.id, e.target.value)}
                className="w-full bg-slate-900 border border-slate-700 text-xs rounded px-2 py-1.5 outline-none focus:border-cyan-500"
              />
            </div>
          )}
          {selectedEdge && (
            <div className="p-3 border-t border-white/10 space-y-2">
              <p className="text-[10px] font-bold text-slate-400 uppercase">Connection</p>
              <p className="text-[10px] text-slate-500">{selectedEdge.source} → {selectedEdge.target}</p>
              <div className="flex gap-1">
                {['Yes', 'No', ''].map(lab => (
                  <button key={lab || 'none'} onClick={() => setEdgeBranch(selectedEdge.id, lab)}
                    className={`flex-1 py-1 rounded text-[10px] font-bold border ${String(selectedEdge.label) === lab ? 'border-cyan-400 text-cyan-300' : 'border-slate-700 text-slate-400'}`}>
                    {lab || 'None'}
                  </button>
                ))}
              </div>
            </div>
          )}
          <div className="p-3 border-t border-white/10 space-y-2">
            <button onClick={handleDebug} disabled={loadingDebug}
              className="w-full py-2 rounded-lg text-xs font-bold bg-gradient-to-r from-violet-600 to-purple-700 text-white disabled:opacity-50 shadow-[0_0_12px_rgba(139,92,246,0.4)]">
              {loadingDebug ? 'Checking…' : 'CHECK FLOWCHART'}
            </button>
            {debugSummary && <p className={`text-[10px] font-semibold text-center ${debugIssues.length ? 'text-red-400' : 'text-green-400'}`}>{debugSummary}</p>}
            {debugIssues.length > 0 && (
              <>
                <div className="space-y-1 max-h-32 overflow-y-auto">
                  {debugIssues.map((issue, i) => (
                    <div key={i} className={`text-[10px] rounded p-1.5 ${issue.type === 'error' ? 'bg-red-900/40 text-red-300' : 'bg-yellow-900/40 text-yellow-300'}`}>
                      {issue.message}
                    </div>
                  ))}
                </div>
                <button onClick={handleAutoFix} disabled={loadingDebug} className="w-full py-1.5 rounded-lg text-[10px] font-bold bg-cyan-600 hover:bg-cyan-500 disabled:opacity-50">Fix Automatically</button>
              </>
            )}
          </div>
        </aside>

        <div className="flex-1 flex flex-col overflow-hidden min-w-0">
          <div className="flex items-center gap-1 px-2 py-2 border-b border-white/10 bg-slate-950/40 shrink-0 flex-wrap">
            <div className="flex items-center gap-1 rounded-lg bg-slate-900 p-0.5 border border-slate-800 mr-1">
              {([['draw', 'Draw'], ['upload', 'Upload'], ['ai', 'AI Generate']] as const).map(([m, lab]) => (
                <button key={m} onClick={() => setMode(m)}
                  className={`px-2.5 py-1.5 rounded-md text-[11px] font-bold ${mode === m ? 'bg-cyan-600 text-white shadow-[0_0_10px_rgba(6,182,212,0.4)]' : 'text-slate-400 hover:text-white'}`}>{lab}</button>
              ))}
            </div>
            <button onClick={() => addNode('process')} className={toolBtn}>Add</button>
            <button onClick={handleUndo} disabled={!history.length} className={toolBtn}>Undo</button>
            <button onClick={handleRedo} disabled={!redoStack.length} className={toolBtn}>Redo</button>
            <button onClick={handleDuplicate} className={toolBtn}>Duplicate</button>
            <button onClick={handleDeleteSelected} className={toolBtn}>Delete</button>
            <button onClick={handleClear} className={toolBtn}>Clear</button>
            <button onClick={() => setZoom(zoomPct - 10)} className={toolBtn}>Zoom −</button>
            <button onClick={() => setZoom(100)} className={toolBtn}>{zoomPct}%</button>
            <button onClick={() => setZoom(zoomPct + 10)} className={toolBtn}>Zoom +</button>
            <button onClick={() => rfInstance?.fitView({ padding: 0.12, duration: 250 })} className={toolBtn}>Fit</button>
            <div className="flex-1" />
            <button onClick={handleGenerateCode} disabled={loadingCode || !nodes.length}
              className="px-3 py-1.5 rounded-lg text-xs font-bold bg-gradient-to-r from-cyan-600 to-blue-600 disabled:opacity-50 shadow-[0_0_10px_rgba(6,182,212,0.35)]">
              {loadingCode ? 'Generating…' : 'Generate Python Code'}
            </button>
          </div>

          {mode === 'upload' && (
            <div className="flex-1 overflow-y-auto p-4">
              <div className="max-w-xl mx-auto space-y-4">
                <h3 className="text-sm font-bold">Upload Flowchart Image</h3>
                <p className="text-xs text-slate-400">PNG/JPG is sent to FastAPI → OpenCV shape detection → OCR → editable graph on the canvas. The image itself is not the flowchart.</p>
                <div className="border-2 border-dashed border-slate-700 hover:border-cyan-500/50 rounded-xl p-6 flex flex-col items-center gap-3">
                  {uploadPreview ? <img src={uploadPreview} alt="Preview" className="max-h-48 rounded-lg object-contain" /> : <div className="text-slate-500 text-sm">Drop or choose an image</div>}
                  <label className="cursor-pointer px-4 py-2 bg-cyan-600 hover:bg-cyan-500 text-white text-xs font-bold rounded-lg">
                    Select Flowchart Image
                    <input type="file" accept="image/png,image/jpg,image/jpeg" onChange={e => handleFileChange(e.target.files?.[0] || null)} className="hidden" />
                  </label>
                </div>
                <div className="flex gap-2">
                  <button onClick={() => handleAnalyzeImage(false)} disabled={!uploadFile || loadingUpload} className="flex-1 py-2.5 bg-slate-800 border border-cyan-500/40 text-cyan-300 text-xs font-bold rounded-lg disabled:opacity-40">
                    {loadingUpload ? 'Processing CV & OCR…' : 'Analyze Image'}
                  </button>
                  <button onClick={() => handleAnalyzeImage(true)} disabled={loadingUpload} className="px-4 py-2.5 bg-slate-800 border border-slate-700 text-xs font-bold rounded-lg">Try Sample</button>
                </div>
                {uploadError && <p className="text-xs text-red-400 bg-red-900/20 border border-red-800/50 rounded-lg p-3">{uploadError}</p>}
                {uploadOverlay && <img src={`data:image/png;base64,${uploadOverlay}`} alt="Overlay" className="w-full rounded-lg border border-slate-700" />}
              </div>
            </div>
          )}

          {mode === 'ai' && (
            <div className="flex-1 overflow-y-auto p-4">
              <div className="max-w-xl mx-auto space-y-4">
                <h3 className="text-sm font-bold">Describe Your Program</h3>
                <p className="text-xs text-slate-400">AI builds a flowchart first. Python is generated later from that graph — never directly from this prompt.</p>
                <textarea value={aiPrompt} onChange={e => setAiPrompt(e.target.value)}
                  placeholder="What do you want to build?"
                  rows={5}
                  className="w-full bg-slate-900 border border-slate-700 focus:border-cyan-500 text-sm rounded-xl p-3 outline-none resize-none" />
                <div className="flex flex-wrap gap-2">
                  {['Create a calculator', 'Check prime number', 'Find largest of 3 numbers', 'Calculate factorial'].map(s => (
                    <button key={s} onClick={() => setAiPrompt(s)} className="px-3 py-1.5 bg-slate-800 border border-slate-700 text-[11px] rounded-lg hover:border-cyan-500/50">{s}</button>
                  ))}
                </div>
                <button onClick={() => handleGenerateFlowchart()} disabled={!aiPrompt.trim() || loadingAiFlow}
                  className="w-full py-3 bg-gradient-to-r from-violet-600 to-cyan-600 text-sm font-bold rounded-xl disabled:opacity-50 shadow-[0_0_20px_rgba(139,92,246,0.3)]">
                  {loadingAiFlow ? 'Generating Flowchart…' : 'AI CREATE — Generate Flowchart with AI'}
                </button>
                {aiError && <p className="text-xs text-red-400 bg-red-900/20 border border-red-800/50 rounded-lg p-3">{aiError}</p>}
              </div>
            </div>
          )}

          <div ref={canvasWrapRef} className={`flex-1 relative overflow-hidden ${mode !== 'draw' ? 'hidden' : ''}`}>
            <ReactFlowProvider>
              <WorkspaceCanvas
                nodes={nodes} edges={edges}
                onNodesChange={onNodesChange} onEdgesChange={onEdgesChange} onConnect={onConnect}
                onReconnect={onReconnect}
                onDrop={onDrop} onDragOver={onDragOver} setInstance={setRfInstance}
                errorNodeIds={errorNodeIds}
                onNodeDragStop={() => snapshot()}
              />
            </ReactFlowProvider>
            {!nodes.length && (
              <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
                <div className="text-center space-y-1">
                  <p className="text-slate-500 text-sm font-semibold">Canvas is empty</p>
                  <p className="text-slate-600 text-xs">Add symbols, upload an image, or use AI Generate</p>
                </div>
              </div>
            )}
          </div>
        </div>

        <aside className={`${rightOpen ? 'flex' : 'hidden'} lg:flex absolute lg:static z-30 inset-y-0 right-0 w-[min(100%,22rem)] shrink-0 flex-col border-l border-white/10 bg-slate-950/95 lg:bg-slate-950/60 overflow-y-auto`}>
          <div className="flex flex-col border-b border-white/10 shrink-0" style={{ maxHeight: chatOpen ? '300px' : 'auto' }}>
            <div className="p-3 border-b border-white/10 flex items-center justify-between bg-slate-950/40">
              <span className="text-xs font-bold text-violet-400">ARIA — FlowForge AI Assistant</span>
              <div className="flex gap-2">
                <button onClick={() => setRightOpen(false)} className="lg:hidden text-slate-500 text-xs">✕</button>
                <button onClick={() => setChatOpen(!chatOpen)} className="text-slate-500 text-xs">{chatOpen ? '▲' : '▼'}</button>
              </div>
            </div>
            {chatOpen && (
              <>
                <div className="flex-1 overflow-y-auto p-3 space-y-2 max-h-[160px]">
                  {chatMessages.map((m, i) => (
                    <div key={i} className={`text-[11px] rounded-xl px-3 py-2 ${m.role === 'aria' ? 'bg-violet-900/30 border border-violet-700/30' : 'bg-slate-800/80 border border-slate-700/50 ml-4'}`}>
                      {m.role === 'aria' && <span className="text-violet-400 font-bold text-[10px] block mb-0.5">ARIA</span>}
                      <pre className="whitespace-pre-wrap font-sans">{m.text}</pre>
                      {m.patch && <span className="text-[10px] text-cyan-400 mt-1 block">Canvas updated</span>}
                    </div>
                  ))}
                  {loadingChat && <div className="text-violet-300 text-[11px] animate-pulse px-2">Thinking…</div>}
                  <div ref={chatEndRef} />
                </div>
                <div className="px-3 pb-2 flex flex-wrap gap-1">
                  {[
                    { label: 'Generate Flowchart', msg: 'Create a flowchart to check whether a number is even or odd' },
                    { label: 'Explain Flowchart', msg: 'Explain this flowchart in simple terms' },
                    { label: 'Fix Flowchart', msg: 'Why is this flowchart incorrect? Fix it.' },
                    { label: 'Generate Code', msg: 'Generate Python code from this flowchart' },
                  ].map(a => (
                    <button key={a.label} onClick={() => handleSendChat(a.msg)} disabled={loadingChat}
                      className="px-2 py-1 rounded-lg text-[10px] font-semibold bg-slate-800 border border-slate-700 hover:border-violet-500/50 disabled:opacity-40">{a.label}</button>
                  ))}
                </div>
                <div className="px-3 pb-2 flex flex-wrap gap-1">
                  {['Create a calculator', 'Check prime number', 'Find largest of 3 numbers', 'Calculate factorial'].map(s => (
                    <button key={s} onClick={() => handleSendChat(`Create a flowchart to ${s.toLowerCase()}`)} className="px-2 py-1 rounded-lg text-[10px] bg-slate-900 border border-slate-800 text-slate-400 hover:text-cyan-300">{s}</button>
                  ))}
                </div>
                <div className="px-3 pb-3 flex gap-2">
                  <input value={chatInput} onChange={e => setChatInput(e.target.value)}
                    onKeyDown={e => e.key === 'Enter' && !e.shiftKey && handleSendChat()}
                    placeholder="Ask ARIA anything…" disabled={loadingChat}
                    className="flex-1 bg-slate-900 border border-slate-700 focus:border-violet-500 text-[11px] rounded-lg px-3 py-2 outline-none" />
                  <button onClick={() => handleSendChat()} disabled={!chatInput.trim() || loadingChat} className="px-3 py-2 bg-violet-600 rounded-lg text-xs font-bold disabled:opacity-40">Send</button>
                </div>
              </>
            )}
          </div>

          <div className="flex flex-col border-b border-white/10 shrink-0" style={{ minHeight: codeOpen ? '180px' : 'auto', maxHeight: codeOpen ? '280px' : 'auto' }}>
            <div className="p-3 border-b border-white/10 flex items-center justify-between bg-slate-950/40">
              <span className="text-xs font-bold text-cyan-400">Generated Python Code</span>
              <div className="flex items-center gap-1">
                <button onClick={handleGenerateCode} disabled={loadingCode} className="px-2 py-1 rounded-md text-[10px] font-semibold bg-cyan-900/40 border border-cyan-700">Generate</button>
                <button onClick={handleCopyCode} disabled={!generatedCode} className="px-2 py-1 rounded-md text-[10px] font-semibold bg-slate-800 border border-slate-700 disabled:opacity-40">{copied ? 'Copied!' : 'Copy'}</button>
                <button onClick={handleDownloadCode} disabled={!generatedCode} className="px-2 py-1 rounded-md text-[10px] font-semibold bg-slate-800 border border-slate-700 disabled:opacity-40">Download</button>
                <button onClick={handleGenerateCode} disabled={loadingCode || !generatedCode} className="px-2 py-1 rounded-md text-[10px] font-semibold bg-slate-800 border border-slate-700 disabled:opacity-40">Regenerate</button>
                <button onClick={() => setCodeOpen(!codeOpen)} className="text-slate-500 text-xs ml-1">{codeOpen ? '▲' : '▼'}</button>
              </div>
            </div>
            {codeOpen && (
              <div className="flex-1 overflow-y-auto" style={{ background: '#0d1117' }}>
                {!generatedCode ? (
                  <div className="flex flex-col items-center justify-center h-full gap-2 p-4 text-center">
                    <p className="text-slate-500 text-xs">No code yet. Build a flowchart, then Generate.</p>
                  </div>
                ) : (
                  <div className="p-2">
                    {codeWarnings.map((w, i) => <div key={i} className="text-[10px] bg-yellow-900/30 border border-yellow-700/40 text-yellow-300 rounded px-2 py-1 mb-2">{w}</div>)}
                    {generatedCode.split('\n').map((line, i) => <SyntaxLine key={i} line={line} num={i + 1} />)}
                  </div>
                )}
              </div>
            )}
          </div>

          <div className="flex flex-col shrink-0 bg-slate-950/80">
            <div className="p-3 border-b border-white/10 flex items-center justify-between bg-slate-950/40">
              <span className="text-xs font-bold text-green-400">Run & Output</span>
              <button onClick={() => setRunOpen(!runOpen)} className="text-slate-500 text-xs">{runOpen ? '▲' : '▼'}</button>
            </div>
            {runOpen && (
              <div className="p-3 space-y-3">
                <div className="flex flex-col gap-1.5">
                  <label className="text-[10px] font-semibold text-slate-400">Program Input (one value per line)</label>
                  <div className="flex flex-col sm:flex-row gap-2 items-stretch sm:items-start">
                    <textarea
                      value={userInput}
                      onChange={e => setUserInput(e.target.value)}
                      placeholder={'Enter each value on a new line\n5\n10\n12'}
                      rows={3}
                      className="flex-1 bg-slate-900 border border-slate-700 focus:border-green-500 text-xs rounded-lg p-2 outline-none font-mono resize-y min-h-[72px]"
                    />
                    <button
                      onClick={handleRunCode}
                      disabled={!generatedCode || loadingRun}
                      className="px-3 py-3 bg-green-700 hover:bg-green-600 text-xs font-bold rounded-lg disabled:opacity-40 shrink-0 self-stretch sm:self-auto flex items-center justify-center shadow-[0_0_10px_rgba(34,197,94,0.3)]"
                    >
                      {loadingRun ? 'Running…' : 'Run Code'}
                    </button>
                  </div>
                </div>

                <div className="space-y-2">
                  <div className="flex items-center justify-between gap-2">
                    <span className="text-[10px] font-semibold text-slate-400">Status:</span>
                    <span className={`text-[10px] font-bold ${execStatus === 'success' ? 'text-green-400' : execStatus === 'error' ? 'text-red-400' : 'text-slate-500'}`}>
                      {execStatus === 'success' ? 'Success' : execStatus === 'error' ? 'Error' : 'Idle'}
                    </span>
                  </div>

                  <div className="space-y-1">
                    <span className="text-[10px] font-semibold text-slate-400">Program Output:</span>
                    <div className="bg-slate-950 border border-slate-800 rounded-lg p-3 min-h-[60px] font-mono text-xs text-green-300 whitespace-pre-wrap max-h-48 overflow-y-auto">
                      {execStatus === 'idle' ? <span className="text-slate-600">Output will appear here…</span> : execProgramOutput || <span className="text-slate-500">No program output.</span>}
                    </div>
                  </div>

                  {execErrorDetails && (
                    <div className="space-y-1">
                      <span className="text-[10px] font-semibold text-slate-400">Error Details:</span>
                      <div className="bg-red-950/40 border border-red-800/60 rounded-lg p-3 font-mono text-xs text-red-200 whitespace-pre-wrap max-h-36 overflow-y-auto">
                        {execErrorDetails}
                      </div>
                    </div>
                  )}

                  {(execStatus === 'success' || execStatus === 'error') && (
                    <button
                      onClick={() => {
                        setExecStatus('idle');
                        setExecProgramOutput('');
                        setExecErrorDetails('');
                      }}
                      className="px-2.5 py-1.5 rounded-lg border border-slate-700 bg-slate-900 text-[10px] font-semibold text-slate-300 hover:border-slate-500"
                    >
                      Clear Output
                    </button>
                  )}
                  <div ref={outputEndRef} />
                </div>
              </div>
            )}
          </div>
        </aside>
      </div>
    </div>
  );
};

export default WorkspacePage;
