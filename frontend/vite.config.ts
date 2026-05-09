import path from 'node:path'
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

// Vite configuration.
// Plugins are registered here. Order matters in some cases but
// not for these two — react() handles JSX/TSX transformation,
// tailwindcss() scans source files for Tailwind classes and
// emits the right CSS.
// resolve.alias maps `@/` to the absolute path of the src
// folder. This must mirror the `paths` setting in tsconfig.json
// so TypeScript and Vite both understand the same imports.
export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
})