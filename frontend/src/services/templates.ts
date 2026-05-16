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

/**
 * Result of POST /templates/parse-sample - inferred column metadata
 * from a sample CSV/XLSX file.
 */
export interface ParsedColumn {
  column_name: string
  data_type: string
  sample_values: string[]
}

export interface ParsedSampleResponse {
  columns: ParsedColumn[]
  total_rows_scanned: number
}

/**
 * Parse a sample file (CSV or XLSX) and return inferred columns.
 *
 * Used by the wizard's columns step to prefill the column list
 * from a user-uploaded file. No template is created or modified.
 */
export async function parseSampleFile(
  file: File
): Promise<ParsedSampleResponse> {
  const formData = new FormData()
  formData.append('file', file)

  const response = await api.post<ParsedSampleResponse>(
    '/api/v1/templates/parse-sample',
    formData,
    {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    }
  )
  return response.data
}


/**
 * Submit a Draft template for approval.
 *
 * Backend endpoint: POST /api/v1/templates/{id}/submit
 *
 * The backend validates the template (has columns, has at least
 * one required reviewer), creates approval rows with tokens,
 * transitions the status to "Pending Approval", and schedules
 * approval-request emails to all reviewers.
 *
 * Returns the updated template (status will be "Pending Approval").
 */
export async function submitTemplate(id: string): Promise<Template> {
  const response = await api.post<Template>(
    `/api/v1/templates/${id}/submit`
  )
  return response.data
}