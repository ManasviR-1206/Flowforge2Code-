export async function apiJson(path: string, options?: RequestInit) {
  const res = await fetch(path, options);
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
      type: 'smoothstep',
      animated: true,
    })),
  };
}
