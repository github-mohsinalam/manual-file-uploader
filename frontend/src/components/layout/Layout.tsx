/**
 * Root layout for the application.
 *
 * Provides the persistent shell (sidebar + main content area)
 * around every page. The Outlet component is where the
 * child route's content renders.
 */

import { Outlet } from 'react-router-dom'
import { Sidebar } from '@/components/layout/Sidebar'

export function Layout() {
  return (
    <div className="flex min-h-screen bg-slate-50">
      <Sidebar />
      <main className="flex-1 p-8">
        <div className="max-w-5xl mx-auto">
          <Outlet />
        </div>
      </main>
    </div>
  )
}