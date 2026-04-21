"""
DDL builder - Python functions that build SQL DDL from
template definition dictionaries.


Input dict structure (template_config):

    {
        "template_id": "uuid",
        "catalog": "manualuploads",
        "schema": "finance",
        "table": "region_mapping",
        "fully_qualified_name": "manualuploads.finance.region_mapping",
        "description": "Region to cost center mapping",
        "reader_group": "data-readers-finance",
        "columns": [
            {
                "name": "region_code",
                "data_type": "STRING",
                "description": "Unique regional identifier",
                "is_included": true,
                "is_pii": false,
                "is_nullable": false,
                "is_unique": true,
                "column_order": 1
            }
        ]
    }
"""

from typing import List


def escape_sql_string(value: str) -> str:
    """
    Escape single quotes in a string for safe SQL embedding.
    SQL uses doubled single quotes to escape a single quote.
    """
    return value.replace("'", "''")


def build_column_definition(column: dict) -> str:
    """
    Build a single column clause for the CREATE TABLE DDL.

    Example output:
        region_code STRING NOT NULL COMMENT 'Unique regional identifier'
    """
    parts = [column["name"], column["data_type"]]

    # NOT NULL is applied directly in CREATE TABLE
    # Delta Lake enforces this at write time
    if not column.get("is_nullable", True):
        parts.append("NOT NULL")

    # Inline column comment - combines PII flag and user description
    comment = column.get("description", "") or ""
    if column.get("is_pii"):
        prefix = "PII - masked"
        comment = f"{prefix} | {comment}" if comment else prefix

    if comment:
        escaped = escape_sql_string(comment)
        parts.append(f"COMMENT '{escaped}'")

    return " ".join(parts)


def build_create_table_ddl(config: dict) -> str:
    """
    Build the full CREATE TABLE IF NOT EXISTS DDL statement.

    Only included columns are part of the DDL. Excluded columns
    are filtered out entirely.
    """
    fqn = config["fully_qualified_name"]

    included_columns = [
        col for col in config["columns"]
        if col.get("is_included", True)
    ]

    # Sort by column_order for deterministic DDL output
    included_columns.sort(key=lambda c: c.get("column_order", 0))

    column_clauses = [
        build_column_definition(col) for col in included_columns
    ]
    columns_block = ",\n    ".join(column_clauses)

    table_comment = config.get("description", "") or ""
    comment_clause = ""
    if table_comment:
        escaped = escape_sql_string(table_comment)
        comment_clause = f"COMMENT '{escaped}'"

    ddl = f"""
CREATE TABLE IF NOT EXISTS {fqn} (
    {columns_block}
)
USING DELTA
{comment_clause}
""".strip()

    return ddl


def build_masking_function_ddl(catalog: str, schema: str) -> str:
    """
    Build the DDL to create a generic PII masking function.

    The function masks string values for users not in the
    'mfu_pii_viewers' group. Members of that group see the
    real value. Non-members see asterisks.

    This is a generic mask - a production system might have
    per-type masking (email, phone, etc.) but for this tool
    a single string-based mask is sufficient.

    Idempotent - uses CREATE OR REPLACE so re-running the job
    is always safe.
    """
    function_name = f"{catalog}.{schema}.mask_pii_string"
    return f"""
                CREATE OR REPLACE FUNCTION {function_name}(val STRING)
                RETURNS STRING
                RETURN CASE
                    WHEN is_member('mfu_pii_viewers') THEN val
                    ELSE REPEAT('*', LEAST(LENGTH(val), 8))
                END
            """.strip()


def build_pii_mask_statements(config: dict) -> List[str]:
    """
    Build ALTER TABLE statements to apply the masking function
    to each PII column.

    Returns one statement per PII column. Empty list if there
    are no PII columns.
    """
    catalog = config["catalog"]
    schema = config["schema"]
    fqn = config["fully_qualified_name"]
    function_name = f"{catalog}.{schema}.mask_pii_string"

    pii_columns = [
        col for col in config["columns"]
        if col.get("is_included", True) and col.get("is_pii", False)
    ]

    return [
        f"ALTER TABLE {fqn} ALTER COLUMN {col['name']} SET MASK {function_name}"
        for col in pii_columns
    ]


def build_grant_statements(config: dict) -> List[str]:
    """
    Build GRANT statements for the reader group.

    Three grants are needed for a group to actually query
    a Unity Catalog table:
    - USE CATALOG on the catalog
    - USE SCHEMA on the schema
    - SELECT on the table

    Returns empty list if no reader_group is configured.
    """
    reader_group = config.get("reader_group")
    if not reader_group:
        return []

    catalog = config["catalog"]
    schema = config["schema"]
    fqn = config["fully_qualified_name"]

    return [
        f"GRANT USE CATALOG ON CATALOG {catalog} TO `{reader_group}`",
        f"GRANT USE SCHEMA ON SCHEMA {catalog}.{schema} TO `{reader_group}`",
        f"GRANT SELECT ON TABLE {fqn} TO `{reader_group}`",
    ]