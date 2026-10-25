import { afterEach, describe, expect, it, vi } from 'vitest';
import { apiJson } from './api';
import { runWithBrowserFallback } from './execution-fallback';
import { browserResultToServerShape } from '../pyodide-executor';

afterEach(() => {
  vi.unstubAllGlobals();
});

describe('runWithBrowserFallback', () => {
  it('uses browser execution when the backend request fails at the network layer', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('Failed to fetch')));
    const browserResult = browserResultToServerShape({
      status: 'success',
      stdout: '120\n',
      stderr: '',
      exit_code: 0,
      timed_out: false,
      truncated: false,
      message: '',
      mode: 'browser',
    });
    const serverRun = () => apiJson('/api/execute');
    const browserRun = vi.fn().mockResolvedValue(browserResult);

    await expect(runWithBrowserFallback(serverRun, browserRun)).resolves.toEqual({
      mode: 'browser',
      result: browserResult,
    });
    expect(browserResult).toMatchObject({ success: true, program_output: '120' });
    expect(browserRun).toHaveBeenCalledOnce();
  });

  it('uses browser execution for HTTP 403', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
      ok: false,
      status: 403,
      json: async () => ({ detail: 'Execution disabled' }),
    }));
    const serverRun = () => apiJson('/api/execute');
    const browserRun = vi.fn().mockResolvedValue({ success: true });

    await expect(runWithBrowserFallback(serverRun, browserRun)).resolves.toMatchObject({
      mode: 'browser',
      result: { success: true },
    });
    expect(browserRun).toHaveBeenCalledOnce();
  });

  it.each(['Execution disabled by configuration.', 'Sandbox unavailable on this host.'])(
    'uses browser execution when the backend reports %s',
    async (message) => {
      vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
        ok: false,
        status: 503,
        json: async () => ({ detail: message }),
      }));
      const serverRun = () => apiJson('/api/execute');
      const browserRun = vi.fn().mockResolvedValue({ success: true });

      await expect(runWithBrowserFallback(serverRun, browserRun)).resolves.toMatchObject({
        mode: 'browser',
      });
      expect(browserRun).toHaveBeenCalledOnce();
    },
  );

  it('keeps unrelated backend errors on the server error path', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
      ok: false,
      status: 422,
      json: async () => ({ detail: 'Invalid graph' }),
    }));
    const serverRun = () => apiJson('/api/execute');
    const browserRun = vi.fn().mockResolvedValue({ success: true });

    await expect(runWithBrowserFallback(serverRun, browserRun)).rejects.toThrow('Invalid graph');
    expect(browserRun).not.toHaveBeenCalled();
  });

  it('returns successful server execution without invoking the browser', async () => {
    const browserRun = vi.fn();

    await expect(runWithBrowserFallback(
      async () => ({ success: true, program_output: '120' }),
      browserRun,
    )).resolves.toEqual({
      mode: 'server',
      result: { success: true, program_output: '120' },
    });
    expect(browserRun).not.toHaveBeenCalled();
  });
});
