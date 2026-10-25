import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [
    react(),
    // In Vite dev mode, React Fast Refresh requires an inline preamble script and WebSocket for HMR.
    // During dev only, relax script-src and connect-src so dev tooling functions.
    // Production builds (vite build) output the strict production CSP in index.html untouched.
    {
      name: 'dev-csp-transform',
      apply: 'serve',
      transformIndexHtml(html) {
        return html
          .replace(
            "script-src 'self'",
            "script-src 'self' 'unsafe-inline'"
          )
          .replace(
            "connect-src 'self'",
            "connect-src 'self' ws: http:"
          );
      },
    },
  ],
  server: {
    proxy: {
      '/api': {
        target: process.env.VITE_BACKEND_URL || 'http://127.0.0.1:8001',
        changeOrigin: true,
      },
    },
    // Content Security Policy for the dev server. Allows Pyodide, dev React Fast Refresh preamble,
    // and WebSocket HMR while keeping third-party origins restricted to approved services.
    headers: {
      'Content-Security-Policy':
        "default-src 'self'; " +
        "script-src 'self' 'unsafe-inline' 'wasm-unsafe-eval' https://cdn.jsdelivr.net; " +
        "worker-src 'self' blob:; " +
        "connect-src 'self' ws: http: https://cdn.jsdelivr.net https://flowforge2code.onrender.com; " +
        "style-src 'self' 'unsafe-inline' https://db.onlinewebfonts.com; " +
        "img-src 'self' data: blob:; " +
        "font-src 'self' https://db.onlinewebfonts.com;",
    },
  },
})
