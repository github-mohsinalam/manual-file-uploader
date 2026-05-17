/**
 * useUploads - fetch the list of uploads.
 *
 * Currently fetches all uploads, optionally scoped to a template.
 * Filters (status, search) are applied client-side because the
 * backend's GET /uploads endpoint doesn't yet support them.
 *
 * For large datasets this should move to server-side filtering,
 * but at our scale (likely under a few hundred uploads) client-
 * side filtering is fine and gives us instant feedback.
 */

import { useQuery } from '@tanstack/react-query'
import { listUploads } from '@/services/uploads'
import type { UploadHistory } from '@/types'

export function useUploads(templateId?: string) {
  return useQuery<UploadHistory[]>({
    queryKey: ['uploads', templateId],
    queryFn: () => listUploads(templateId),
  })
}