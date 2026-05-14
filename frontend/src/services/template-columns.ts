/**
 * Template columns API service.
 *
 * Wraps /api/v1/templates/{template_id}/columns endpoints.
 *
 * The backend uses a replace-list pattern: POST replaces all
 * columns for a template, GET lists them. There's no
 * "create one column" endpoint - templates always get their
 * columns set as a batch.
 */

import { api } from '@/lib/api/client'
import type { TemplateColumn, TemplateColumnCreate } from '@/types'

/** Fetch all columns for a template, ordered by column_order. */
export async function listTemplateColumns(
  templateId: string
): Promise<TemplateColumn[]> {
  const response = await api.get<TemplateColumn[]>(
    `/api/v1/templates/${templateId}/columns`
  )
  return response.data
}

/**
 * Replace the entire column list for a template.
 * The backend deletes existing columns and inserts the new list.
 */
export async function replaceTemplateColumns(
  templateId: string,
  columns: TemplateColumnCreate[]
): Promise<TemplateColumn[]> {
  const response = await api.post<TemplateColumn[]>(
    `/api/v1/templates/${templateId}/columns`,
    columns
  )
  return response.data
}

/** Delete a single column from a template. */
export async function deleteTemplateColumn(
  templateId: string,
  columnId: string
): Promise<void> {
  await api.delete(
    `/api/v1/templates/${templateId}/columns/${columnId}`
  )
}