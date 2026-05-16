/**
 * TypeScript types for the TemplateApproval resource.
 *
 * Mirrors backend/app/schemas/template_approval.py.
 *
 * An approval row records a reviewer's decision (approved or
 * rejected) on a specific template. Created when a template is
 * submitted for approval; updated once the reviewer acts via
 * their email link.
 *
 * The reviewer_type field is joined in from the
 * template_reviewers table by the backend - the frontend uses it
 * to render required vs optional reviewers differently in the
 * approval timeline.
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

  /**
   * Joined in from template_reviewers - the role this person
   * has on the template. May be null defensively if the join
   * failed (shouldn't happen in practice).
   */
  reviewer_type: 'required' | 'optional' | null

  action: ApprovalAction
  comment: string | null

  /** When the reviewer acted; null until they do. */
  actioned_at: string | null

  created_at: string
}