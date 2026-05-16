/**
 * useTemplateApprovals - fetch the approval rows for a template.
 *
 * Returns an empty list for Draft templates - approval rows are
 * only created when a template is submitted for approval.
 */

import { useQuery } from '@tanstack/react-query'
import { listTemplateApprovals } from '@/services/template-approvals'
import type { TemplateApproval } from '@/types'

export function useTemplateApprovals(templateId: string | undefined) {
  return useQuery<TemplateApproval[]>({
    queryKey: ['template-approvals', templateId],
    queryFn: () => listTemplateApprovals(templateId as string),
    enabled: Boolean(templateId),
  })
}