/**
 * TypeScript types for the approval action endpoint.
 *
 * Mirrors backend/app/schemas/approval_action.py.
 *
 * The approval action endpoint accepts a token (in URL) and an
 * optional comment (in body), and returns an outcome summary.
 */

/**
 * URL paths use imperative verbs ("approve" / "reject").
 * The backend converts these to past-tense ("approved" /
 * "rejected") before storing.
 */
export type ApprovalActionVerb = 'approve' | 'reject'

export interface ApprovalActionRequest {
  comment?: string | null
}

export interface ApprovalActionResponse {
  template_id: string
  reviewer_email: string

  /** Past-tense form returned by the backend. */
  action: 'approved' | 'rejected'

  /** Current overall template status after this action. */
  template_status: string

  message: string
}