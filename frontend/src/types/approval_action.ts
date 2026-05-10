/**
 * TypeScript types for the approval action endpoint.
 *
 * Mirrors backend/app/schemas/approval_action.py.
 *
 * The approval action endpoint accepts a token (in URL) and a
 * body containing the decision and an optional comment. Returns
 * an outcome summary for the UI to display.
 */

/**
 * URL paths use imperative verbs ("approve" / "reject").
 * The backend converts these to past-tense ("approved" /
 * "rejected") before storing.
 */
export type ApprovalActionVerb = 'approve' | 'reject'

/** Body of POST /approvals/{token}/{action}. */
export interface ApprovalActionRequest {
  decision: ApprovalActionVerb
  comment?: string | null
}

/** Response body returned after the action succeeds. */
export interface ApprovalActionResponse {
  decision_recorded: boolean
  template_status: string
  message: string
}