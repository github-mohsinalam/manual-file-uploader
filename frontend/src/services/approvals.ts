/**
 * Approval API service.
 *
 * Used by the public /approve page where reviewers land from
 * their email links. No auth required - the token in the URL
 * is the credential.
 */

import { api } from '@/lib/api/client'
import type { ApprovalActionResponse } from '@/types'

/**
 * Token-bearing response from GET /approvals/{token}.
 *
 * Returned before the reviewer makes a decision. Once a decision
 * is recorded, GET on the same token returns 410.
 */
export interface ApprovalTokenInfo {
  reviewer_email: string
  reviewer_name: string
  reviewer_type: 'required' | 'optional'

  template: {
    id: string
    name: string
    display_name: string
    description: string | null
    fully_qualified_name: string
    domain_name: string
  }

  token_expires_at: string
}

/**
 * Fetch the template + reviewer info for a given approval token.
 *
 * Possible responses:
 *   200 - returns ApprovalTokenInfo
 *   404 - invalid token
 *   410 - already used or expired (the error's detail tells the
 *         reviewer what they previously decided)
 *
 * The caller should NOT swallow the 410 - it's a useful render
 * state, not an error.
 */
export async function fetchApprovalInfo(
  token: string
): Promise<ApprovalTokenInfo> {
  const response = await api.get<ApprovalTokenInfo>(
    `/api/v1/approvals/${token}`
  )
  return response.data
}

/**
 * Submit an approval decision for a given token.
 *
 * decision must be 'approve' or 'reject'. Comment is optional.
 *
 * Possible responses:
 *   200 - decision recorded, returns ApprovalActionResponse
 *   400 - bad payload or template not in Pending Approval
 *   404 - invalid token
 *   410 - already used (race condition - someone else submitted)
 */
export async function submitApprovalDecision(
  token: string,
  decision: 'approve' | 'reject',
  comment?: string
): Promise<ApprovalActionResponse> {
  const response = await api.post<ApprovalActionResponse>(
    `/api/v1/approvals/${token}`,
    { decision, comment: comment || null }
  )
  return response.data
}