import { describe, it, expect } from 'vitest';
import indexHtml from '../index.html?raw';
import viteConfigText from '../vite.config.ts?raw';

function parseCspDirectives(cspString: string): Record<string, string[]> {
  const directives: Record<string, string[]> = {};
  const entries = cspString.split(';').map(s => s.trim()).filter(Boolean);
  for (const entry of entries) {
    const parts = entry.split(/\s+/).filter(Boolean);
    if (parts.length > 0) {
      const directiveName = parts[0];
      directives[directiveName] = parts.slice(1);
    }
  }
  return directives;
}

describe('Content Security Policy (CSP) Configuration', () => {
  it('has exactly one CSP meta tag in index.html with no duplicates', () => {
    const matches = indexHtml.match(/<meta[^>]*http-equiv=["']Content-Security-Policy["'][^>]*>/gi);
    expect(matches).not.toBeNull();
    expect(matches?.length).toBe(1);
  });

  it('enforces safe and strictly scoped directives in index.html', () => {
    const metaTagMatch = indexHtml.match(/<meta\s+http-equiv="Content-Security-Policy"\s+content="([^"]+)"/i);
    expect(metaTagMatch).not.toBeNull();
    const cspContent = metaTagMatch![1];
    const directives = parseCspDirectives(cspContent);

    // default-src: only 'self'
    expect(directives['default-src']).toEqual(["'self'"]);

    // connect-src: permits 'self', cdn.jsdelivr.net, and backend https://flowforge2code.onrender.com
    expect(directives['connect-src']).toBeDefined();
    expect(directives['connect-src']).toContain("'self'");
    expect(directives['connect-src']).toContain('https://cdn.jsdelivr.net');
    expect(directives['connect-src']).toContain('https://flowforge2code.onrender.com');

    // script-src: allows Pyodide WASM evaluation and CDN
    expect(directives['script-src']).toBeDefined();
    expect(directives['script-src']).toContain("'self'");
    expect(directives['script-src']).toContain("'wasm-unsafe-eval'");
    expect(directives['script-src']).toContain('https://cdn.jsdelivr.net');

    // worker-src: allows same-origin and blob for Pyodide worker
    expect(directives['worker-src']).toBeDefined();
    expect(directives['worker-src']).toContain("'self'");
    expect(directives['worker-src']).toContain('blob:');

    // style-src: allows 'self', 'unsafe-inline', and required font stylesheet domain
    expect(directives['style-src']).toBeDefined();
    expect(directives['style-src']).toContain("'self'");
    expect(directives['style-src']).toContain("'unsafe-inline'");
    expect(directives['style-src']).toContain('https://db.onlinewebfonts.com');

    // font-src: allows 'self' and required font domain
    expect(directives['font-src']).toBeDefined();
    expect(directives['font-src']).toContain("'self'");
    expect(directives['font-src']).toContain('https://db.onlinewebfonts.com');

    // img-src: allows same-origin, data URLs, and blob URLs for image previews
    expect(directives['img-src']).toBeDefined();
    expect(directives['img-src']).toContain("'self'");
    expect(directives['img-src']).toContain('data:');
    expect(directives['img-src']).toContain('blob:');

    // Ensure no broad wildcards (* or plain http: or unconstrained https:) in any directive
    for (const [, values] of Object.entries(directives)) {
      expect(values).not.toContain('*');
      expect(values).not.toContain('http:');
      expect(values).not.toContain('https:');
    }
  });

  it('maintains consistent CSP headers in vite.config.ts without conflicts', () => {
    expect(viteConfigText).toContain("'Content-Security-Policy'");
    expect(viteConfigText).toContain('https://flowforge2code.onrender.com');
    expect(viteConfigText).toContain('https://cdn.jsdelivr.net');
    expect(viteConfigText).toContain('https://db.onlinewebfonts.com');
  });
});
