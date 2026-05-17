/**
 * useUpload - fetch an upload's status with polling.
 *
 * Polls every 2 seconds while the upload is in a non-terminal
 * state. Stops once status is one of: completed, failed, partial.
 *
 * TanStack Query handles the interval automatically; we just
 * declare the refetchInterval as a function that inspects the
 * latest data.
 */

import { useQuery } from '@tanstack/react-query'
import { getUpload } from '@/services/uploads'
import type { UploadHistory, UploadStatus } from '@/types'

const TERMINAL_STATUSES: UploadStatus[] = ['completed', 'failed', 'partial']

const POLL_INTERVAL_MS = 2000

export function useUpload(id: string | undefined) {
  return useQuery<UploadHistory>({
    queryKey: ['upload', id],
    queryFn: () => getUpload(id as string),
    enabled: Boolean(id),
    refetchInterval: (query) => {
      const data = query.state.data
      if (!data) return POLL_INTERVAL_MS
      if (TERMINAL_STATUSES.includes(data.status)) {
        return false
      }
      return POLL_INTERVAL_MS
    },
  })
}