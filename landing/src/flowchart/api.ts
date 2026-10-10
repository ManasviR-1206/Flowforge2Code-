const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || '').replace(/\/$/, '');

export function apiUrl(path: string) {
  return `${API_BASE_URL}${path.startsWith('/') ? path : `/${path}`}`;
}

export async function apiJson(path: string, options?: RequestInit) {
  const res = await fetch(apiUrl(path), options);
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const detail = (data as any)?.detail;
    const msg = typeof detail === 'string' ? detail : Array.isArray(detail) ? detail.map((d: any) => d.msg || d).join(' ') : (data as any)?.message || `Request failed (${res.status})`;
    throw new Error(msg);
  }
  return data;
}

export function graphPayload(nodes: any[], edges: any[]) {
  return {
    nodes: nodes.map((n) => ({
      id: n.id,
      type: n.type,
      position: n.position,
      data: { label: n.data?.label || '' },
    })),
    edges: edges.map((e) => ({
      id: e.id,
      source: e.source,
      target: e.target,
      label: e.label || '',
      sourceHandle: e.sourceHandle,
      data: e.data?.uncertain ? { uncertain: true, confidence: e.data.confidence } : undefined,
      type: 'smoothstep',
      animated: true,
    })),
  };
}
