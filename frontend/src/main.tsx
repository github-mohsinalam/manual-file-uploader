/**
 * Application entry point.
 *
 * createRoot mounts the React tree into the <div id="root"> in
 * index.html. Everything React renders lives inside that div.
 *
 * The QueryClientProvider wraps the app so every component can
 * call useQuery / useMutation. Without this provider, those
 * hooks throw at runtime.
 *
 * StrictMode is a React dev-only safety net that runs effects
 * twice and surfaces side-effect bugs early. In production
 * builds it has no effect on behavior or performance.
 */

import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { QueryClientProvider } from '@tanstack/react-query'
import './index.css'
import App from './App.tsx'
import { queryClient } from '@/lib/api/query-client'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <App />
    </QueryClientProvider>
  </StrictMode>,
)