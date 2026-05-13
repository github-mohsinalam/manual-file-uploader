/**
 * Template API service.
 *
 * Wraps the /api/v1/templates endpoints with typed functions.
 * Components and hooks call these, not axios directly.
 */

import { api } from '@/lib/api/client'
import type {
  Template,
  TemplateCreate,
  TemplateUpdate,
  TemplateStatus,
} from '@/types'

/**
 * Filters that can be applied to GET /templates.
 *
 * All fields are optional. Empty/undefined values are dropped
 * from the URL automatically by axios.
 */
export interface ListTemplatesParams {
  status?: TemplateStatus
  domain_id?: string
  created_by?: string
  search?: string
  limit?: number
  offset?: number
}

/**
 * Fetch templates with optional filters.
 *
 * Backend endpoint: GET /api/v1/templates
 */
export async function listTemplates(
  params: ListTemplatesParams = {}
): Promise<Template[]> {
  const response = await api.get<Template[]>('/api/v1/templates', {
    params,
  })
  return response.data
}

/** Fetch a single template by ID. */
export async function getTemplate(id: string): Promise<Template> {
  const response = await api.get<Template>(`/api/v1/templates/${id}`)
  return response.data
}

/** Create a new draft template. */
export async function createTemplate(
  payload: TemplateCreate
): Promise<Template> {
  const response = await api.post<Template>('/api/v1/templates', payload)
  return response.data
}

/** Update a draft template's fields. */
export async function updateTemplate(
  id: string,
  payload: TemplateUpdate
): Promise<Template> {
  const response = await api.patch<Template>(
    `/api/v1/templates/${id}`,
    payload
  )
  return response.data
}

/** Delete a draft template. */
export async function deleteTemplate(id: string): Promise<void> {
  await api.delete(`/api/v1/templates/${id}`)
}