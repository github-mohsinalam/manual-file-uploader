/**
 * Domains page.
 *
 * Lists the seeded business domains. Each domain maps to a
 * Unity Catalog schema. Domains are seeded in PostgreSQL and
 * are not user-creatable from this UI.
 */

import { Database } from 'lucide-react'

import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import { useDomains } from '@/hooks/useDomains'

export default function Domains() {
  const { data, isLoading, error } = useDomains()

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-slate-900">Domains</h1>
        <p className="text-slate-600 mt-1">
          Business domains available for templates. Each domain maps
          to a Unity Catalog schema.
        </p>
      </div>

      {isLoading && <DomainsListSkeleton />}

      {error && (
        <Card>
          <CardContent className="pt-6">
            <p className="text-red-600">
              Failed to load domains: {(error as Error).message}
            </p>
          </CardContent>
        </Card>
      )}

      {data && data.length === 0 && (
        <Card>
          <CardContent className="pt-6">
            <p className="text-slate-500">No domains have been seeded.</p>
          </CardContent>
        </Card>
      )}

      {data && data.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {data.map((domain) => (
            <Card key={domain.id}>
              <CardHeader>
                <div className="flex items-start gap-3">
                  <div className="bg-slate-100 p-2 rounded-md">
                    <Database size={20} className="text-slate-700" />
                  </div>
                  <div className="flex-1">
                    <CardTitle>{domain.name}</CardTitle>
                    <CardDescription>
                      Schema: <code>{domain.uc_schema_name}</code>
                    </CardDescription>
                  </div>
                </div>
              </CardHeader>
              {domain.description && (
                <CardContent>
                  <p className="text-sm text-slate-600">
                    {domain.description}
                  </p>
                </CardContent>
              )}
            </Card>
          ))}
        </div>
      )}
    </div>
  )
}

/**
 * Skeleton loader for the domain grid.
 *
 * Renders 4 gray pulsing card-shaped boxes while the real
 * data is being fetched. Gives users a visual cue that data
 * is coming and roughly how it will be laid out.
 */
function DomainsListSkeleton() {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
      {Array.from({ length: 4 }).map((_, i) => (
        <Card key={i}>
          <CardHeader>
            <Skeleton className="h-5 w-32 mb-2" />
            <Skeleton className="h-4 w-24" />
          </CardHeader>
          <CardContent>
            <Skeleton className="h-4 w-full mb-1" />
            <Skeleton className="h-4 w-4/5" />
          </CardContent>
        </Card>
      ))}
    </div>
  )
}