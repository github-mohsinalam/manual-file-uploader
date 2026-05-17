/**
 * Template Create Wizard - Step 4 (Review + Submit).
 *
 * Final step of the create wizard. Shows a read-only summary
 * of everything the user has entered, then lets them submit
 * for approval.
 *
 * On submit:
 *   - POST /templates/{id}/submit transitions the template
 *     from Draft to Pending Approval
 *   - Backend creates approval rows + tokens
 *   - Backend dispatches approval-request emails (async)
 *   - We navigate to the detail page so the user sees the
 *     new status
 *
 * To edit anything, the user clicks Back. This step is purely
 * "confirm and go".
 */

import { useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { AlertCircle, AlertTriangle, Check } from 'lucide-react'

import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'

import { WizardShell } from '@/components/wizard/WizardShell'
import { useTemplate } from '@/hooks/useTemplate'
import { useTemplateColumns } from '@/hooks/useTemplateColumns'
import { useTemplateReviewers } from '@/hooks/useTemplateReviewers'
import { useDomains } from '@/hooks/useDomains'
import { submitTemplate } from '@/services/templates'
import { toApiError } from '@/lib/api/client'

export default function TemplateCreateReview() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const queryClient = useQueryClient()

  // Confirmation dialog visibility.
  const [confirmOpen, setConfirmOpen] = useState(false)

  // Fetch everything we need to display.
  const templateQuery = useTemplate(id)
  const columnsQuery = useTemplateColumns(id)
  const reviewersQuery = useTemplateReviewers(id)
  const domainsQuery = useDomains()

  // Mutation: submit template for approval.
  const submitMutation = useMutation({
    mutationFn: () => submitTemplate(id!),
    onSuccess: () => {
      // Invalidate caches so the detail page and list both
      // show the new status.
      queryClient.invalidateQueries({ queryKey: ['template', id] })
      queryClient.invalidateQueries({ queryKey: ['templates'] })

      // Close the confirmation dialog.
      setConfirmOpen(false)

      // Navigate to the detail page so the user sees the
      // template's new Pending Approval status.
      navigate(`/templates/${id}`)
    },
  })

  // Wait for the main template fetch before deciding what to render.
  if (templateQuery.isLoading || !templateQuery.data) {
    return <ReviewSkeleton />
  }

  if (templateQuery.error) {
    return (
      <WizardShell currentStep={5} title="Review and submit">
        <Card>
          <CardContent className="pt-6">
            <p className="text-red-600">
              Failed to load template:{' '}
              {(templateQuery.error as Error).message}
            </p>
          </CardContent>
        </Card>
      </WizardShell>
    )
  }

  const template = templateQuery.data
  const columns = columnsQuery.data ?? []
  const reviewers = reviewersQuery.data ?? []
  const domain = domainsQuery.data?.find(
    (d) => d.id === template.domain_id
  )

  const hasRequiredReviewer = reviewers.some(
    (r) => r.reviewer_type === 'required'
  )

  // Check whether the template is ready for submission.
  // The backend will reject if these aren't met, but we also
  // show pre-flight warnings so the user knows what's missing.
  const canSubmit = columns.length > 0 && hasRequiredReviewer

  const submitError = submitMutation.error
    ? toApiError(submitMutation.error)
    : null

  return (
    <WizardShell
      currentStep={5}
      title="Review and submit"
      description="Confirm everything is correct. Once submitted, the template enters the approval workflow."
    >
      {/* Basics summary */}
      <Card>
        <CardHeader>
          <CardTitle>Basics</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <SummaryRow label="Technical name">
            <code className="text-sm">{template.name}</code>
          </SummaryRow>
          <SummaryRow label="Display name">
            {template.display_name}
          </SummaryRow>
          <SummaryRow label="Domain">
            {domain?.name ?? '-'}{' '}
            {domain && (
              <span className="text-slate-500 text-sm">
                (schema: <code>{domain.uc_schema_name}</code>)
              </span>
            )}
          </SummaryRow>
          <SummaryRow label="Target table">
            <code className="text-sm">
              {template.fully_qualified_name}
            </code>
          </SummaryRow>
          {template.description && (
            <SummaryRow label="Description">
              {template.description}
            </SummaryRow>
          )}
        </CardContent>
      </Card>

      {/* Columns summary */}
      <Card>
        <CardHeader>
          <CardTitle>Columns ({columns.length})</CardTitle>
          <CardDescription>
            Schema for the target Unity Catalog table.
          </CardDescription>
        </CardHeader>
        <CardContent>
          {columnsQuery.isLoading && (
            <Skeleton className="h-32 w-full" />
          )}

          {columns.length === 0 && !columnsQuery.isLoading && (
            <p className="text-sm text-amber-700">
              No columns configured. Go back and add at least one
              column before submitting.
            </p>
          )}

          {columns.length > 0 && (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Column</TableHead>
                  <TableHead>Type</TableHead>
                  <TableHead>Flags</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {columns.map((col) => (
                  <TableRow key={col.id}>
                    <TableCell className="font-medium">
                      {col.column_name}
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
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      {/* Reviewers summary */}
      <Card>
        <CardHeader>
          <CardTitle>Reviewers ({reviewers.length})</CardTitle>
          <CardDescription>
            People who will review this template before activation.
          </CardDescription>
        </CardHeader>
        <CardContent>
          {reviewersQuery.isLoading && (
            <Skeleton className="h-24 w-full" />
          )}

          {reviewers.length === 0 && !reviewersQuery.isLoading && (
            <p className="text-sm text-amber-700">
              No reviewers configured. Go back and add at least one
              required reviewer before submitting.
            </p>
          )}

          {reviewers.length > 0 && !hasRequiredReviewer && (
            <p className="text-sm text-amber-700 mb-3">
              No required reviewers. At least one reviewer must be
              marked Required before submitting.
            </p>
          )}

          {reviewers.length > 0 && (
            <ul className="divide-y divide-slate-200">
              {reviewers.map((rev) => (
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
                      rev.reviewer_type === 'required'
                        ? 'default'
                        : 'outline'
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

      {/* What happens next */}
      <Card className="bg-blue-50 border-blue-200">
        <CardContent className="pt-6">
          <div className="flex gap-3">
            <AlertCircle
              className="text-blue-600 shrink-0 mt-0.5"
              size={20}
            />
            <div className="space-y-2 text-sm text-blue-900">
              <p className="font-medium">What happens after you submit:</p>
              <ul className="list-disc list-inside space-y-1 ml-2">
                <li>The template status changes to Pending Approval</li>
                <li>
                  All reviewers receive an email with approve/reject links
                </li>
                <li>
                  Once all required reviewers approve, the Unity Catalog
                  table is created automatically
                </li>
                <li>
                  If any required reviewer rejects, the template returns
                  to Draft status
                </li>
              </ul>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Pre-submit error from backend */}
      {submitError && (
        <Card className="bg-red-50 border-red-200">
          <CardContent className="pt-6">
            <div className="flex gap-3">
              <AlertTriangle
                className="text-red-600 shrink-0 mt-0.5"
                size={20}
              />
              <div className="space-y-1 text-sm">
                <p className="font-medium text-red-900">
                  Submit failed
                </p>
                <p className="text-red-800">{submitError.message}</p>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Action buttons */}
      <div className="flex justify-between">
        <Button
          type="button"
          variant="outline"
          onClick={() => navigate(`/templates/new/${id}/reviewers`)}
          disabled={submitMutation.isPending}
        >
          Back
        </Button>
        <Button
          onClick={() => setConfirmOpen(true)}
          disabled={!canSubmit || submitMutation.isPending}
        >
          <Check size={14} />
          Submit for Approval
        </Button>
      </div>

      {/* Confirmation dialog */}
      <AlertDialog open={confirmOpen} onOpenChange={setConfirmOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Submit this template?</AlertDialogTitle>
            <AlertDialogDescription asChild>
              <div className="space-y-2">
                <p>
                  This will send approval request emails to all{' '}
                  {reviewers.length} reviewers and move the template
                  to <strong>Pending Approval</strong>.
                </p>
                <p>
                  Once submitted, you cannot edit the template until
                  it is either approved or returned to Draft after
                  a rejection.
                </p>
              </div>
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel disabled={submitMutation.isPending}>
              Cancel
            </AlertDialogCancel>
            <AlertDialogAction
              onClick={() => submitMutation.mutate()}
              disabled={submitMutation.isPending}
            >
              {submitMutation.isPending
                ? 'Submitting...'
                : 'Yes, submit'}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </WizardShell>
  )
}

/**
 * Two-column label/value row for the summary cards.
 */
function SummaryRow({
  label,
  children,
}: {
  label: string
  children: React.ReactNode
}) {
  return (
    <div className="grid grid-cols-[140px_1fr] gap-3 items-baseline">
      <div className="text-xs uppercase tracking-wide text-slate-500">
        {label}
      </div>
      <div className="text-sm text-slate-900">{children}</div>
    </div>
  )
}

/**
 * Loading skeleton shown while the main template fetch is in flight.
 */
function ReviewSkeleton() {
  return (
    <WizardShell currentStep={5} title="Review and submit">
      <Skeleton className="h-32 w-full" />
      <Skeleton className="h-48 w-full" />
      <Skeleton className="h-32 w-full" />
    </WizardShell>
  )
}