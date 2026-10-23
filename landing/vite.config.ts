import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/api': {
        target: process.env.VITE_BACKEND_URL || 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
    },
    // Content Security Policy for the dev server.  Allows Pyodide (loaded from
    // a pinned CDN) and blob-based Web Workers while keeping everything else
    // same-origin.
    headers: {
      'Content-Security-Policy':
        "default-src 'self'; " +
        "script-src 'self' https://cdn.jsdelivr.net; " +
        "worker-src 'self' blob:; " +
        "connect-src 'self' https://cdn.jsdelivr.net; " +
        "style-src 'self' 'unsafe-inline'; " +
        "img-src 'self' data:; " +
        "font-src 'self';",
    },
  },
})
