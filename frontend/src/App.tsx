/**
 * Root component of the application.
 *
 * Smoke test for the toolchain:
 *   - Path alias (@/) resolving correctly
 *   - Tailwind CSS classes applying
 *   - shadcn/ui Button component rendering and interactive
 *
 * Real routes and pages will replace this in Task 9.5 onward.
 */
import { Button } from '@/components/ui/button'

function App() {
  return (
    <div className="min-h-screen bg-slate-50 flex items-center justify-center">
      <div className="text-center space-y-4">
        <h1 className="text-4xl font-bold text-slate-900">
          Manual File Uploader
        </h1>
        <p className="text-slate-600">
          Toolchain check — Tailwind, path aliases, shadcn/ui Button.
        </p>
        <div className="flex gap-2 justify-center">
          <Button>Default</Button>
          <Button variant="outline">Outline</Button>
          <Button variant="destructive">Destructive</Button>
          <Button variant="secondary">Secondary</Button>
        </div>
      </div>
    </div>
  )
}

export default App