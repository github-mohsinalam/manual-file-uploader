"""
DDL Job entry point.

This job creates a Unity Catalog Delta table for an approved
template. It is triggered by FastAPI once all required
reviewers have approved a template.

Parameters:
    template_id (string) - UUID of the approved template in
        PostgreSQL. The job fetches the full template
        configuration from PostgreSQL using this ID.

Flow:
    1. Read template_id from job parameter
    2. Fetch template config from PostgreSQL (db_client.py)
    3. Build CREATE TABLE DDL (ddl_builder.py)
    4. Execute CREATE TABLE on Unity Catalog
    5. If PII columns exist, create masking function
       and apply mask to each PII column
    6. Apply GRANT statements for reader group
    7. Exit successfully

Idempotency:
    Every step is designed to be safely re-runnable. CREATE TABLE
    uses IF NOT EXISTS. Masking function uses CREATE OR REPLACE.
    Mask application wraps the ALTER in a try/except to handle
    the case where the mask is already applied. GRANTs are
    naturally idempotent.
"""

import sys
import traceback

from db_client import load_template_config
from ddl_builder import (
    build_create_table_ddl,
    build_masking_function_ddl,
    build_pii_mask_statements,
    build_grant_statements,
)


def execute_idempotent_mask(spark_session, mask_statement: str) -> None:
    """
    Apply a mask to a column, tolerating the case where the mask
    is already applied.

    Databricks raises an exception with a specific message if the
    mask is already set. We catch just that case and continue.
    Any other error is re-raised.
    """
    try:
        spark_session.sql(mask_statement)
        print(f"  Mask applied: {mask_statement}")
    except Exception as e:
        error_message = str(e).lower()
        if "already" in error_message and "mask" in error_message:
            print(f"  Mask already applied (skipping): {mask_statement}")
        else:
            # Any other error - re-raise
            raise


def run_ddl_job(template_id: str, spark_session) -> None:
    """
    Orchestrate the full DDL job execution.

    Args:
        template_id: UUID of the approved template
        spark_session: Spark session (injected for testability)
    """
    print(f"DDL job starting for template_id: {template_id}")

    # Step 1 - Fetch config from PostgreSQL
    print("\nFetching template configuration from PostgreSQL...")
    config = load_template_config(template_id)
    fqn = config["fully_qualified_name"]
    print(f"  Template: {fqn}")
    print(f"  Columns: {len(config['columns'])}")

    # Step 2 - Create the Delta table
    print("\nCreating Unity Catalog table...")
    create_ddl = build_create_table_ddl(config)
    print(f"  DDL:\n{create_ddl}")
    spark_session.sql(create_ddl)
    print(f"  Table created (or already existed): {fqn}")

    # Step 3 - PII masking if any PII columns exist
    has_pii = any(
        col.get("is_pii", False) and col.get("is_included", True)
        for col in config["columns"]
    )

    if has_pii:
        print("\nApplying PII masking...")

        # Create (or replace) the masking function
        mask_function_ddl = build_masking_function_ddl(
            catalog=config["catalog"],
            schema=config["schema"],
        )
        spark_session.sql(mask_function_ddl)
        print(f"  Masking function created (or replaced)")

        # Apply mask to each PII column
        mask_statements = build_pii_mask_statements(config)
        for statement in mask_statements:
            execute_idempotent_mask(spark_session, statement)
    else:
        print("\nNo PII columns - skipping masking setup.")

    # Step 4 - Apply GRANT statements
    grants = build_grant_statements(config)
    if grants:
        print("\nApplying reader group grants...")
        for grant in grants:
            spark_session.sql(grant)
            print(f"  Granted: {grant}")
    else:
        print("\nNo reader_group configured - skipping grants.")

    print(f"\nDDL job completed successfully for: {fqn}")


if __name__ == "__main__":
    # dbutils and spark are automatically available in Databricks runtime
    template_id = dbutils.widgets.get("template_id")  

    try:
        run_ddl_job(template_id, spark)  
    except Exception as error:
        print(f"\nDDL job FAILED: {error}")
        traceback.print_exc()
        # Exit with non-zero status so Databricks marks the job as FAILED
        sys.exit(1)