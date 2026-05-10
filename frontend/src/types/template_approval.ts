/**
 * TypeScript types for the TemplateApproval resource.
 *
 * Mirrors backend/app/schemas/template_approval.py.
 *
 * An approval row records a reviewer's decision (approved or
 * rejected) on a specific template. Created when a template is
 * submitted for approval; updated once the reviewer acts via
 * their email link.
 */

/**
 * Past-tense values stored in the database.
 * Matches the SQL CHECK constraint in
 * sql/06_create_template_approvals_table.sql.
 *
 * `null` means the reviewer has not yet acted.
 */
export type ApprovalAction = 'approved' | 'rejected' | null

export interface TemplateApproval {
  id: string
  template_id: string

  reviewer_email: string
  reviewer_name: string | null

  action: ApprovalAction
  comment: string | null

  /** Token expiry as ISO 8601. */
  token_expires_at: string

  /** When the reviewer acted; null until they do. */
  actioned_at: string | null

  created_at: string
}