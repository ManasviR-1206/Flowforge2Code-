/**
 * FlowForge Pyodide Executor (browser-based)
 *
 * Manages a Web Worker that runs Python code via Pyodide.  Provides an API
 * similar to the server-side /api/execute so the frontend can switch between
 * server and browser execution without changing the UI contract.
 *
 * Execution is fully client-side: no code, input, or output is sent to any
 * server.  The worker is terminated and recreated on timeout to enforce
 * execution limits.
 */
// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------
export interface PyodideRunOptions {
  code: string;
  userInput: string;
  timeoutSec: number;
}

export interface PyodideRunResult {
  status: 'success' | 'error' | 'timeout' | 'rejected';
  stdout: string;
  stderr: string;
  exit_code: number | null;
  timed_out: boolean;
  truncated: boolean;
  message: string;
  mode: 'browser';
}

// ---------------------------------------------------------------------------
// Worker URL
// ---------------------------------------------------------------------------
const WORKER_URL = new URL('./pyodide-worker.ts', import.meta.url).href;

// ---------------------------------------------------------------------------
// Executor class
// ---------------------------------------------------------------------------
export class PyodideExecutor {
  private worker: Worker | null = null;
  private resolve: ((value: PyodideRunResult) => void) | null = null;
  private reject: ((err: Error) => void) | null = null;
  private timeoutTimer: number | null = null;

  /** True if the worker is currently busy running code. */
  get isBusy(): boolean {
    return this.resolve !== null;
  }

  /** Construct.  The worker is created lazily on first run. */
  constructor() {
    // Handle messages from the worker
    const onMessage = (event: MessageEvent) => {
      const data = event.data || {};
      switch (data.type) {
        case 'RESULT': {
          this.clearTimeout();
          const r = this.resolve;
          this.resolve = null;
          this.reject = null;
          if (r) r(data as PyodideRunResult);
          break;
        }
        case 'LOADING': {
          // Surface loading progress via the global progress callback if set
          if (this.onProgress) this.onProgress(data);
          break;
        }
        default: {
          // Ignore unknown message types
        }
      }
    };

    const onError = (err: ErrorEvent) => {
      this.clearTimeout();
      const r = this.reject;
      this.resolve = null;
      this.reject = null;
      if (r) r(new Error(`Worker error: ${err.message || 'unknown worker error'}`));
    };

    this._onMessage = onMessage;
    this._onError = onError;
  }

  private _onMessage: (event: MessageEvent) => void = () => {};
  private _onError: (event: ErrorEvent) => void = () => {};
  private onProgress?: (data: any) => void;

  /** Set a callback for Pyodide loading progress events. */
  setProgressCallback(cb: (data: any) => void): void {
    this.onProgress = cb;
  }

  private createWorker(): Worker {
    const worker = new Worker(WORKER_URL, { type: 'module' });
    worker.addEventListener('message', this._onMessage);
    worker.addEventListener('error', this._onError);
    return worker;
  }

  private clearTimeout(): void {
    if (this.timeoutTimer !== null) {
      window.clearTimeout(this.timeoutTimer);
      this.timeoutTimer = null;
    }
  }

  private terminateWorker(): void {
    this.clearTimeout();
    if (this.worker) {
      try {
        this.worker.terminate();
      } catch {
        // Ignore terminate errors
      }
      this.worker.removeEventListener('message', this._onMessage);
      this.worker.removeEventListener('error', this._onError);
      this.worker = null;
    }
  }

  /**
   * Run Python code in the browser via Pyodide.
   * Returns a promise that resolves with a result object matching the
   * server-side execution contract.
   */
  run(opts: PyodideRunOptions): Promise<PyodideRunResult> {
    if (this.isBusy) {
      return Promise.reject(new Error('Execution already in progress.'));
    }

    return new Promise((resolve, reject) => {
      this.resolve = resolve;
      this.reject = reject;

      // (Re)create the worker for a clean slate each run
      this.terminateWorker();
      this.worker = this.createWorker();

      // Enforce timeout from the main thread by terminating the worker
      const timeoutMs = Math.max(500, Math.min(opts.timeoutSec * 1000, 30000));
      this.timeoutTimer = window.setTimeout(() => {
        this.terminateWorker();
        const r = this.resolve;
        this.resolve = null;
        this.reject = null;
        if (r) {
          r({
            status: 'timeout',
            stdout: '',
            stderr: '',
            exit_code: null,
            timed_out: true,
            truncated: false,
            message: `Execution timed out after ${opts.timeoutSec} seconds.`,
            mode: 'browser',
          });
        }
      }, timeoutMs + 1000); // Give the worker 1s extra to send its own result

      this.worker.postMessage({
        type: 'RUN',
        code: opts.code,
        userInput: opts.userInput,
        timeoutMs,
      });
    });
  }

  /** Terminate the worker and release resources. */
  destroy(): void {
    this.clearTimeout();
    this.terminateWorker();
    this.resolve = null;
    this.reject = null;
  }
}

// ---------------------------------------------------------------------------
// Singleton
// ---------------------------------------------------------------------------
export const pyodideExecutor = new PyodideExecutor();

// ---------------------------------------------------------------------------
// Convert a browser result into the same shape the UI expects from the server
// ---------------------------------------------------------------------------
export function browserResultToServerShape(result: PyodideRunResult): {
  output: string;
  stdout: string;
  stderr: string;
  status: string;
  success: boolean;
  error_details: string;
  program_output: string;
  timed_out: boolean;
  truncated: boolean;
  execution_mode: string;
} {
  const output = result.status === 'success' ? result.stdout : result.message;
  const status = result.status === 'timeout' ? 'error' : result.status;
  const success = result.status === 'success';
  return {
    output,
    stdout: result.stdout,
    stderr: result.stderr,
    status,
    success,
    error_details: result.status === 'error' ? result.message : '',
    program_output: result.stdout.trim(),
    timed_out: result.timed_out,
    truncated: result.truncated,
    execution_mode: 'browser',
  };
}
