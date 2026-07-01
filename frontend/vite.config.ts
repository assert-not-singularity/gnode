import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// Dev server proxies API calls to the FastAPI backend (`make serve`, port 8080).
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/api': 'http://127.0.0.1:8080',
    },
  },
})
