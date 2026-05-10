/**
 * TypeScript types for the Domain resource.
 *
 * Mirrors backend/app/schemas/domain.py.
 *
 * Domains are seeded server-side (no UI to create them) so we
 * only define a response type, not a create/update type.
 */

export interface Domain {
  /** UUID v4. Backend returns it as a string. */
  id: string

  /** Human-readable domain name (e.g. "Finance"). */
  name: string

  /** Unity Catalog schema name (e.g. "finance"). */
  uc_schema_name: string

  description: string | null

  /** ISO 8601 timestamp string. */
  created_at: string

  /** ISO 8601 timestamp string. */
  updated_at: string

  created_by: string | null
}