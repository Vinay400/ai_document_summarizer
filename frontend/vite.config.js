import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

// Tailwind v4 integrates as a first-party Vite plugin (no tailwind.config.js
// and no PostCSS pipeline are required any more).
export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    port: 5173,
    // The front-end talks to FastAPI directly over HTTP (cross-origin), which
    // is deliberate: it exercises the backend CORS configuration that the
    // project is required to implement. No dev proxy is used.
    strictPort: true,
  },
})
