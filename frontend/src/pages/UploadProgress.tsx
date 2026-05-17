/**
 * Upload Progress Page.
 *
 * Polls GET /uploads/{id} every 2 seconds until status reaches
 * a terminal state. Renders a 5-step indicator showing where the
 * upload is in its lifecycle, plus row counts and any validation
 * errors.
 *
 * Polling logic lives in useUpload (refetchInterval). Validation
 * errors are fetched only after a terminal status via
 * useUploadErrors.
 */

import { Link } from 'react-router-dom'
import { useParams } from 'react-router-dom'
import {
  ArrowLeft,
  Check,
  X,
  AlertTriangle,
  Loader2,
  CheckCircle2,
} from 'lucide-react'

import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { Badge } from '@/components/ui/badge'
import { cn } from '@/lib/utils'

import { useUpload } from '@/hooks/useUpload'
import { useUploadErrors } from '@/hooks/useUploadErrors'
import { useTemplate } from '@/hooks/useTemplate'
import { formatDateTime } from '@/lib/format'
import type { UploadStatus } from '@/types'

/** All 7 backend statuses ordered by lifecycle position. */
const LIFECYCLE_STEPS: {
  status: UploadStatus
  label: string
}[] = [
  { status: 'in_progress', label: 'Receiving' },
  { status: 'file_uploaded', label: 'Uploaded' },
  { status: 'schema_validated', label: 'Schema check' },
  { status: 'constraints_checked', label: 'Validation' },
  { status: 'writing_to_catalog', label: 'Writing' },
]

const TERMINAL_STATUSES: UploadStatus[] = ['completed', 'failed', 'partial']

/**
 * Map a status to a step index in the LIFECYCLE_STEPS array.
 * Terminal statuses map to one past the last step (5).
 */
function statusToStepIndex(status: UploadStatus): number {
  const index = LIFECYCLE_STEPS.findIndex((s) => s.status === status)
  if (index >= 0) return index
  // Terminal status - all steps done
  return LIFECYCLE_STEPS.length
}

