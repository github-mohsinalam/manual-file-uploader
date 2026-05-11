/**
 * Root component of the application.
 *
 * Currently a smoke test for the data layer:
 *   - axios client correctly configured
 *   - TanStack Query fetching from the backend
 *   - TypeScript types flowing from the API response into UI
 *
 * This will be replaced by routing in Task 9.6 — App will become
 * a layout shell, and pages like DomainsList will live in their
 * own files under src/pages/.
 */

import { useQuery } from '@tanstack/react-query'
import { Button } from '@/components/ui/button'
import { listDomains } from '@/services/domains'
import type { Domain } from '@/types'

function App() {
  // useQuery reads from the shared cache (or fetches if missing).
  // The generic <Domain[]> tells TypeScript what shape data has.
  // queryKey identifies the cached entry; queryFn is the fetcher.
  const { data, isLoading, error, refetch } = useQuery<Domain[]>({
    queryKey: ['domains'],
    queryFn: listDomains,
  })

  return (
    <div className="min-h-screen bg-slate-50 p-8">
      <div className="max-w-2xl mx-auto space-y-6">
        <div>
          <h1 className="text-3xl font-bold text-slate-900">
            Manual File Uploader
          </h1>
          <p className="text-slate-600 mt-1">
            API client smoke test — fetching domains from the backend.
          </p>
        </div>

        <div className="bg-white rounded-lg border border-slate-200 p-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-xl font-semibold text-slate-900">
              Domains
            </h2>
            <Button onClick={() => refetch()} variant="outline" size="sm">
              Refresh
            </Button>
          </div>

          {isLoading && (
            <p className="text-slate-500">Loading domains...</p>
          )}

          {error && (
            <p className="text-red-600">
              Error loading domains: {(error as Error).message}
            </p>
          )}

          {data && data.length === 0 && (
            <p className="text-slate-500">No domains found.</p>
          )}

          {data && data.length > 0 && (
            <ul className="divide-y divide-slate-200">
              {data.map((domain) => (
                <li key={domain.id} className="py-3">
                  <div className="font-medium text-slate-900">
                    {domain.name}
                  </div>
                  <div className="text-sm text-slate-500">
                    Schema: <code>{domain.uc_schema_name}</code>
                  </div>
                  {domain.description && (
                    <div className="text-sm text-slate-600 mt-1">
                      {domain.description}
                    </div>
                  )}
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </div>
  )
}

export default App