"""
PostgreSQL client for Databricks jobs.

Provides functions to fetch template metadata from the Azure
PostgreSQL database using Spark's JDBC reader.

Credentials are read from the 'mfu-dev' Databricks secret scope.

All database access goes through this module. Individual Databricks
jobs import from here and never talk JDBC directly.
"""

from typing import Optional

# The spark and dbutils objects are automatically available in
# the Databricks runtime. They are imported through the runtime,
# not from a Python package. Do not try to pip install them.


SECRET_SCOPE = "mfu-dev"


def _build_jdbc_url() -> str:
    """Build the JDBC URL from secrets."""
    host = dbutils.secrets.get(scope=SECRET_SCOPE, key="postgres-host")   
    port = dbutils.secrets.get(scope=SECRET_SCOPE, key="postgres-port")   
    db = dbutils.secrets.get(scope=SECRET_SCOPE, key="postgres-db")       
    # sslmode=require is mandatory for Azure Database for PostgreSQL
    return f"jdbc:postgresql://{host}:{port}/{db}?sslmode=require"


def _get_jdbc_options() -> dict:
    """Return a dict of JDBC options including credentials."""
    return {
        "url": _build_jdbc_url(),
        "user": dbutils.secrets.get(scope=SECRET_SCOPE, key="postgres-user"),   
        "password": dbutils.secrets.get(scope=SECRET_SCOPE, key="postgres-password"),   
        "driver": "org.postgresql.Driver",
    }


def _read_query_as_rows(query: str) -> list:
    """
    Execute a SQL query against PostgreSQL and return the result
    as a list of dicts - one dict per row with column names as keys.

    Uses a derived table (subquery) so Spark can run arbitrary SQL
    via the dbtable option. This is a common JDBC pattern.
    """
    options = _get_jdbc_options()

    df = (
        spark.read                                                    
        .format("jdbc")
        .option("url", options["url"])
        .option("dbtable", f"({query}) AS t")
        .option("user", options["user"])
        .option("password", options["password"])
        .option("driver", options["driver"])
        .load()
    )

    # Collect is fine here - we never fetch millions of rows
    # when reading template metadata
    return [row.asDict() for row in df.collect()]


def load_template_config(template_id: str) -> dict:
    """
    Fetch the full template definition from PostgreSQL and assemble
    it into the dict structure expected by the DDL builder.

    This executes two queries:
    1. Fetch the template row + domain info (joined)
    2. Fetch all column configs for the template

    Returns a dict matching the ddl_builder input contract. Raises
    ValueError if the template is not found.
    """
    # Query 1: template plus its domain
    template_query = f"""
        SELECT
            t.id                   AS template_id,
            t.name                 AS template_name,
            t.uc_table_name        AS uc_table_name,
            t.fully_qualified_name AS fully_qualified_name,
            t.description          AS description,
            t.reader_group         AS reader_group,
            d.uc_schema_name       AS uc_schema_name
        FROM templates t
        JOIN domains d ON t.domain_id = d.id
        WHERE t.id = '{template_id}'
    """.strip()
    template_rows = _read_query_as_rows(template_query)
    if not template_rows:
        raise ValueError(f"Template not found: {template_id}")
    template = template_rows[0]

    # Query 2: all column configurations ordered by column_order
    columns_query = f"""
        SELECT
            column_name,
            display_name,
            data_type,
            description,
            is_included,
            is_pii,
            is_nullable,
            is_unique,
            column_order
        FROM template_columns
        WHERE template_id = '{template_id}'
        ORDER BY column_order
    """
    columns = _read_query_as_rows(columns_query)

    # Assemble the dict in the shape the DDL builder expects
    return {
        "template_id": template["template_id"],
        "catalog": "manualuploads",
        "schema": template["uc_schema_name"],
        "table": template["uc_table_name"],
        "fully_qualified_name": template["fully_qualified_name"],
        "description": template.get("description") or "",
        "reader_group": template.get("reader_group"),
        "columns": [
            {
                "name": col["column_name"],
                "display_name": col.get("display_name"),
                "data_type": col["data_type"],
                "description": col.get("description") or "",
                "is_included": bool(col["is_included"]),
                "is_pii": bool(col["is_pii"]),
                "is_nullable": bool(col["is_nullable"]),
                "is_unique": bool(col["is_unique"]),
                "column_order": int(col.get("column_order", 0)),
            }
            for col in columns
        ],
    }