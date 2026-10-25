/**
 * Regression tests for the Pyodide browser-based execution path.
 *
 * These tests cover the parts that can be verified in Node/Vitest without a
 * browser or Pyodide runtime:
 *   - Static import rejection (unsupported modules)
 *   - Result shape transformation (browser → server contract)
 *   - Timeout and output-limit behaviour
 *
 * Full end-to-end Pyodide execution requires a browser with WebAssembly and
 * Web Worker support; it is checked separately against a production build.
 */

import { describe, it, expect } from 'vitest';
import { appendLimitedOutput, findUnsupportedImports, MAX_OUTPUT_CHARS, UNSUPPORTED_MODULES } from './pyodide-utils';
import { browserResultToServerShape, type PyodideRunResult } from './pyodide-executor';

// ---------------------------------------------------------------------------
// findUnsupportedImports
// ---------------------------------------------------------------------------
describe('findUnsupportedImports', () => {
  it('returns [] for code with no imports', () => {
    expect(findUnsupportedImports('print(1 + 1)')).toEqual([]);
    expect(findUnsupportedImports('x = 5\nif x > 0:\n    print("pos")')).toEqual([]);
  });

  it('rejects os import', () => {
    expect(findUnsupportedImports('import os')).toEqual(['os']);
  });

  it('rejects sys import', () => {
    expect(findUnsupportedImports('import sys')).toEqual(['sys']);
  });

  it('rejects socket import', () => {
    expect(findUnsupportedImports('import socket')).toEqual(['socket']);
  });

  it('rejects subprocess import', () => {
    expect(findUnsupportedImports('import subprocess')).toEqual(['subprocess']);
  });

  it('rejects from-imports', () => {
    expect(findUnsupportedImports('from os import path')).toEqual(['os']);
    expect(findUnsupportedImports('from sys import argv')).toEqual(['sys']);
  });

  it('allows supported builtins', () => {
    expect(findUnsupportedImports('import math')).toEqual([]);
    expect(findUnsupportedImports('print(abs(-5))')).toEqual([]);
  });

  it('deduplicates repeated imports', () => {
    expect(findUnsupportedImports('import os\nimport os')).toEqual(['os']);
  });

  it('finds multiple unsupported modules', () => {
    const result = findUnsupportedImports('import os\nimport sys\nimport socket');
    expect(result).toEqual(expect.arrayContaining(['os', 'sys', 'socket']));
    expect(result.length).toBe(3);
  });
});

// ---------------------------------------------------------------------------
// browserResultToServerShape
// ---------------------------------------------------------------------------
describe('browserResultToServerShape', () => {
  it('maps success result correctly', () => {
    const input: PyodideRunResult = {
      status: 'success',
      stdout: '120\n',
      stderr: '',
      exit_code: 0,
      timed_out: false,
      truncated: false,
      message: '',
      mode: 'browser',
    };
    const out = browserResultToServerShape(input);
    expect(out.status).toBe('success');
    expect(out.success).toBe(true);
    expect(out.output).toBe('120\n');
    expect(out.program_output).toBe('120');
    expect(out.execution_mode).toBe('browser');
    expect(out.error_details).toBe('');
  });

  it('maps error result correctly', () => {
    const input: PyodideRunResult = {
      status: 'error',
      stdout: '',
      stderr: 'NameError: name x is not defined',
      exit_code: 1,
      timed_out: false,
      truncated: false,
      message: 'NameError: name x is not defined',
      mode: 'browser',
    };
    const out = browserResultToServerShape(input);
    expect(out.status).toBe('error');
    expect(out.success).toBe(false);
    expect(out.error_details).toBe("NameError: name x is not defined");
    expect(out.program_output).toBe('');
  });

  it('maps timeout result correctly', () => {
    const input: PyodideRunResult = {
      status: 'timeout',
      stdout: '',
      stderr: '',
      exit_code: null,
      timed_out: true,
      truncated: false,
      message: 'Execution timed out after 5 seconds.',
      mode: 'browser',
    };
    const out = browserResultToServerShape(input);
    expect(out.status).toBe('error');
    expect(out.success).toBe(false);
    expect(out.timed_out).toBe(true);
    expect(out.output).toBe('Execution timed out after 5 seconds.');
  });

  it('preserves the output truncation flag in server-shaped results', () => {
    const longOutput = 'x'.repeat(70000);
    const input: PyodideRunResult = {
      status: 'success',
      stdout: longOutput,
      stderr: '',
      exit_code: 0,
      timed_out: false,
      truncated: true,
      message: '',
      mode: 'browser',
    };
    const out = browserResultToServerShape(input);
    expect(out.truncated).toBe(true);
  });
});

// ---------------------------------------------------------------------------
// UNSUPPORTED_MODULES coverage
// ---------------------------------------------------------------------------
describe('UNSUPPORTED_MODULES', () => {
  it('includes modules that require C extensions', () => {
    ['os', 'sys', 'subprocess', 'socket', 'shutil', 'pathlib', 'ctypes',
     'http', 'urllib', 'requests', 'threading', 'select'].forEach((mod) => {
      expect(UNSUPPORTED_MODULES.has(mod)).toBe(true);
    });
  });

  it('does not include basic builtins', () => {
    expect(UNSUPPORTED_MODULES.has('math')).toBe(false);
    expect(UNSUPPORTED_MODULES.has('print')).toBe(false);
  });
});

describe('appendLimitedOutput', () => {
  it('caps output and marks it as truncated when the limit is exceeded', () => {
    expect(appendLimitedOutput('x'.repeat(MAX_OUTPUT_CHARS - 1), 'yz')).toBe(
      'x'.repeat(MAX_OUTPUT_CHARS - 1) + 'y\n[output truncated]',
    );
  });

  it('does not add the truncation marker when output is exactly at the limit', () => {
    expect(appendLimitedOutput('x'.repeat(MAX_OUTPUT_CHARS - 1), 'y')).toBe(
      'x'.repeat(MAX_OUTPUT_CHARS - 1) + 'y',
    );
  });
});
