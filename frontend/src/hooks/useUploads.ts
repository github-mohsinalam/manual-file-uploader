/**
 * useUploads - fetch the list of uploads with server-side
 * filtering.
 *
 * Filters are part of the queryKey so different filter
 * combinations are cached separately. Switching filters
 * triggers a refetch (or hits the cache if previously
 * loaded).
 */

import { useQuery } from '@tanstack/react-query'
import { listUploads, type UploadsListFilters } from '@/services/uploads'
import type { UploadHistory } from '@/types'

export function useUploads(filters: UploadsListFilters = {}) {
  return useQuery<UploadHistory[]>({
    // queryKey includes the filters object so different filter
    // combinations are cached independently.
    queryKey: ['uploads', filters],
    queryFn: () => listUploads(filters),
  })
}