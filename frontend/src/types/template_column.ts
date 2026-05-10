/**
 * TypeScript types for the TemplateColumn resource.
 *
 * Mirrors backend/app/schemas/template_column.py.
 *
 * A TemplateColumn defines a single column within a template:
 * its data type, whether it's PII, nullable, unique, etc.
 */

/**
 * Data types supported by the template column configuration.
 * Must match the SQL CHECK constraint in
 * sql/04_create_template_columns_table.sql.
 */
export type ColumnDataType =
  | 'STRING'
  | 'INTEGER'
  | 'BIGINT'
  | 'LONG'
  | 'DOUBLE'
  | 'DECIMAL'
  | 'BOOLEAN'
  | 'DATE'
  | 'TIMESTAMP'

/** Response shape returned by the backend. */
export interface TemplateColumn {
  id: string
  template_id: string

  column_name: string
  display_name: string | null
  data_type: ColumnDataType
  description: string | null

  is_included: boolean
  is_pii: boolean
  is_nullable: boolean
  is_unique: boolean
  column_order: number

  created_at: string
}

/**
 * Payload for creating a new template column.
 *
 * Optional fields marked with `?` may be omitted from the JSON
 * body. Backend applies defaults if missing.
 */
export interface TemplateColumnCreate {
  column_name: string
  display_name?: string | null
  data_type?: ColumnDataType
  description?: string | null
  is_included?: boolean
  is_pii?: boolean
  is_nullable?: boolean
  is_unique?: boolean
  column_order?: number
}