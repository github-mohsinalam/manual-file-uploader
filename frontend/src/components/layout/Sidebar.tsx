/**
 * Sidebar navigation component.
 *
 * Renders the persistent left-hand nav with one entry per
 * top-level section of the app. Highlights the active route
 * using NavLink's automatic isActive state.
 */

import { NavLink } from 'react-router-dom'
import {
  FileText,
  Upload,
  Database,
  Info,
} from 'lucide-react'
import { cn } from '@/lib/utils'

/**
 * The list of nav items.
 * Each has a path, label, and icon component.
 * Adding a new section means adding one entry here.
 */
const navItems = [
  { to: '/templates', label: 'Templates', icon: FileText },
  { to: '/uploads', label: 'Uploads', icon: Upload },
  { to: '/domains', label: 'Domains', icon: Database },
  { to: '/about', label: 'About', icon: Info },
]

export function Sidebar() {
  return (
    <aside className="w-60 bg-slate-900 text-slate-100 min-h-screen p-4">
      <div className="mb-8">
        <h2 className="text-xl font-bold">Manual File Uploader</h2>
        <p className="text-xs text-slate-400 mt-1">Phase 9 in progress</p>
      </div>

      <nav className="space-y-1">
        {navItems.map((item) => {
          const Icon = item.icon
          return (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) =>
                cn(
                  'flex items-center gap-3 px-3 py-2 rounded-md text-sm transition-colors',
                  isActive
                    ? 'bg-slate-800 text-white'
                    : 'text-slate-300 hover:bg-slate-800 hover:text-white'
                )
              }
            >
              <Icon size={16} />
              {item.label}
            </NavLink>
          )
        })}
      </nav>
    </aside>
  )
}