import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
        // Analysis runs multiple static passes and sandbox measurements. Keep
        // the proxy connection alive long enough for larger uploads to finish.
        timeout: 600000,
        rewrite: (path) => path.replace(/^\/api/, '')
      }
    }
  }
})
