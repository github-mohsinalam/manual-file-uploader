/**
 * Templates list page.
 *
 * Fetches templates from the backend with server-side filters
 * (status, search term). Renders them in a table with status
 * badges. Each row navigates to the template detail page.
 *
 * Filter state lives in this component (useState). The search
 * input is debounced 300ms so we do not hammer the backend
 * on every keystroke.
 */

import { useState } from 'react'
import { Link } from 'react-router-dom'
import { Plus, Search } from 'lucide-react'

import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { Card, CardContent } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'

import { StatusBadge } from '@/components/templates/StatusBadge'
import { useDebounce } from '@/hooks/useDebounce'
import { useTemplates } from '@/hooks/useTemplates'
import type { TemplateStatus } from '@/types'

// The status values we offer in the dropdown. Includes a
// sentinel 'all' for "no status filter".
const STATUS_OPTIONS: Array<{ value: TemplateStatus | 'all'; label: string }> = [
  { value: 'all', label: 'All statuses' },
  { value: 'Draft', label: 'Draft' },
  { value: 'Pending Approval', label: 'Pending Approval' },
  { value: 'Pending DDL', label: 'Pending DDL' },
  { value: 'Approved', label: 'Approved' },
  { value: 'Rejected', label: 'Rejected' },
  { value: 'DDL Failed', label: 'DDL Failed' },
  { value: 'Deprecated', label: 'Deprecated' },
]

export default function TemplatesList() {
  // Filter state - local to this page.
  const [statusFilter, setStatusFilter] = useState<TemplateStatus | 'all'>('all')
  const [searchInput, setSearchInput] = useState('')

  // Debounce the search input so we don't query the backend
  // on every keystroke.
  const debouncedSearch = useDebounce(searchInput, 300)

  // Build the filters object. Undefined values get dropped
  // from the URL by axios automatically.
  const filters = {
    status: statusFilter === 'all' ? undefined : statusFilter,
    search: debouncedSearch || undefined,
  }

  const { data, isLoading, error } = useTemplates(filters)

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-3xl font-bold text-slate-900">Templates</h1>
          <p className="text-slate-600 mt-1">
            Manage manual file templates and their target Unity Catalog tables.
          </p>
        </div>
        <Link to="/templates/new">
          <Button>
            <Plus size={16} />
            New Template
          </Button>
        </Link>
      </div>

      {/* Filters row */}
      <div className="flex gap-3">
        <div className="relative flex-1 max-w-md">
          <Search
            size={16}
            className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400"
          />
          <Input
            placeholder="Search by name or display name..."
            value={searchInput}
            onChange={(e) => setSearchInput(e.target.value)}
            className="pl-9"
          />
        </div>

        <Select
          value={statusFilter}
          onValueChange={(v) => setStatusFilter(v as TemplateStatus | 'all')}
        >
          <SelectTrigger className="w-56">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {STATUS_OPTIONS.map((opt) => (
              <SelectItem key={opt.value} value={opt.value}>
                {opt.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {/* Data area */}
      {isLoading && <TableSkeleton />}

      {error && (
        <Card>
          <CardContent className="pt-6">
            <p className="text-red-600">
              Failed to load templates: {(error as Error).message}
            </p>
          </CardContent>
        </Card>
      )}

      {data && data.length === 0 && (
        <Card>
          <CardContent className="pt-6 text-center space-y-2">
            <p className="text-slate-700 font-medium">No templates found.</p>
            <p className="text-sm text-slate-500">
              {statusFilter !== 'all' || debouncedSearch
                ? 'Try adjusting your filters.'
                : 'Create your first template to get started.'}
            </p>
          </CardContent>
        </Card>
      )}

      {data && data.length > 0 && (
        <Card>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Name</TableHead>
                <TableHead>Display name</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Version</TableHead>
                <TableHead>Created by</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {data.map((template) => (
                <TableRow key={template.id}>
                  <TableCell>
                    <Link
                      to={`/templates/${template.id}`}
                      className="font-medium text-slate-900 hover:underline"
                    >
                      {template.name}
                    </Link>
                  </TableCell>
                  <TableCell className="text-slate-700">
                    {template.display_name}
                  </TableCell>
                  <TableCell>
                    <StatusBadge status={template.status} />
                  </TableCell>
                  <TableCell className="text-slate-700">
                    v{template.version}
                  </TableCell>
                  <TableCell className="text-slate-700 text-sm">
                    {template.created_by}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </Card>
      )}
    </div>
  )
}

/**
 * Skeleton rows for the templates table.
 */
function TableSkeleton() {
  return (
    <Card>
      <div className="p-4 space-y-3">
        {Array.from({ length: 5 }).map((_, i) => (
          <div key={i} className="flex gap-4 items-center">
            <Skeleton className="h-4 w-32" />
            <Skeleton className="h-4 w-48" />
            <Skeleton className="h-4 w-24" />
            <Skeleton className="h-4 w-12" />
            <Skeleton className="h-4 w-40" />
          </div>
        ))}
      </div>
    </Card>
  )
}