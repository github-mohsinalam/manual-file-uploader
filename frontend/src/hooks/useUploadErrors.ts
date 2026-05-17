/**
 * useUploadErrors - fetch validation errors for an upload.
 *
 * Only enabled once the upload reaches a terminal state.
 */

import { useQuery } from '@tanstack/react-query'
import { listUploadErrors } from '@/services/uploads'
import type { UploadValidationError, UploadStatus } from '@/types'

const TERMINAL_STATUSES: UploadStatus[] = ['completed', 'failed', 'partial']

export function useUploadErrors(
  uploadId: string | undefined,
  uploadStatus: UploadStatus | undefined
) {
  return useQuery<UploadValidationError[]>({
    queryKey: ['upload-errors', uploadId],
    queryFn: () => listUploadErrors(uploadId as string),
    // Only fetch when the upload has finished - error counts are
    // not final until then.
    enabled:
      Boolean(uploadId) &&
      Boolean(uploadStatus) &&
      TERMINAL_STATUSES.includes(uploadStatus as UploadStatus),
  })
}