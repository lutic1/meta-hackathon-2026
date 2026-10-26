import { defineConfig } from 'vite'

// The dev server forwards /api/* to uvicorn, so the client keeps one origin and never needs CORS (AD-9).
export default defineConfig({
  server: {
    proxy: {
      '/api': 'http://127.0.0.1:8000',
    },
  },
})
