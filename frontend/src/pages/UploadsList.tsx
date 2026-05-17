/**
 * Uploads list page.
 *
 * Shows all file uploads across all templates with status,
 * row counts, and timestamps. Clicking a row navigates to
 * the progress/detail page.
 *
 * Filter state lives in the URL (status, search) so it survives
 * navigation and refresh - same pattern as the templates list.
 */

import { useEffect, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { Search } from 'lucide-react'

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

import { UploadStatusBadge } from '@/components/uploads/UploadStatusBadge'
import { useDebounce } from '@/hooks/useDebounce'
import { useUploads } from '@/hooks/useUploads'
import { useTemplates } from '@/hooks/useTemplates'
import { formatRelativeTime } from '@/lib/format'
import type { UploadStatus, UploadHistory, Template } from '@/types'

// Status values offered in the dropdown. 'all' is the no-filter
// sentinel.
const STATUS_OPTIONS: Array<{ value: UploadStatus | 'all'; label: string }> = [
  { value: 'all', label: 'All statuses' },
  { value: 'in_progress', label: 'In progress' },
  { value: 'file_uploaded', label: 'Uploaded' },
  { value: 'schema_validated', label: 'Schema OK' },
  { value: 'constraints_checked', label: 'Validating' },
  { value: 'writing_to_catalog', label: 'Writing' },
  { value: 'completed', label: 'Completed' },
  { value: 'partial', label: 'Partial' },
  { value: 'failed', label: 'Failed' },
]

export default function UploadsList() {
  const [searchParams, setSearchParams] = useSearchParams()

  // Pull filters from URL.
  const statusFilter = (searchParams.get('status') ?? 'all') as
    | UploadStatus
    | 'all'
  const urlSearch = searchParams.get('search') ?? ''

  // Local mirror of the search input for snappy typing.
  const [searchInput, setSearchInput] = useState(urlSearch)
  const debouncedSearch = useDebounce(searchInput, 300)

  // Push debounced search to URL (same pattern as templates list).
  useEffect(() => {
    const next = new URLSearchParams(searchParams)
    if (debouncedSearch) {
      next.set('search', debouncedSearch)
    } else {
      next.delete('search')
    }
    if (next.toString() !== searchParams.toString()) {
      setSearchParams(next, { replace: true })
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [debouncedSearch])

  function handleStatusChange(value: string) {
    const next = new URLSearchParams(searchParams)
    if (value === 'all') {
      next.delete('status')
    } else {
      next.set('status', value)
    }
    setSearchParams(next)
  }

  // Build server-side filter object from URL state.
  const filters = {
    ...(statusFilter !== 'all' && { status: statusFilter }),
  }
  const uploadsQuery = useUploads(filters)
  const templatesQuery = useTemplates()

  // Server-side filtering applies status (via queryKey).
  // Search is still client-side because the backend's GET
  // /uploads endpoint doesn't expose a filename-search param.
  // Filtering by filename here on the page is fine - it's
  // applied against the already-filtered server response.
  const fetched = uploadsQuery.data ?? []
  const filtered = debouncedSearch
    ? fetched.filter((u) =>
        u.original_filename
          .toLowerCase()
          .includes(debouncedSearch.toLowerCase())
      )
    : fetched

  // Build a templateId -> Template lookup for display.
  const templateById = new Map<string, Template>()
  for (const t of templatesQuery.data ?? []) {
    templateById.set(t.id, t)
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold text-slate-900">Uploads</h1>
        <p className="text-slate-600 mt-1">
          All file uploads across all templates.
        </p>
      </div>

      {/* Filters */}
      <div className="flex gap-3">
        <div className="relative flex-1 max-w-md">
          <Search
            size={16}
            className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400"
          />
          <Input
            placeholder="Search by filename..."
            value={searchInput}
            onChange={(e) => setSearchInput(e.target.value)}
            className="pl-9"
          />
        </div>

        <Select
          value={statusFilter}
          onValueChange={handleStatusChange}
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
      {uploadsQuery.isLoading && <TableSkeleton />}

      {uploadsQuery.error && (
        <Card>
          <CardContent className="pt-6">
            <p className="text-red-600">
              Failed to load uploads:{' '}
              {(uploadsQuery.error as Error).message}
            </p>
          </CardContent>
        </Card>
      )}

      {!uploadsQuery.isLoading && filtered.length === 0 && (
        <Card>
          <CardContent className="pt-6 text-center space-y-2">
            <p className="text-slate-700 font-medium">No uploads found.</p>
            <p className="text-sm text-slate-500">
              {statusFilter !== 'all' || debouncedSearch
                ? 'Try adjusting your filters.'
                : 'Upload a file via an Approved template to get started.'}
            </p>
          </CardContent>
        </Card>
      )}

      {filtered.length > 0 && (
        <Card>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>File</TableHead>
                <TableHead>Template</TableHead>
                <TableHead>Status</TableHead>
                <TableHead className="text-right">Rows</TableHead>
                <TableHead>Uploaded</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {filtered.map((upload) => {
                const template = templateById.get(upload.template_id)
                return (
                  <TableRow key={upload.id}>
                    <TableCell>
                      <Link
                        to={`/uploads/${upload.id}`}
                        className="font-medium text-slate-900 hover:underline"
                      >
                        {upload.original_filename}
                      </Link>
                      <div className="text-xs text-slate-500">
                        by {upload.uploaded_by}
                      </div>
                    </TableCell>
                    <TableCell>
                      {template ? (
                        <Link
                          to={`/templates/${template.id}`}
                          className="text-slate-700 hover:underline"
                        >
                          {template.display_name}
                        </Link>
                      ) : (
                        <span className="text-slate-400 text-sm">—</span>
                      )}
                    </TableCell>
                    <TableCell>
                      <UploadStatusBadge status={upload.status} />
                    </TableCell>
                    <TableCell className="text-right">
                      <RowCountCell upload={upload} />
                    </TableCell>
                    <TableCell className="text-sm text-slate-600">
                      {formatRelativeTime(upload.uploaded_at)}
                    </TableCell>
                  </TableRow>
                )
              })}
            </TableBody>
          </Table>
        </Card>
      )}
    </div>
  )
}

/**
 * Cell content for row counts. Shows "valid / total" with the
 * invalid count below in amber if non-zero.
 */
function RowCountCell({ upload }: { upload: UploadHistory }) {
  if (upload.total_rows === null) {
    return <span className="text-slate-400">—</span>
  }

  return (
    <div>
      <div className="font-medium tabular-nums">
        {(upload.valid_rows ?? 0).toLocaleString()} /{' '}
        {upload.total_rows.toLocaleString()}
      </div>
      {upload.invalid_rows !== null && upload.invalid_rows > 0 && (
        <div className="text-xs text-amber-700">
          {upload.invalid_rows.toLocaleString()} invalid
        </div>
      )}
    </div>
  )
}

/** Skeleton rows during initial load. */
function TableSkeleton() {
  return (
    <Card>
      <div className="p-4 space-y-3">
        {Array.from({ length: 5 }).map((_, i) => (
          <div key={i} className="flex gap-4 items-center">
            <Skeleton className="h-4 w-40" />
            <Skeleton className="h-4 w-48" />
            <Skeleton className="h-4 w-24" />
            <Skeleton className="h-4 w-20" />
            <Skeleton className="h-4 w-16" />
          </div>
        ))}
      </div>
    </Card>
  )
}