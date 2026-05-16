/**
 * ApprovalTimeline - renders the approval activity for a template.
 *
 * One card per approval row, showing:
 *   - Reviewer name + email
 *   - Their role (required / optional)
 *   - State: approved (green), rejected (red), or pending (gray)
 *   - When they acted (or "waiting" if not yet)
 *   - Their comment, if any
 *
 * Used inside the template detail page's "Approval activity" card.
 * Handles three top-level states: loading, error, populated.
 *
 * For Draft templates the timeline is empty; the parent renders
 * a different message in that case rather than this component.
 */

import { Check, X, Clock } from 'lucide-react'

import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import { cn } from '@/lib/utils'
import { formatDateTime } from '@/lib/format'
import type { TemplateApproval } from '@/types'

interface ApprovalTimelineProps {
  approvals: TemplateApproval[] | undefined
  isLoading: boolean
  error: Error | null
}

export function ApprovalTimeline({
  approvals,
  isLoading,
  error,
}: ApprovalTimelineProps) {
  if (isLoading) {
    return (
      <div className="space-y-3">
        {Array.from({ length: 2 }).map((_, i) => (
          <Skeleton key={i} className="h-16 w-full" />
        ))}
      </div>
    )
  }

  if (error) {
    return (
      <p className="text-sm text-red-600">
        Failed to load approval activity: {error.message}
      </p>
    )
  }

  if (!approvals || approvals.length === 0) {
    return (
      <p className="text-sm text-slate-500">
        No approval activity yet.
      </p>
    )
  }

  return (
    <ul className="space-y-3">
      {approvals.map((a) => (
        <ApprovalRow key={a.id} approval={a} />
      ))}
    </ul>
  )
}

/**
 * Single row in the approval timeline.
 *
 * The icon, color, and primary state-line text are all derived
 * from the approval's action field.
 */
function ApprovalRow({ approval }: { approval: TemplateApproval }) {
  const state = getApprovalState(approval)

  return (
    <li
      className={cn(
        'rounded-md border p-3 flex gap-3',
        state.borderClass
      )}
    >
      <div
        className={cn(
          'shrink-0 w-8 h-8 rounded-full flex items-center justify-center',
          state.iconBgClass
        )}
      >
        <state.Icon size={16} className={state.iconColorClass} />
      </div>

      <div className="flex-1 min-w-0">
        <div className="flex items-start justify-between gap-2">
          <div className="min-w-0">
            <div className="font-medium text-slate-900 truncate">
              {approval.reviewer_name ?? approval.reviewer_email}
            </div>
            <div className="text-xs text-slate-500 truncate">
              {approval.reviewer_email}
            </div>
          </div>
          {approval.reviewer_type && (
            <Badge
              variant={
                approval.reviewer_type === 'required'
                  ? 'default'
                  : 'outline'
              }
            >
              {approval.reviewer_type}
            </Badge>
          )}
        </div>

        <div className={cn('text-sm mt-1', state.textClass)}>
          {state.label}
          {approval.actioned_at && (
            <span className="text-slate-500 ml-1">
              on {formatDateTime(approval.actioned_at)}
            </span>
          )}
        </div>

        {approval.comment && (
          <div className="mt-2 rounded bg-slate-50 border border-slate-200 px-3 py-2 text-sm text-slate-700">
            <span className="text-slate-500 text-xs uppercase tracking-wide block mb-1">
              Comment
            </span>
            {approval.comment}
          </div>
        )}
      </div>
    </li>
  )
}

/**
 * Compute the visual treatment for an approval row based on its
 * action field.
 *
 * Returns a bundle of icon component, color classes, and label
 * text. Centralized here so all three states stay visually
 * consistent.
 */
function getApprovalState(approval: TemplateApproval) {
  if (approval.action === 'approved') {
    return {
      Icon: Check,
      label: 'Approved',
      iconBgClass: 'bg-green-100',
      iconColorClass: 'text-green-700',
      borderClass: 'border-green-200',
      textClass: 'text-green-800 font-medium',
    }
  }
  if (approval.action === 'rejected') {
    return {
      Icon: X,
      label: 'Rejected',
      iconBgClass: 'bg-red-100',
      iconColorClass: 'text-red-700',
      borderClass: 'border-red-200',
      textClass: 'text-red-800 font-medium',
    }
  }
  return {
    Icon: Clock,
    label: 'Waiting on review',
    iconBgClass: 'bg-slate-100',
    iconColorClass: 'text-slate-500',
    borderClass: 'border-slate-200',
    textClass: 'text-slate-600',
  }
}