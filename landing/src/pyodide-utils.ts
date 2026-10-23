/**
 * Shared Pyodide utility functions used by both the Web Worker and tests.
 * Kept free of browser globals (self, Worker, etc.) so it can be unit tested
 * in Node/Vitest without a DOM or Pyodide runtime.
 */

// Modules that the generated flowchart compiler never needs and that Pyodide
// either lacks entirely or provides only in a crippled form.  We reject them
// up front with a clear message rather than letting Pyodide fail obscurely.
export const UNSUPPORTED_MODULES = new Set([
  'os', 'sys', 'subprocess', 'socket', 'shutil', 'pathlib', 'ctypes',
  'importlib', 'multiprocessing', 'threading', 'signal', 'pickle',
  'http', 'urllib', 'requests', 'ftplib', 'webbrowser',
  'builtins', 'runpy', 'code', 'codeop', 'inspect', 'gc', 'marshal',
  'resource', 'mmap', 'fcntl', 'posix', 'nt', 'pty', 'tempfile', 'glob',
  'asyncio', 'select', 'selectors', 'atexit',
]);

/**
 * Statically detect imports of modules that are not supported in Pyodide.
 * Returns a list of unsupported module names found in `code`.
 * Regex-based (no AST parse) so it stays fast and dependency-free.
 */
export function findUnsupportedImports(code: string): string[] {
  const found: string[] = [];
  const importRe = /(?:^\s*import\s+([a-zA-Z_][a-zA-Z0-9_]*)|^\s*from\s+([a-zA-Z_][a-zA-Z0-9_]*)\s+import)/gm;
  let match: RegExpExecArray | null;
  while ((match = importRe.exec(code)) !== null) {
    const mod = match[1] || match[2];
    if (mod && UNSUPPORTED_MODULES.has(mod) && !found.includes(mod)) {
      found.push(mod);
    }
  }
  return found;
}
