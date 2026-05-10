/**
 * TypeScript types for the UploadHistory resource.
 *
 * Mirrors backend/app/schemas/upload_history.py.
 *
 * The upload lifecycle has 8 status values driving the progress
 * stepper UI.
 */

/**
 * Upload lifecycle statuses.
 * Must stay in sync with the SQL CHECK constraint in
 * sql/07_create_upload_history_table.sql.
 *
 * Terminal states: completed, failed, partial. Polling stops
 * on these.
 */
export type UploadStatus =
  | 'in_progress'
  | 'file_uploaded'
  | 'schema_validated'
  | 'constraints_checked'
  | 'writing_to_catalog'
  | 'completed'
  | 'failed'
  | 'partial'

/**
 * Compact response from POST /uploads, returned right after
 * synchronous validation completes.
 */
export interface UploadSummary {
  id: string
  template_id: string
  status: UploadStatus
  total_rows: number | null
  valid_rows: number | null
  invalid_rows: number | null
  error_summary: string | null
}

/**
 * Full response from GET /uploads/{id}. Drives the progress
 * stepper UI on the upload-progress page.
 */
export interface UploadHistory {
  id: string
  template_id: string

  uploaded_by: string
  uploaded_at: string

  original_filename: string
  file_size_bytes: number | null

  total_rows: number | null
  valid_rows: number | null
  invalid_rows: number | null

  status: UploadStatus
  error_summary: string | null

  databricks_run_id: string | null

  completed_at: string | null
  updated_at: string
}