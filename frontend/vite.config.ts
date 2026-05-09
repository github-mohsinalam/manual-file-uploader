import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

// Vite configuration.
// Plugins are registered here. Order matters in some cases but
// not for these two — react() handles JSX/TSX transformation,
// tailwindcss() scans source files for Tailwind classes and
// emits the right CSS.
export default defineConfig({
  plugins: [react(), tailwindcss()],
})