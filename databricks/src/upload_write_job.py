"""
Upload Write Job entry point.

This job is triggered by FastAPI after Polars validation
passes the threshold check and the clean Parquet has been
staged to ADLS. It reads that Parquet, stamps three audit
columns on every row, and writes the result to the
template's Unity Catalog Delta table.

Parameters (command line arguments):
    --template_id (string) - UUID of the template the upload
        targets. Used to fetch FQN and write_mode from
        PostgreSQL.
    --upload_id (string) - UUID of the upload_history row
        for this upload. Used to derive the staging path
        and to populate the _upload_id audit column.
    --uploaded_by (string) - email of the user who
        performed the upload. Stored in the _uploaded_by
        audit column.

Why these three parameters and not more
---------------------------------------
The staging path is fully determined by domain +
template_id + upload_id, so there is no need to pass it
explicitly - we rebuild it the same way FastAPI did. FQN
and write_mode are template properties; passing them as
parameters would let them drift from the template
definition. Better to read them from Postgres at job time
and stay aligned. The only piece FastAPI uniquely knows
is the current_user identity, hence uploaded_by.

Audit columns
-------------
Every Delta table created by this tool carries three
platform audit columns (added by the DDL builder):
    _uploaded_by   - email of the uploader
    _uploaded_at   - timestamp pinned at job start, same
                     value for every row in this batch
    _upload_id     - UUID of the upload_history row

This job is responsible for filling them. The audit
timestamp is taken once when the job starts (literal,
not current_timestamp() per row) so a single upload
batch shares one timestamp across every row written.
That makes "what changed in this upload" a clean
filter: WHERE _upload_id = '...'.

Failure surface
---------------
Exceptions propagate. Databricks marks the run FAILED;
FastAPI's polling code reads the run state
and surfaces the failure to the user.
"""

import sys
import traceback
from datetime import datetime, timezone

from pyspark.sql import functions as F

from db_client import _read_query_as_rows


AUDIT_UPLOADED_BY = "_uploaded_by"
AUDIT_UPLOADED_AT = "_uploaded_at"
AUDIT_UPLOAD_ID = "_upload_id"


def load_template_target(spark, dbutils, template_id: str) -> dict:
    """
    Fetch the table FQN, write_mode, and domain schema name
    needed to perform the write.

    A second template lookup function (alongside
    db_client.load_template_config used by the DDL job)
    because we need a different shape - just the few fields
    relevant to writing data, plus the domain's UC schema
    name so we can build the staging path.

    Returns:
        {
            "fully_qualified_name": str,
            "write_mode": str,
            "uc_schema_name": str,
        }
    """
    query = f"""
        SELECT
            t.fully_qualified_name AS fully_qualified_name,
            t.write_mode           AS write_mode,
            d.uc_schema_name       AS uc_schema_name
        FROM templates t
        JOIN domains d ON t.domain_id = d.id
        WHERE t.id = '{template_id}'
    """
    rows = _read_query_as_rows(spark, dbutils, query)
    if not rows:
        raise ValueError(f"Template not found: {template_id}")
    return rows[0]


def build_staging_abfss_path(
    dbutils, uc_schema_name: str, template_id: str, upload_id: str
) -> str:
    """
    Build the abfss:// URL for the staging Parquet.

    Mirrors the path scheme used by FastAPI's
    storage_service.build_staging_path (kept in
    backend/app/services/storage/storage_service.py). Drift
    between these two functions would mean Spark cannot find
    the file FastAPI wrote.

    The storage account name and container name are read
    from the same secret scope as Postgres credentials,
    keeping all secrets in one place.
    """
    account = dbutils.secrets.get(
        scope="mfu-dev", key="storage-account-name"
    )
    container = dbutils.secrets.get(
        scope="mfu-dev", key="storage-container-name"
    )
    return (
        f"abfss://{container}@{account}.dfs.core.windows.net/"
        f"staging/{uc_schema_name}/{template_id}/{upload_id}/data.parquet"
    )


def add_audit_columns(
    df, uploaded_by: str, upload_id: str, uploaded_at: datetime
):
    """
    Add the three audit columns to the DataFrame.
    """
    return (
        df
        .withColumn(AUDIT_UPLOADED_BY, F.lit(uploaded_by))
        .withColumn(AUDIT_UPLOAD_ID, F.lit(upload_id))
        .withColumn(
            AUDIT_UPLOADED_AT,
            F.lit(uploaded_at).cast("timestamp"),
        )
    )


def write_to_target(df, fully_qualified_name: str, write_mode: str) -> None:
    """
    Write the DataFrame to the target Delta table.
    """
    if write_mode not in ("append", "overwrite"):
        raise ValueError(f"Unsupported write_mode: {write_mode}")

    (
        df.write
        .format("delta")
        .mode(write_mode)
        .saveAsTable(fully_qualified_name)
    )


def run_upload_write_job(
    template_id: str,
    upload_id: str,
    uploaded_by: str,
    spark_session,
    dbutils,
) -> None:
    """
    Orchestrate the full upload write.

    Args:
        template_id:   UUID of the template
        upload_id:     UUID of the upload_history row
        uploaded_by:   email of the uploader
        spark_session: Spark session (injected for testability)
        dbutils:       DBUtils handle (injected)
    """
    print(
        f"Upload write job starting: "
        f"template_id={template_id} upload_id={upload_id} "
        f"uploaded_by={uploaded_by}"
    )

    # Pin the audit timestamp at job start. Every row written
    # by this batch will carry exactly this value.
    uploaded_at = datetime.now(timezone.utc)
    print(f"  Audit timestamp: {uploaded_at.isoformat()}")

    # Step 1 - resolve target table and write mode from Postgres.

    print("\nFetching template target from PostgreSQL...")
    target = load_template_target(spark_session, dbutils, template_id)
    fqn = target["fully_qualified_name"]
    write_mode = target["write_mode"]
    uc_schema = target["uc_schema_name"]
    print(f"  Target: {fqn}")
    print(f"  Write mode: {write_mode}")

    # Step 2 - read staging Parquet
    staging_path = build_staging_abfss_path(
        dbutils, uc_schema, template_id, upload_id
    )
    print(f"\nReading staging Parquet from: {staging_path}")
    df = spark_session.read.parquet(staging_path)

    # Step 3 - stamp audit columns
    print("\nAdding audit columns...")
    df_with_audit = add_audit_columns(
        df=df,
        uploaded_by=uploaded_by,
        upload_id=upload_id,
        uploaded_at=uploaded_at,
    )

    # Step 4 - write to Delta target
    print(f"\nWriting to {fqn} (mode={write_mode})...")
    write_to_target(df_with_audit, fqn, write_mode)

    print(f"\nUpload write job completed successfully for: {fqn}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Upload write job for Manual File Uploader"
    )
    parser.add_argument(
        "--template_id",
        required=True,
        help="UUID of the template the upload targets",
    )
    parser.add_argument(
        "--upload_id",
        required=True,
        help="UUID of the upload_history row",
    )
    parser.add_argument(
        "--uploaded_by",
        required=True,
        help="Email of the user who performed the upload",
    )
    args = parser.parse_args()

    from pyspark.dbutils import DBUtils
    dbutils = DBUtils(spark)  

    try:
        run_upload_write_job(
            template_id=args.template_id,
            upload_id=args.upload_id,
            uploaded_by=args.uploaded_by,
            spark_session=spark,  
            dbutils=dbutils,
        )
    except Exception as error:
        print(f"\nUpload write job FAILED: {error}")
        traceback.print_exc()
        sys.exit(1)