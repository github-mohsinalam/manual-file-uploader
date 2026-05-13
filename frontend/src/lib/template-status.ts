/**
 * Helpers for rendering template status consistently.
 *
 * Maps each TemplateStatus value to:
 *   - A Tailwind color class for the badge
 *   - A short human-readable label (same as the value but
 *     could diverge in the future)
 *
 * Centralizing here means every page that shows a status
 * uses the same colors.
 */

import type { TemplateStatus } from '@/types'

interface StatusStyle {
  /** Tailwind classes for background + text color */
  className: string
  /** Display label */
  label: string
}

const STATUS_STYLES: Record<TemplateStatus, StatusStyle> = {
  'Draft': {
    className: 'bg-slate-100 text-slate-700 border-slate-200',
    label: 'Draft',
  },
  'Pending Approval': {
    className: 'bg-amber-100 text-amber-800 border-amber-200',
    label: 'Pending Approval',
  },
  'Pending DDL': {
    className: 'bg-blue-100 text-blue-800 border-blue-200',
    label: 'Pending DDL',
  },
  'Approved': {
    className: 'bg-green-100 text-green-800 border-green-200',
    label: 'Approved',
  },
  'Rejected': {
    className: 'bg-red-100 text-red-800 border-red-200',
    label: 'Rejected',
  },
  'DDL Failed': {
    className: 'bg-red-100 text-red-800 border-red-200',
    label: 'DDL Failed',
  },
  'Deprecated': {
    className: 'bg-slate-100 text-slate-500 border-slate-200',
    label: 'Deprecated',
  },
}

export function getStatusStyle(status: TemplateStatus): StatusStyle {
  return STATUS_STYLES[status] ?? {
    className: 'bg-slate-100 text-slate-700',
    label: status,
  }
}