/**
 * Template approvals API service.
 *
 * Wraps GET /templates/{template_id}/approvals.
 *
 * Used by the detail page to render the approval timeline. The
 * endpoint returns one row per reviewer with the decision state
 * (approved / rejected / not yet acted) and any comment they
 * left.
 */

import { api } from '@/lib/api/client'
import type { TemplateApproval } from '@/types'

/** Fetch all approval rows for a template, with reviewer info. */
export async function listTemplateApprovals(
  templateId: string
): Promise<TemplateApproval[]> {
  const response = await api.get<TemplateApproval[]>(
    `/api/v1/templates/${templateId}/approvals`
  )
  return response.data
}