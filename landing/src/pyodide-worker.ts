/**
 * FlowForge Pyodide Web Worker
 *
 * Runs untrusted Python code entirely in the browser using Pyodide (Python
 * compiled to WebAssembly).  This is a client-side execution path that never
 * touches the backend, sends no code or secrets to any server, and runs in an
 * isolated Web Worker thread.
 *
 * The worker loads Pyodide from a pinned CDN URL, executes the received code,
 * captures stdout/stderr, and posts results back to the main thread.
 *
 * Supported: basic Python (print, input, arithmetic, conditionals, loops,
 * variables, function definitions).  Modules requiring C extensions that are
 * not compiled for WASM (os, subprocess, socket, etc.) are rejected with a
 * clear error message.
 *
 * Messages received: { type: 'RUN', code, userInput, timeoutMs }
 * Messages sent:   { type: 'RESULT', ... } | { type: 'LOADING', progress }
 */

// ---------------------------------------------------------------------------
// Configuration
// ---------------------------------------------------------------------------
const PYODIDE_VERSION = '0.27.3';
const PYODIDE_CDN = `https://cdn.jsdelivr.net/pyodide/v${PYODIDE_VERSION}/full/`;
const MAX_OUTPUT_CHARS = 65536;      // ~64 KB cap, mirrors the backend limit

import { findUnsupportedImports } from './pyodide-utils';

// ---------------------------------------------------------------------------
// State
// ---------------------------------------------------------------------------
let pyodide: any = null;
let initPromise: Promise<any> | null = null;
let stdoutBuffer = '';
let stderrBuffer = '';
let inputQueue: string[] = [];

// ---------------------------------------------------------------------------
// Pyodide initialisation
// ---------------------------------------------------------------------------
async function ensurePyodide(): Promise<any> {
  if (pyodide) return pyodide;
  if (initPromise) return initPromise;

  initPromise = (async () => {
    self.postMessage({ type: 'LOADING', progress: 0, message: 'Downloading Pyodide runtime…' });
    // Dynamic import from a pinned CDN URL (type-safe shim below).
    const mod = await import(/* @ts-ignore */ PYODIDE_CDN + 'pyodide.mjs');
    const py = await mod.loadPyodide({ indexURL: PYODIDE_CDN });
    self.postMessage({ type: 'LOADING', progress: 100, message: 'Pyodide ready.' });
    pyodide = py;
    return py;
  })();

  return initPromise;
}

// ---------------------------------------------------------------------------
// Stdout / stderr capture
// ---------------------------------------------------------------------------
function captureOutput(text: string, isError: boolean): void {
  if (isError) {
    stderrBuffer += text;
    if (stderrBuffer.length > MAX_OUTPUT_CHARS) {
      stderrBuffer = stderrBuffer.slice(0, MAX_OUTPUT_CHARS) + '\n[output truncated]';
    }
  } else {
    stdoutBuffer += text;
    if (stdoutBuffer.length > MAX_OUTPUT_CHARS) {
      stdoutBuffer = stdoutBuffer.slice(0, MAX_OUTPUT_CHARS) + '\n[output truncated]';
    }
  }
}

// ---------------------------------------------------------------------------
// Stdin handling for input()
//
// We pre-load the user-provided input into a queue.  When the Python program
// calls input(), we pop the next line.  If the queue is exhausted we return
// an empty string so the Python program can handle it (e.g. int('') raises,
// which we report as a normal runtime error).
// ---------------------------------------------------------------------------
function refillStdin(py: any): void {
  const readline = () => {
    if (inputQueue.length > 0) {
      return inputQueue.shift()! + '\n';
    }
    return '';
  };
  py.setStdin({ readline, isatty: () => false });
}

// ---------------------------------------------------------------------------
// Code execution
// ---------------------------------------------------------------------------
async function runCode(code: string, userInput: string, timeoutMs: number): Promise<void> {
  const py = await ensurePyodide();

  // Reset buffers
  stdoutBuffer = '';
  stderrBuffer = '';

  // Static pre-check: reject imports of unsupported modules
  const unsupported = findUnsupportedImports(code);
  if (unsupported.length) {
    const names = unsupported.join(', ');
    throw new Error(
      `Unsupported module(s): ${names}. Browser execution only supports the Python ` +
      'standard library subset available in Pyodide (print, input, math, basic ' +
      'control flow). Try server-side execution for full Python support.'
    );
  }

  // Load user input into the stdin queue
  inputQueue = (userInput || '')
    .split('\n')
    .map((l) => l.trimEnd())
    .filter((l) => l.length > 0);

  // Set up output capture
  py.setStdout({ batched: (msg: string) => captureOutput(msg, false) });
  py.setStderr({ batched: (msg: string) => captureOutput(msg, true) });
  refillStdin(py);

  // Execute with a timeout.  On timeout we terminate the worker from the main
  // thread instead (see pyodide-executor.ts).
  const execPromise = py.runPythonAsync(code);
  const timeoutPromise = new Promise<never>((_, reject) => {
    setTimeout(() => reject(new Error(`Execution timed out after ${timeoutMs / 1000} seconds.`)), timeoutMs);
  });

  await Promise.race([execPromise, timeoutPromise]);
}

// ---------------------------------------------------------------------------
// Message handler
// ---------------------------------------------------------------------------
self.onmessage = async (event: MessageEvent) => {
  const { type, code, userInput, timeoutMs } = event.data || {};

  if (type === 'RUN') {
    try {
      await runCode(code, userInput ?? '', timeoutMs ?? 5000);
      self.postMessage({
        type: 'RESULT',
        status: stderrBuffer ? 'error' : 'success',
        stdout: stdoutBuffer,
        stderr: stderrBuffer,
        exit_code: stderrBuffer ? 1 : 0,
        timed_out: false,
        truncated: stdoutBuffer.length >= MAX_OUTPUT_CHARS || stderrBuffer.length >= MAX_OUTPUT_CHARS,
        message: stderrBuffer || '',
        mode: 'browser',
      });
    } catch (err: any) {
      self.postMessage({
        type: 'RESULT',
        status: 'error',
        stdout: stdoutBuffer,
        stderr: stderrBuffer || err.message || String(err),
        exit_code: 1,
        timed_out: err.message?.includes('timed out') ?? false,
        truncated: false,
        message: err.message || String(err),
        mode: 'browser',
      });
    }
  }
};
