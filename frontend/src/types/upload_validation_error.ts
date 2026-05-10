/**
 * TypeScript types for upload validation errors.
 *
 * Mirrors backend/app/schemas/upload_validation_error.py.
 *
 * One row per bad cell from Polars Layer 1 validation.
 */

/**
 * Validation error categories.
 * Must match the SQL CHECK constraint in
 * sql/08_create_upload_validation_errors_table.sql.
 */
export type ValidationErrorType =
  | 'NOT_NULL'
  | 'UNIQUE'
  | 'TYPE_MISMATCH'
  | 'SCHEMA_MISMATCH'
  | 'ENCODING_ERROR'
  | 'PARSE_ERROR'

export interface UploadValidationError {
  id: string
  upload_id: string
  row_number: number
  column_name: string
  error_type: ValidationErrorType
  error_message: string
  raw_value: string | null
  created_at: string
}