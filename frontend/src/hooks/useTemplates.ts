/**
 * useTemplates - custom hook for fetching templates with
 * optional filters.
 *
 * The filter object is part of the queryKey, so each unique
 * combination gets its own cache entry. Switching back to a
 * previous filter combination renders instantly from cache.
 */

import { useQuery } from '@tanstack/react-query'
import {
  listTemplates,
  type ListTemplatesParams,
} from '@/services/templates'
import type { Template } from '@/types'

export function useTemplates(filters: ListTemplatesParams = {}) {
  return useQuery<Template[]>({
    queryKey: ['templates', filters],
    queryFn: () => listTemplates(filters),
  })
}