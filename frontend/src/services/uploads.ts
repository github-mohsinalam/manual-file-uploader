/**
 * Uploads API service.
 *
 * Wraps POST /uploads (multipart file upload) and GET /uploads/{id}.
 * The POST endpoint accepts a CSV or XLSX file, runs Polars
 * validation synchronously, and returns an UploadSummary with
 * the upload_id and initial status.
 *
 * The progress page (Task 9.16) polls GET /uploads/{id} for
 * status changes until a terminal state.
 */

import { api } from '@/lib/api/client'
import type { UploadHistory, UploadSummary } from '@/types'
import type { UploadValidationError } from '@/types'

/**
 * Submit a file for upload against a template.
 *
 * Backend endpoint: POST /api/v1/uploads
 *
 * onProgress is fired as upload bytes are transmitted - useful
 * for showing a progress bar. The percent is 0-100; total may be
 * undefined on some connections, in which case onProgress is
 * not fired.
 */
export async function submitUpload(
  templateId: string,
  file: File,
  onProgress?: (percent: number) => void
): Promise<UploadSummary> {
  const formData = new FormData()
  formData.append('template_id', templateId)
  formData.append('file', file)

  const response = await api.post<UploadSummary>(
    '/api/v1/uploads',
    formData,
    {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
      // Uploads can be slow on large files - give it more time
      // than the default 30s axios timeout.
      timeout: 10 * 60 * 1000,
      onUploadProgress: (event) => {
        if (event.total && onProgress) {
          const percent = Math.round(
            (event.loaded / event.total) * 100
          )
          onProgress(percent)
        }
      },
    }
  )
  return response.data
}

/** Fetch full upload details by ID (drives the progress page). */
export async function getUpload(id: string): Promise<UploadHistory> {
  const response = await api.get<UploadHistory>(
    `/api/v1/uploads/${id}`
  )
  return response.data
}

/** List uploads, optionally filtered by template. */
export async function listUploads(
  templateId?: string
): Promise<UploadHistory[]> {
  const response = await api.get<UploadHistory[]>(
    '/api/v1/uploads',
    {
      params: templateId ? { template_id: templateId } : undefined,
    }
  )
  return response.data
}



/**
 * Fetch validation errors for an upload.
 *
 * Backend endpoint: GET /api/v1/uploads/{upload_id}/errors
 *
 * Returns one row per bad cell from Polars validation. Empty
 * for successful uploads.
 */
export async function listUploadErrors(
  uploadId: string
): Promise<UploadValidationError[]> {
  const response = await api.get<UploadValidationError[]>(
    `/api/v1/uploads/${uploadId}/errors`
  )
  return response.data
}