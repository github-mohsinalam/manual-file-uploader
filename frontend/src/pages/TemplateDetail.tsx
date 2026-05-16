/**
 * Template detail page - read-only view of a single template.
 *
 * Stacked sections:
 *   1. Basics
 *   2. Columns
 *   3. Reviewers
 *   4. Approval activity (placeholder)
 *
 * Action buttons in the header are status-conditional. Most
 * click handlers are placeholders for now (alert popups);
 * later tasks wire them to real mutations.
 */

import { useParams, useNavigate } from 'react-router-dom'
import {
  ArrowLeft,
  Pencil,
  Send,
  Trash2,
  Upload,
  GitBranch,
  RotateCcw,
  AlertTriangle,
} from 'lucide-react'

import { Button } from '@/components/ui/button'
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import { Separator } from '@/components/ui/separator'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { Badge } from '@/components/ui/badge'

import { StatusBadge } from '@/components/templates/StatusBadge'
import { useTemplate } from '@/hooks/useTemplate'
import { useTemplateColumns } from '@/hooks/useTemplateColumns'
import { useTemplateReviewers } from '@/hooks/useTemplateReviewers'
import { useDomains } from '@/hooks/useDomains'
import { formatDateTime } from '@/lib/format'
import type { Template } from '@/types'

