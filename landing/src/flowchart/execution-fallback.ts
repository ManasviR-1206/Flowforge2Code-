import { ApiRequestError } from './api';

export function shouldFallbackToBrowser(error: unknown): boolean {
  if (error instanceof TypeError) return true;
  if (!(error instanceof Error)) return false;
  if (error instanceof ApiRequestError && error.status === 403) return true;
  return /\b(disabled|sandbox)\b/i.test(error.message);
}

export async function runWithBrowserFallback<TServer, TBrowser>(
  serverRun: () => Promise<TServer>,
  browserRun: () => Promise<TBrowser>,
): Promise<
  | { mode: 'server'; result: TServer }
  | { mode: 'browser'; result: TBrowser }
> {
  try {
    return { mode: 'server', result: await serverRun() };
  } catch (error) {
    if (!shouldFallbackToBrowser(error)) throw error;
    return { mode: 'browser', result: await browserRun() };
  }
}
