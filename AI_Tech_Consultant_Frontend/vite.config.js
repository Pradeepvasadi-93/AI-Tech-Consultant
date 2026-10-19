import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// Proxy requests through Vite to avoid browser CORS issues during local development.
export default defineConfig({
  plugins: [react()],
  server: {
    host: '127.0.0.1',
    port: 5173,
    strictPort: true,
    proxy: {
      '/api/task1': { target: 'http://127.0.0.1:8000', changeOrigin: true, rewrite: path => path.replace(/^\/api\/task1/, '') },
      '/api/task2': { target: 'http://127.0.0.1:8001', changeOrigin: true, rewrite: path => path.replace(/^\/api\/task2/, '') },
      '/api/task3': { target: 'http://127.0.0.1:8002', changeOrigin: true, rewrite: path => path.replace(/^\/api\/task3/, '') }
    }
  }
});
