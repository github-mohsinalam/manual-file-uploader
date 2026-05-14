/**
 * useTemplateReviewers - fetch the reviewer list for a template.
 */

import { useQuery } from '@tanstack/react-query'
import { listTemplateReviewers } from '@/services/template-reviewers'
import type { TemplateReviewer } from '@/types'

export function useTemplateReviewers(templateId: string | undefined) {
  return useQuery<TemplateReviewer[]>({
    queryKey: ['template-reviewers', templateId],
    queryFn: () => listTemplateReviewers(templateId as string),
    enabled: Boolean(templateId),
  })
}