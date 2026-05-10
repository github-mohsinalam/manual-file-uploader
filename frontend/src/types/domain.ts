export interface Domain {
  /** UUID v4. Backend returns it as a string. */
  id: string

  /** Human-readable domain name (e.g. "Finance"). */
  name: string

  /** Unity Catalog schema name (e.g. "finance"). */
  uc_schema_name: string

  description: string | null
}