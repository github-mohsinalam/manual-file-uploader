/**
 * 404 Not Found page.
 *
 * Shown when the URL matches no defined route.
 */

import { Link } from 'react-router-dom'
import { Button } from '@/components/ui/button'

export default function NotFound() {
  return (
    <div className="space-y-4">
      <h1 className="text-3xl font-bold text-slate-900">Page not found</h1>
      <p className="text-slate-600">
        The page you requested does not exist or has been moved.
      </p>
      <Link to="/templates">
        <Button>Go to Templates</Button>
      </Link>
    </div>
  )
}