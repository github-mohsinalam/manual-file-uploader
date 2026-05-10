/**
 * TypeScript types for the Template resource.
 *
 * Mirrors backend/app/schemas/template.py.
 *
 * A template defines the structure of a manual mapping file
 * and the corresponding Unity Catalog Delta table.
 */

/**
 * Lifecycle status values.
 *
 * Must stay in sync with both:
 *   - SQL CHECK constraint in sql/03_create_templates_table.sql
 *   - app/models/template.py default value
 */
export type TemplateStatus =
  | 'Draft'
  | 'Pending Approval'
  | 'Pending DDL'
  | 'Approved'
  | 'Rejected'
  | 'DDL Failed'
  | 'Deprecated'

export type FileFormat = 'csv' | 'xlsx'
export type WriteMode = 'append' | 'overwrite'
export type BadRowAction = 'fail' | 'drop'

/** Full response shape returned by GET /templates/{id}. */
export interface Template {
  id: string
  name: string
  display_name: string
  description: string | null

  domain_id: string

  uc_table_name: string
  fully_qualified_name: string

  file_format: FileFormat
  delimiter: string
  encoding: string
  write_mode: WriteMode

  /** Percentage 0-100. Returned as a string by Pydantic Decimal. */
  bad_row_threshold: string
  bad_row_action: BadRowAction

  storage_path: string | null
  reader_group: string | null

  status: TemplateStatus
  version: number
  parent_template_id: string | null

  created_by: string
  created_at: string
  updated_at: string
  approved_at: string | null
  databricks_ddl_run_id: string | null
}

/**
 * Payload for POST /templates.
 *
 * The user provides only the basic identification fields; the
 * server fills in defaults for everything else.
 */
export interface TemplateCreate {
  name: string
  display_name: string
  description?: string | null
  domain_id: string
}

/**
 * Payload for PATCH /templates/{id}.
 *
 * All fields are optional — only fields the client actually wants
 * to change need to be sent. Backend uses model_dump(exclude_unset=True)
 * so missing fields are NOT touched.
 */
export interface TemplateUpdate {
  display_name?: string
  description?: string | null
  file_format?: FileFormat
  delimiter?: string
  encoding?: string
  write_mode?: WriteMode
  bad_row_threshold?: string
  bad_row_action?: BadRowAction
  reader_group?: string | null
}