export default function TemplateDetail() {
  const { id } = useParams()
  const navigate = useNavigate()

  // Three queries fire in parallel - TanStack handles the
  // concurrency. Each section handles its own loading/error.
  const templateQuery = useTemplate(id)
  const columnsQuery = useTemplateColumns(id)
  const reviewersQuery = useTemplateReviewers(id)

  // Domains are needed to resolve the template's domain_id
  // to a domain name. Cached from earlier visits to /domains.
  const domainsQuery = useDomains()

  // Hard error - template fetch failed (e.g. 404 on bad ID).
  if (templateQuery.error) {
    return (
      <div className="space-y-4">
        <BackLink />
        <Card>
          <CardContent className="pt-6 space-y-2">
            <p className="text-red-600 font-medium">
              Failed to load template
            </p>
            <p className="text-sm text-slate-600">
              {(templateQuery.error as Error).message}
            </p>
          </CardContent>
        </Card>
      </div>
    )
  }

  // Loading - block the page until the main template arrives.
  if (templateQuery.isLoading || !templateQuery.data) {
    return <DetailSkeleton />
  }

  const template = templateQuery.data
  const domain = domainsQuery.data?.find(
    (d) => d.id === template.domain_id
  )

  return (
    <div className="space-y-6">
      <BackLink />

      {/* Header */}
      <div className="flex items-start justify-between gap-4">
        <div className="space-y-1">
          <div className="flex items-center gap-3 flex-wrap">
            <h1 className="text-3xl font-bold text-slate-900">
              {template.display_name}
            </h1>
            <StatusBadge status={template.status} />
          </div>
          <p className="text-slate-600">
            <code className="text-sm">{template.fully_qualified_name}</code>
          </p>
        </div>

        <ActionButtons template={template} onNavigate={navigate} />
      </div>

      {/* Section 1 - Basics */}
      <Card>
        <CardHeader>
          <CardTitle>Basics</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <Field label="Technical name">{template.name}</Field>
            <Field label="Domain">{domain?.name ?? '-'}</Field>
            <Field label="Version">v{template.version}</Field>
            <Field label="Created by">{template.created_by}</Field>
            <Field label="Created at">
              {formatDateTime(template.created_at)}
            </Field>
            <Field label="Updated at">
              {formatDateTime(template.updated_at)}
            </Field>
            <Field label="Approved at">
              {formatDateTime(template.approved_at)}
            </Field>
            <Field label="Reader group">
              {template.reader_group ?? '-'}
            </Field>
          </div>

          <Separator />

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <Field label="File format">
              {template.file_format.toUpperCase()}
            </Field>
            <Field label="Delimiter">
              {template.delimiter ? `"${template.delimiter}"` : '-'}
            </Field>
            <Field label="Encoding">{template.encoding}</Field>
            <Field label="Write mode">{template.write_mode}</Field>
            <Field label="Bad row threshold">
              {template.bad_row_threshold}%
            </Field>
            <Field label="Bad row action">{template.bad_row_action}</Field>
          </div>

          {template.description && (
            <>
              <Separator />
              <Field label="Description">{template.description}</Field>
            </>
          )}
        </CardContent>
      </Card>

      {/* Section 2 - Columns */}
      <Card>
        <CardHeader>
          <CardTitle>Columns</CardTitle>
          <CardDescription>
            Schema and constraints for the target Unity Catalog table.
          </CardDescription>
        </CardHeader>
        <CardContent>
          {columnsQuery.isLoading && (
            <div className="space-y-2">
              {Array.from({ length: 3 }).map((_, i) => (
                <Skeleton key={i} className="h-8 w-full" />
              ))}
            </div>
          )}

          {columnsQuery.error && (
            <p className="text-sm text-red-600">
              Failed to load columns:{' '}
              {(columnsQuery.error as Error).message}
            </p>
          )}

          {columnsQuery.data && columnsQuery.data.length === 0 && (
            <p className="text-sm text-slate-500">
              No columns configured yet.
            </p>
          )}

          {columnsQuery.data && columnsQuery.data.length > 0 && (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Column</TableHead>
                  <TableHead>Type</TableHead>
                  <TableHead>Flags</TableHead>
                  <TableHead>Description</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {columnsQuery.data.map((col) => (
                  <TableRow key={col.id}>
                    <TableCell>
                      <div className="font-medium">{col.column_name}</div>
                      {col.display_name && (
                        <div className="text-xs text-slate-500">
                          {col.display_name}
                        </div>
                      )}
                    </TableCell>
                    <TableCell>
                      <code className="text-sm">{col.data_type}</code>
                    </TableCell>
                    <TableCell>
                      <div className="flex gap-1 flex-wrap">
                        {!col.is_nullable && (
                          <Badge variant="outline">NOT NULL</Badge>
                        )}
                        {col.is_unique && (
                          <Badge variant="outline">UNIQUE</Badge>
                        )}
                        {col.is_pii && (
                          <Badge
                            variant="outline"
                            className="bg-amber-50 text-amber-800 border-amber-200"
                          >
                            PII
                          </Badge>
                        )}
                        {!col.is_included && (
                          <Badge
                            variant="outline"
                            className="bg-slate-100 text-slate-500"
                          >
                            excluded
                          </Badge>
                        )}
                      </div>
                    </TableCell>
                    <TableCell className="text-sm text-slate-600">
                      {col.description ?? '-'}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      {/* Section 3 - Reviewers */}
      <Card>
        <CardHeader>
          <CardTitle>Reviewers</CardTitle>
          <CardDescription>
            Required reviewers must all approve before the template is activated.
          </CardDescription>
        </CardHeader>
        <CardContent>
          {reviewersQuery.isLoading && (
            <div className="space-y-2">
              {Array.from({ length: 2 }).map((_, i) => (
                <Skeleton key={i} className="h-8 w-full" />
              ))}
            </div>
          )}

          {reviewersQuery.error && (
            <p className="text-sm text-red-600">
              Failed to load reviewers:{' '}
              {(reviewersQuery.error as Error).message}
            </p>
          )}

          {reviewersQuery.data && reviewersQuery.data.length === 0 && (
            <p className="text-sm text-slate-500">
              No reviewers assigned yet.
            </p>
          )}

          {reviewersQuery.data && reviewersQuery.data.length > 0 && (
            <ul className="divide-y divide-slate-200">
              {reviewersQuery.data.map((rev) => (
                <li
                  key={rev.id}
                  className="py-3 flex items-center justify-between"
                >
                  <div>
                    <div className="font-medium">{rev.reviewer_name}</div>
                    <div className="text-sm text-slate-500">
                      {rev.reviewer_email}
                    </div>
                  </div>
                  <Badge
                    variant={
                      rev.reviewer_type === 'required' ? 'default' : 'outline'
                    }
                  >
                    {rev.reviewer_type}
                  </Badge>
                </li>
              ))}
            </ul>
          )}
        </CardContent>
      </Card>

      {/* Section 4 - Approval activity (placeholder) */}
      <Card>
        <CardHeader>
          <CardTitle>Approval activity</CardTitle>
          <CardDescription>
            Reviewer decisions on this template.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-slate-500">
            Approval timeline will appear here in a future task.
          </p>
        </CardContent>
      </Card>
    </div>
  )
}

/**
 * Back link to the list page.
 *
 * Uses navigate(-1) so the previous URL (with filters) is
 * restored on Back. Falls back to /templates if the user
 * landed here directly (no history to go back to).
 */
function BackLink() {
  const navigate = useNavigate()

  function handleBack() {
    if (window.history.length > 1) {
      navigate(-1)
    } else {
      navigate('/templates')
    }
  }

  return (
    <button
      onClick={handleBack}
      className="inline-flex items-center gap-1 text-sm text-slate-600 hover:text-slate-900 cursor-pointer"
    >
      <ArrowLeft size={14} />
      Back
    </button>
  )
}

/**
 * A labeled value pair shown in the basics section.
 * Just a styling wrapper to keep markup readable.
 */
function Field({
  label,
  children,
}: {
  label: string
  children: React.ReactNode
}) {
  return (
    <div>
      <div className="text-xs uppercase tracking-wide text-slate-500 mb-1">
        {label}
      </div>
      <div className="text-sm text-slate-900">{children}</div>
    </div>
  )
}

/**
 * Action buttons in the page header. Visibility depends on
 * template.status. Click handlers are placeholders for now.
 */
function ActionButtons({
  template,
  onNavigate,
}: {
  template: Template
  onNavigate: (path: string) => void
}) {
  const status = template.status

  return (
    <div className="flex gap-2 shrink-0 flex-wrap justify-end">
      {status === 'Draft' && (
        <>
          <Button
            variant="outline"
            onClick={() =>
              onNavigate(`/templates/new/${template.id}`)
            }
          >
            <Pencil size={14} />
            Edit
        </Button>
          <Button
            onClick={() =>
              onNavigate(`/templates/new/${template.id}/review`)
            }
          >
            <Send size={14} />
            Submit for Approval
          </Button>
          <Button
            variant="destructive"
            onClick={() =>
              alert('Delete confirmation lands in a future task.')
            }
          >
            <Trash2 size={14} />
            Delete
          </Button>
        </>
      )}

      {status === 'Approved' && (
        <>
          <Button onClick={() => onNavigate(`/templates/${template.id}/upload`)}>
            <Upload size={14} />
            Upload File
          </Button>
          <Button
            variant="outline"
            onClick={() =>
              alert('New-version flow lands in a future task.')
            }
          >
            <GitBranch size={14} />
            New Version
          </Button>
        </>
      )}

      {status === 'Rejected' && (
        <Button
          variant="outline"
          onClick={() =>
            alert(
              'Rejected templates return to Draft - flow lands in a future task.'
            )
          }
        >
          <Pencil size={14} />
          Edit
        </Button>
      )}

      {status === 'DDL Failed' && (
        <Button
          onClick={() => alert('Retry DDL flow lands in a future task.')}
        >
          <RotateCcw size={14} />
          Retry DDL
        </Button>
      )}

      {(status === 'Pending Approval' || status === 'Pending DDL') && (
        <div className="flex items-center gap-2 text-sm text-slate-500">
          <AlertTriangle size={14} />
          Waiting on workflow
        </div>
      )}
    </div>
  )
}

/** Full-page skeleton shown while the template is loading. */
function DetailSkeleton() {
  return (
    <div className="space-y-6">
      <Skeleton className="h-4 w-32" />
      <div className="space-y-2">
        <Skeleton className="h-8 w-64" />
        <Skeleton className="h-4 w-96" />
      </div>
      {Array.from({ length: 3 }).map((_, i) => (
        <Card key={i}>
          <CardHeader>
            <Skeleton className="h-5 w-32" />
          </CardHeader>
          <CardContent className="space-y-2">
            <Skeleton className="h-4 w-full" />
            <Skeleton className="h-4 w-4/5" />
            <Skeleton className="h-4 w-3/5" />
          </CardContent>
        </Card>
      ))}
    </div>
  )
}