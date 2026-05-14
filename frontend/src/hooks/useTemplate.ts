/**
 * useTemplate - fetch a single template by ID.
 *
 * Distinct queryKey from useTemplates (plural) so they're
 * cached independently.
 */

import { useQuery } from '@tanstack/react-query'
import { getTemplate } from '@/services/templates'
import type { Template } from '@/types'

export function useTemplate(id: string | undefined) {
  return useQuery<Template>({
    queryKey: ['template', id],
    queryFn: () => getTemplate(id as string),
    // Don't fire the query if there's no ID yet.
    enabled: Boolean(id),
  })
}