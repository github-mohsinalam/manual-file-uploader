/**
 * Helpers for rendering upload status consistently across pages.
 *
 * Maps each UploadStatus value to a Tailwind color set and a
 * short human-readable label.
 *
 * Centralized so every place that shows an upload status uses
 * the same colors.
 */

import type { UploadStatus } from '@/types'

interface StatusStyle {
  className: string
  label: string
}

const STATUS_STYLES: Record<UploadStatus, StatusStyle> = {
  in_progress: {
    className: 'bg-blue-100 text-blue-800 border-blue-200',
    label: 'In progress',
  },
  file_uploaded: {
    className: 'bg-blue-100 text-blue-800 border-blue-200',
    label: 'Uploaded',
  },
  schema_validated: {
    className: 'bg-blue-100 text-blue-800 border-blue-200',
    label: 'Schema OK',
  },
  constraints_checked: {
    className: 'bg-blue-100 text-blue-800 border-blue-200',
    label: 'Validating',
  },
  writing_to_catalog: {
    className: 'bg-blue-100 text-blue-800 border-blue-200',
    label: 'Writing',
  },
  completed: {
    className: 'bg-green-100 text-green-800 border-green-200',
    label: 'Completed',
  },
  partial: {
    className: 'bg-amber-100 text-amber-800 border-amber-200',
    label: 'Partial',
  },
  failed: {
    className: 'bg-red-100 text-red-800 border-red-200',
    label: 'Failed',
  },
}

export function getUploadStatusStyle(status: UploadStatus): StatusStyle {
  return STATUS_STYLES[status] ?? {
    className: 'bg-slate-100 text-slate-700',
    label: status,
  }
}