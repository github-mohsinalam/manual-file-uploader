/**
 * Template reviewers API service.
 *
 * Wraps /api/v1/templates/{template_id}/reviewers endpoints.
 */

import { api } from '@/lib/api/client'
import type { TemplateReviewer, TemplateReviewerCreate } from '@/types'

/** Fetch all reviewers for a template, ordered by email. */
export async function listTemplateReviewers(
  templateId: string
): Promise<TemplateReviewer[]> {
  const response = await api.get<TemplateReviewer[]>(
    `/api/v1/templates/${templateId}/reviewers`
  )
  return response.data
}

/** Replace the entire reviewer list for a template. */
export async function replaceTemplateReviewers(
  templateId: string,
  reviewers: TemplateReviewerCreate[]
): Promise<TemplateReviewer[]> {
  const response = await api.post<TemplateReviewer[]>(
    `/api/v1/templates/${templateId}/reviewers`,
    reviewers
  )
  return response.data
}

/** Delete a single reviewer from a template. */
export async function deleteTemplateReviewer(
  templateId: string,
  reviewerId: string
): Promise<void> {
  await api.delete(
    `/api/v1/templates/${templateId}/reviewers/${reviewerId}`
  )
}