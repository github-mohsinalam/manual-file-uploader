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
    <aside className="w-60 bg-white border border-slate-200 rounded-lg shadow-sm text-slate-700 p-4">
      <div className="mb-8">
        <h2 className="text-xl font-bold text-slate-900">Manual File Uploader</h2>
        <p className="text-xs text-slate-500 mt-1">Version 1</p>
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
                  'flex items-center gap-2 px-3 py-2 rounded-md text-sm transition-colors',
                  isActive
                  ? 'bg-indigo-50 hover:bg-indigo-100 text-indigo-900 font-semibold border-l-[3px] border-indigo-600 pl-[9px]'
                  : 'text-slate-600 hover:bg-slate-100 hover:text-slate-900 font-medium'
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