export default function UploadProgress() {
  const { id } = useParams<{ id: string }>()

  const uploadQuery = useUpload(id)
  const upload = uploadQuery.data

  // Conditionally fetch template (just for display) and errors.
  const templateQuery = useTemplate(upload?.template_id)
  const errorsQuery = useUploadErrors(id, upload?.status)

  if (uploadQuery.isLoading || !upload) {
    return <PageSkeleton />
  }

  if (uploadQuery.error) {
    return (
      <div className="space-y-4">
        <Back />
        <Card>
          <CardContent className="pt-6">
            <p className="text-red-600">
              Failed to load upload:{' '}
              {(uploadQuery.error as Error).message}
            </p>
          </CardContent>
        </Card>
      </div>
    )
  }

  const isTerminal = TERMINAL_STATUSES.includes(upload.status)
  const stepIndex = statusToStepIndex(upload.status)
  const template = templateQuery.data

  return (
    <div className="space-y-6">
      <Back />

      <div>
        <h1 className="text-3xl font-bold text-slate-900">
          Upload progress
        </h1>
        <p className="text-slate-600 mt-1">
          {upload.original_filename}
          {template && (
            <>
              {' → '}
              <Link
                to={`/templates/${template.id}`}
                className="text-slate-700 hover:underline"
              >
                {template.display_name}
              </Link>
            </>
          )}
        </p>
      </div>

      {/* Step indicator */}
      <Card>
        <CardContent className="pt-6">
          <StepIndicator
            currentStep={stepIndex}
            isTerminal={isTerminal}
            terminalStatus={isTerminal ? upload.status : null}
          />
        </CardContent>
      </Card>

      {/* Status + row counts */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <StatCard
          label="Total rows"
          value={upload.total_rows ?? '—'}
        />
        <StatCard
          label="Valid rows"
          value={upload.valid_rows ?? '—'}
          valueClass="text-green-700"
        />
        <StatCard
          label="Invalid rows"
          value={upload.invalid_rows ?? '—'}
          valueClass={
            upload.invalid_rows && upload.invalid_rows > 0
              ? 'text-amber-700'
              : 'text-slate-900'
          }
        />
      </div>

      {/* Live status indicator (polling or terminal) */}
      <StatusBanner upload={upload} />

      {/* Terminal-state error details */}
      {isTerminal && (errorsQuery.data?.length ?? 0) > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Validation errors</CardTitle>
            <CardDescription>
              Rows that failed validation. The Databricks job may
              have skipped these depending on the bad-row action
              configured on the template.
            </CardDescription>
          </CardHeader>
          <CardContent>
            {errorsQuery.isLoading ? (
              <Skeleton className="h-32 w-full" />
            ) : (
              <ErrorsTable errors={errorsQuery.data ?? []} />
            )}
          </CardContent>
        </Card>
      )}

      {/* Metadata footer */}
      <Card>
        <CardHeader>
          <CardTitle>Details</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2 text-sm">
          <div className="grid grid-cols-[180px_1fr] gap-2">
            <span className="text-slate-500">Started</span>
            <span>{formatDateTime(upload.uploaded_at)}</span>
          </div>
          {upload.completed_at && (
            <div className="grid grid-cols-[180px_1fr] gap-2">
              <span className="text-slate-500">Finished</span>
              <span>{formatDateTime(upload.completed_at)}</span>
            </div>
          )}
          <div className="grid grid-cols-[180px_1fr] gap-2">
            <span className="text-slate-500">Uploaded by</span>
            <span>{upload.uploaded_by}</span>
          </div>
          {upload.databricks_run_id && (
            <div className="grid grid-cols-[180px_1fr] gap-2">
              <span className="text-slate-500">Databricks run ID</span>
              <span>
                <code className="text-xs">{upload.databricks_run_id}</code>
              </span>
            </div>
          )}
          <div className="grid grid-cols-[180px_1fr] gap-2">
            <span className="text-slate-500">Upload ID</span>
            <span>
              <code className="text-xs">{upload.id}</code>
            </span>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}

/** Back link to the uploads list. */
function Back() {
  return (
    <Link
      to="/uploads"
      className="inline-flex items-center gap-1 text-sm text-slate-600 hover:text-slate-900"
    >
      <ArrowLeft size={14} />
      Back to uploads
    </Link>
  )
}

/** 5-step progress indicator with terminal-state coloring. */
function StepIndicator({
  currentStep,
  isTerminal,
  terminalStatus,
}: {
  currentStep: number
  isTerminal: boolean
  terminalStatus: UploadStatus | null
}) {
  return (
    <div className="flex items-center justify-between">
      {LIFECYCLE_STEPS.map((step, i) => {
        const isCompleted = i < currentStep
        const isActive = i === currentStep && !isTerminal
        const isLast = i === LIFECYCLE_STEPS.length - 1

        let circleClass = 'bg-slate-200 text-slate-500'
        let labelClass = 'text-slate-500'

        if (isTerminal) {
          // For partial: earlier steps (schema, validation) actually
          // succeeded - only the final Write step had partial success,
          // so only that step gets the amber treatment.
          // For completed: all green.
          // For failed: green up to where it failed, red on the
          // failure step.
          const isWriteStep = step.status === 'writing_to_catalog'

          if (terminalStatus === 'completed') {
            circleClass = 'bg-green-600 text-white'
            labelClass = 'text-slate-700'
          } else if (terminalStatus === 'partial') {
            // Earlier steps green - they passed. Write step amber.
            if (isWriteStep) {
              circleClass = 'bg-amber-500 text-white'
              labelClass = 'text-slate-700 font-medium'
            } else {
              circleClass = 'bg-green-600 text-white'
              labelClass = 'text-slate-700'
            }
          } else {
            // failed - red on the step where it failed, otherwise gray
            circleClass = i < currentStep
              ? 'bg-red-600 text-white'
              : 'bg-slate-200 text-slate-500'
            labelClass = 'text-slate-500'
          }
        } else if (isCompleted) {
          circleClass = 'bg-green-600 text-white'
          labelClass = 'text-slate-700'
        } else if (isActive) {
          circleClass = 'bg-blue-600 text-white animate-pulse'
          labelClass = 'text-slate-900 font-medium'
        }

        return (
          <div key={step.status} className="flex items-center flex-1">
            <div className="flex flex-col items-center">
              <div
                className={cn(
                  'w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium',
                  circleClass
                )}
              >
                {isCompleted || (isTerminal && terminalStatus === 'completed')
                  ? <Check size={16} />
                  : i + 1}
              </div>
              <div className={cn('text-xs mt-1 text-center', labelClass)}>
                {step.label}
              </div>
            </div>
            {!isLast && (
              <div
                className={cn(
                  'flex-1 h-px mx-2 -mt-4',
                  i < currentStep ? 'bg-green-600' : 'bg-slate-200'
                )}
              />
            )}
          </div>
        )
      })}
    </div>
  )
}

/** A small stats card showing label + value. */
function StatCard({
  label,
  value,
  valueClass,
}: {
  label: string
  value: number | string
  valueClass?: string
}) {
  return (
    <Card>
      <CardContent className="pt-6">
        <div className="text-xs uppercase tracking-wide text-slate-500">
          {label}
        </div>
        <div
          className={cn(
            'text-2xl font-bold text-slate-900 mt-1',
            valueClass
          )}
        >
          {typeof value === 'number' ? value.toLocaleString() : value}
        </div>
      </CardContent>
    </Card>
  )
}

/**
 * Banner above the metadata showing live status.
 *
 * Polling state when in flight; success/error variants for
 * terminal states.
 */
function StatusBanner({
  upload,
}: {
  upload: { status: UploadStatus; error_summary: string | null }
}) {
  if (upload.status === 'completed') {
    return (
      <Card className="bg-green-50 border-green-200">
        <CardContent className="pt-6 flex gap-3">
          <CheckCircle2 className="text-green-600 shrink-0" size={20} />
          <div className="text-sm text-green-900">
            <p className="font-medium">Upload completed successfully</p>
            <p>All rows have been written to the target table.</p>
          </div>
        </CardContent>
      </Card>
    )
  }

  if (upload.status === 'partial') {
    return (
      <Card className="bg-amber-50 border-amber-200">
        <CardContent className="pt-6 flex gap-3">
          <AlertTriangle className="text-amber-600 shrink-0" size={20} />
          <div className="text-sm text-amber-900">
            <p className="font-medium">Upload partially completed</p>
            <p>
              {upload.error_summary ||
                'Some rows failed validation and thus were not written to the target table. See below to find rows that were dropped.'}
            </p>
          </div>
        </CardContent>
      </Card>
    )
  }

  if (upload.status === 'failed') {
    return (
      <Card className="bg-red-50 border-red-200">
        <CardContent className="pt-6 flex gap-3">
          <X className="text-red-600 shrink-0" size={20} />
          <div className="text-sm text-red-900">
            <p className="font-medium">Upload failed</p>
            <p>
              {upload.error_summary ||
                'The upload could not be processed. See errors below.'}
            </p>
          </div>
        </CardContent>
      </Card>
    )
  }

  // Non-terminal - polling
  return (
    <Card className="bg-blue-50 border-blue-200">
      <CardContent className="pt-6 flex items-center gap-3">
        <Loader2 className="text-blue-600 animate-spin shrink-0" size={20} />
        <div className="text-sm text-blue-900">
          <p className="font-medium">Upload in progress</p>
          <p>
            Status: <code>{upload.status}</code>. Refreshing every 2 seconds...
          </p>
        </div>
      </CardContent>
    </Card>
  )
}

/** Tabular view of validation errors. */
function ErrorsTable({
  errors,
}: {
  errors: Array<{
    id: string
    row_number: number
    column_name: string
    error_type: string
    error_message: string
    raw_value: string | null
  }>
}) {
  // Cap displayed rows to avoid hanging the browser on huge error lists.
  const MAX_DISPLAY = 100
  const displayed = errors.slice(0, MAX_DISPLAY)
  const truncated = errors.length > MAX_DISPLAY

  return (
    <div className="space-y-2">
      {truncated && (
        <p className="text-xs text-slate-500">
          Showing first {MAX_DISPLAY} of {errors.length} errors.
        </p>
      )}
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead className="w-16">Row</TableHead>
            <TableHead className="w-32">Column</TableHead>
            <TableHead className="w-32">Type</TableHead>
            <TableHead>Message</TableHead>
            <TableHead className="w-40">Value</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {displayed.map((err) => (
            <TableRow key={err.id}>
              <TableCell>{err.row_number}</TableCell>
              <TableCell>
                <code className="text-xs">{err.column_name}</code>
              </TableCell>
              <TableCell>
                <Badge variant="outline" className="text-xs">
                  {err.error_type}
                </Badge>
              </TableCell>
              <TableCell className="text-sm">{err.error_message}</TableCell>
              <TableCell>
                <code className="text-xs text-slate-600 truncate block">
                  {err.raw_value ?? '—'}
                </code>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  )
}

/** Skeleton while the upload fetch is in flight. */
function PageSkeleton() {
  return (
    <div className="space-y-6">
      <Skeleton className="h-4 w-32" />
      <Skeleton className="h-8 w-64" />
      <Skeleton className="h-32 w-full" />
      <div className="grid grid-cols-3 gap-4">
        <Skeleton className="h-20" />
        <Skeleton className="h-20" />
        <Skeleton className="h-20" />
      </div>
    </div>
  )
}