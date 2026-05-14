/**
 * useTemplateColumns - fetch the column list for a template.
 */

import { useQuery } from '@tanstack/react-query'
import { listTemplateColumns } from '@/services/template-columns'
import type { TemplateColumn } from '@/types'

export function useTemplateColumns(templateId: string | undefined) {
  return useQuery<TemplateColumn[]>({
    queryKey: ['template-columns', templateId],
    queryFn: () => listTemplateColumns(templateId as string),
    enabled: Boolean(templateId),
  })
}