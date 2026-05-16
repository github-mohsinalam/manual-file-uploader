/**
 * Public approval page.
 *
 * Reviewers land here from email links in the form:
 *   /approve?token=XYZ&action=approve
 *   /approve?token=XYZ&action=reject
 *
 * NO LOGIN REQUIRED - the token is the credential.
 *
 * The page renders one of five states:
 *   - Loading: fetching token info
 *   - Review form: token valid, decision not yet made
 *   - Submission in progress: decision being recorded
 *   - Confirmation: decision recorded (this session)
 *   - Already decided: 410 caught - show thank-you with prior decision
 *   - Invalid token: 404 caught
 *   - Generic error: anything else
 *
 * The page lives outside the app Layout - no sidebar, no nav.
 */

import { useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { useMutation, useQuery } from '@tanstack/react-query'
import { useForm } from 'react-hook-form'
import { Check, X, AlertTriangle, Loader2 } from 'lucide-react'

import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import { Badge } from '@/components/ui/badge'
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import {
  Field,
  FieldDescription,
  FieldLabel,
} from '@/components/ui/field'

import {
  fetchApprovalInfo,
  submitApprovalDecision,
  type ApprovalTokenInfo,
} from '@/services/approvals'
import { toApiError } from '@/lib/api/client'
import { formatDateTime } from '@/lib/format'

export default function ApprovalPage() {
  const [searchParams] = useSearchParams()
  const token = searchParams.get('token')
  const initialAction = searchParams.get('action') as
    | 'approve'
    | 'reject'
    | null

  // The action the reviewer is currently choosing. Starts from
  // the URL hint, but the user can flip it before confirming.
  const [decision, setDecision] = useState<'approve' | 'reject'>(
    initialAction === 'reject' ? 'reject' : 'approve'
  )

  // Form for the optional comment.
  const form = useForm<{ comment: string }>({
    defaultValues: { comment: '' },
  })

  // Token info query - one fetch on mount, no retry on errors
  // since 404 and 410 are meaningful states not transient failures.
  const infoQuery = useQuery<ApprovalTokenInfo>({
    queryKey: ['approval-token', token],
    queryFn: () => fetchApprovalInfo(token!),
    enabled: Boolean(token),
    retry: false,
  })

  // Mutation to submit the decision.
  const submitMutation = useMutation({
    mutationFn: (vars: { decision: 'approve' | 'reject'; comment: string }) =>
      submitApprovalDecision(token!, vars.decision, vars.comment),
  })

  function handleSubmit(values: { comment: string }) {
    submitMutation.mutate({
      decision,
      comment: values.comment,
    })
  }

  // -----------------------------------------------------------
  // Render branches - check most-specific cases first.
  // -----------------------------------------------------------

  // No token at all in URL
  if (!token) {
    return (
      <CenteredCard variant="error">
        <Title>Missing token</Title>
        <p className="text-sm text-slate-600">
          This page expects a token in the URL. The link you
          followed appears to be incomplete.
        </p>
      </CenteredCard>
    )
  }

  // Submission succeeded (this session)
  if (submitMutation.isSuccess) {
    return (
      <CenteredCard variant="success">
        <SuccessIcon decision={decision} />
        <Title>
          {decision === 'approve'
            ? 'Approval recorded'
            : 'Rejection recorded'}
        </Title>
        <p className="text-sm text-slate-700">
          Thank you. Your decision has been saved.
        </p>
        <p className="text-sm text-slate-600">
          {submitMutation.data.message}
        </p>
      </CenteredCard>
    )
  }

  // Error branch from the fetch
  if (infoQuery.error) {
    const apiError = toApiError(infoQuery.error)

    if (apiError.status === 410) {
      // Already decided - the message tells us what they decided
      return (
        <CenteredCard variant="success">
          <SuccessIcon decision="approve" />
          <Title>Already recorded</Title>
          <p className="text-sm text-slate-700">{apiError.message}</p>
          <p className="text-xs text-slate-500 mt-4">
            You can safely close this page.
          </p>
        </CenteredCard>
      )
    }

    if (apiError.status === 404) {
      return (
        <CenteredCard variant="error">
          <Title>Invalid approval link</Title>
          <p className="text-sm text-slate-700">
            This approval link doesn't exist or has been removed.
          </p>
          <p className="text-xs text-slate-500 mt-4">
            If you believe this is an error, please contact the
            person who sent you this link.
          </p>
        </CenteredCard>
      )
    }

    // Anything else
    return (
      <CenteredCard variant="error">
        <Title>Unable to load approval</Title>
        <p className="text-sm text-slate-700">{apiError.message}</p>
      </CenteredCard>
    )
  }

  // Loading state
  if (infoQuery.isLoading || !infoQuery.data) {
    return (
      <CenteredCard>
        <div className="flex items-center justify-center gap-2 text-slate-500 text-sm">
          <Loader2 className="animate-spin" size={16} />
          Loading approval details...
        </div>
      </CenteredCard>
    )
  }

  // Main render - review form
  const info = infoQuery.data
  const submitError = submitMutation.error
    ? toApiError(submitMutation.error)
    : null

  return (
    <div className="min-h-screen bg-slate-50 py-12 px-4">
      <div className="max-w-2xl mx-auto space-y-6">
        {/* Header */}
        <div className="text-center space-y-2">
          <h1 className="text-3xl font-bold text-slate-900">
            Template Approval
          </h1>
          <p className="text-slate-600">
            Hello {info.reviewer_name}, please review the template
            below and record your decision.
          </p>
        </div>

        {/* Template details */}
        <Card>
          <CardHeader>
            <div className="flex items-start justify-between gap-3">
              <div>
                <CardTitle>{info.template.display_name}</CardTitle>
                <CardDescription>
                  <code className="text-xs">
                    {info.template.fully_qualified_name}
                  </code>
                </CardDescription>
              </div>
              <Badge
                variant={
                  info.reviewer_type === 'required' ? 'default' : 'outline'
                }
              >
                {info.reviewer_type === 'required'
                  ? 'Required reviewer'
                  : 'Optional reviewer'}
              </Badge>
            </div>
          </CardHeader>
          <CardContent className="space-y-3">
            <DetailRow label="Technical name">
              <code className="text-sm">{info.template.name}</code>
            </DetailRow>
            <DetailRow label="Domain">{info.template.domain_name}</DetailRow>
            {info.template.description && (
              <DetailRow label="Description">
                {info.template.description}
              </DetailRow>
            )}
            <DetailRow label="Link expires">
              {formatDateTime(info.token_expires_at)}
            </DetailRow>
          </CardContent>
        </Card>

        {/* Decision form */}
        <Card>
          <CardHeader>
            <CardTitle>Your decision</CardTitle>
            <CardDescription>
              Choose Approve or Reject. You may add an optional
              comment that the template creator will see.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={form.handleSubmit(handleSubmit)} className="space-y-6">
              {/* Decision toggle */}
              <div className="grid grid-cols-2 gap-3">
                <button
                  type="button"
                  onClick={() => setDecision('approve')}
                  disabled={submitMutation.isPending}
                  className={
                    decision === 'approve'
                      ? 'flex items-center justify-center gap-2 py-3 rounded-md border-2 border-green-600 bg-green-50 text-green-800 font-medium transition-colors'
                      : 'flex items-center justify-center gap-2 py-3 rounded-md border-2 border-slate-200 bg-white text-slate-700 hover:border-slate-300 transition-colors'
                  }
                >
                  <Check size={18} />
                  Approve
                </button>
                <button
                  type="button"
                  onClick={() => setDecision('reject')}
                  disabled={submitMutation.isPending}
                  className={
                    decision === 'reject'
                      ? 'flex items-center justify-center gap-2 py-3 rounded-md border-2 border-red-600 bg-red-50 text-red-800 font-medium transition-colors'
                      : 'flex items-center justify-center gap-2 py-3 rounded-md border-2 border-slate-200 bg-white text-slate-700 hover:border-slate-300 transition-colors'
                  }
                >
                  <X size={18} />
                  Reject
                </button>
              </div>

              {/* Comment */}
              <Field>
                <FieldLabel htmlFor="comment">
                  Comment{' '}
                  <span className="text-slate-400 font-normal">
                    (optional)
                  </span>
                </FieldLabel>
                <Textarea
                  id="comment"
                  placeholder={
                    decision === 'approve'
                      ? 'Optional comment...'
                      : 'Why are you rejecting? This helps the creator revise.'
                  }
                  rows={3}
                  {...form.register('comment', {
                    maxLength: {
                      value: 500,
                      message: 'At most 500 characters',
                    },
                  })}
                  disabled={submitMutation.isPending}
                />
                <FieldDescription>
                  The template creator will see this comment in their
                  notification email.
                </FieldDescription>
              </Field>

              {submitError && (
                <div className="flex gap-2 rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-800">
                  <AlertTriangle size={16} className="shrink-0 mt-0.5" />
                  <span>{submitError.message}</span>
                </div>
              )}

              <Button
                type="submit"
                disabled={submitMutation.isPending}
                className="w-full"
              >
                {submitMutation.isPending
                  ? 'Submitting...'
                  : decision === 'approve'
                    ? 'Confirm Approval'
                    : 'Confirm Rejection'}
              </Button>
            </form>
          </CardContent>
        </Card>

        <p className="text-center text-xs text-slate-500">
          This approval link is unique to you. Closing this page
          before confirming does not record any decision.
        </p>
      </div>
    </div>
  )
}

/**
 * Wrapper for the "non-form" render states (loading, errors,
 * thank-you). Just centers a single card on the page.
 */
function CenteredCard({
  variant,
  children,
}: {
  variant?: 'success' | 'error'
  children: React.ReactNode
}) {
  const borderClass =
    variant === 'success'
      ? 'border-green-200'
      : variant === 'error'
      ? 'border-red-200'
      : 'border-slate-200'

  return (
    <div className="min-h-screen bg-slate-50 flex items-center justify-center p-4">
      <Card className={`max-w-md w-full ${borderClass}`}>
        <CardContent className="pt-8 pb-6 space-y-3 text-center">
          {children}
        </CardContent>
      </Card>
    </div>
  )
}

function Title({ children }: { children: React.ReactNode }) {
  return <h1 className="text-2xl font-bold text-slate-900">{children}</h1>
}

function SuccessIcon({ decision }: { decision: 'approve' | 'reject' }) {
  if (decision === 'approve') {
    return (
      <div className="mx-auto w-16 h-16 rounded-full bg-green-100 flex items-center justify-center">
        <Check size={32} className="text-green-600" />
      </div>
    )
  }
  return (
    <div className="mx-auto w-16 h-16 rounded-full bg-red-100 flex items-center justify-center">
      <X size={32} className="text-red-600" />
    </div>
  )
}

function DetailRow({
  label,
  children,
}: {
  label: string
  children: React.ReactNode
}) {
  return (
    <div className="grid grid-cols-[120px_1fr] gap-3 items-baseline">
      <div className="text-xs uppercase tracking-wide text-slate-500">
        {label}
      </div>
      <div className="text-sm text-slate-900">{children}</div>
    </div>
  )
}