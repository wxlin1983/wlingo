/// <reference types="vitest/config" />
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

const rootPath = process.env.VITE_ROOT_PATH || ''

export default defineConfig(({ mode }) => ({
  plugins: [react()],
  // In dev: serve from root so HMR works cleanly.
  // In production: assets are under /static/ (optionally prefixed with ROOT_PATH).
  base: mode === 'production' ? (rootPath ? `${rootPath}/static/` : '/static/') : '/',
  build: {
    outDir: 'dist',
    emptyOutDir: true,
  },
  server: {
    port: 5173,
    proxy: {
      '/api': 'http://localhost:8002',
      '/start': 'http://localhost:8002',
      '/submit_answer': 'http://localhost:8002',
    },
  },
  test: {
    environment: 'jsdom',
    setupFiles: ['./src/test/setup.ts'],
  },
}))
