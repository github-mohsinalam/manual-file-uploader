/**
 * TypeScript types for the TemplateReviewer resource.
 *
 * Mirrors backend/app/schemas/template_reviewer.py.
 *
 * A reviewer is required or optional. Required reviewers must
 * all approve before a template is activated.
 */

export type ReviewerType = 'required' | 'optional'

export interface TemplateReviewer {
  id: string
  template_id: string

  reviewer_email: string
  reviewer_name: string | null
  reviewer_type: ReviewerType

  created_at: string
}

export interface TemplateReviewerCreate {
  reviewer_email: string
  reviewer_name?: string | null
  reviewer_type?: ReviewerType
}