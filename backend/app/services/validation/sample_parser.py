"""
Sample file parser - one-shot inference of column schema from
a user-uploaded CSV or XLSX.

This is intentionally simple. The user has uploaded a sample of
their data; we want to suggest column names and types so they do
not have to type 30 column definitions by hand. The user can
always override our suggestions in the UI.

We use Polars for both formats:
  - CSV: native Polars reader
  - XLSX: Polars uses fastexcel under the hood (same as the
    validation layer)

Polars samples up to the first 1000 rows for type inference,
which is plenty.
"""

import io
import logging
from typing import List

import polars as pl

from app.schemas.sample_column import (
    SampleColumnResponse,
    SampleParseResponse,
)

logger = logging.getLogger(__name__)


# How many rows Polars looks at to infer types. Polars' default
# is 100; we raise it because real-world data often has nulls in
# the first 100 rows that mask the actual type.
INFER_SCHEMA_LENGTH = 1000

# How many sample values to return per column in the response.
SAMPLE_VALUES_PER_COLUMN = 3


# Mapping from Polars dtypes to our supported ColumnDataType
# values. Anything not listed falls back to STRING.
def _map_polars_dtype(dtype: pl.DataType) -> str:
    """Translate a Polars dtype to our ColumnDataType string."""
    if dtype in (pl.Int64, pl.Int32, pl.UInt64, pl.UInt32):
        return "BIGINT"
    if dtype in (pl.Int16, pl.Int8, pl.UInt16, pl.UInt8):
        return "INTEGER"
    if dtype in (pl.Float64, pl.Float32):
        return "DOUBLE"
    if dtype == pl.Boolean:
        return "BOOLEAN"
    if dtype == pl.Date:
        return "DATE"
    if isinstance(dtype, pl.Datetime):
        return "TIMESTAMP"
    if dtype == pl.Utf8:
        return "STRING"
    # Decimal, Categorical, List, Struct, Null - all collapse to STRING
    return "STRING"


def _extract_sample_values(
    df: pl.DataFrame, column_name: str
) -> List[str]:
    """
    Pull up to N non-null sample values from a column as strings.

    The UI uses these to let the user verify column inference
    matches their actual data.
    """
    column = df[column_name].drop_nulls().head(SAMPLE_VALUES_PER_COLUMN)
    return [str(v) for v in column.to_list()]


def parse_sample_file(
    file_bytes: bytes,
    file_extension: str,
) -> SampleParseResponse:
    """
    Parse a sample CSV or XLSX file and return inferred columns.

    Args:
        file_bytes: raw bytes of the uploaded file
        file_extension: 'csv' or 'xlsx' (lowercased, no dot)

    Returns:
        SampleParseResponse with one entry per inferred column.

    Raises:
        ValueError: if the file is unreadable, empty, or in an
        unsupported format. The router converts this to a 400.
    """
    if not file_bytes:
        raise ValueError("Uploaded file is empty.")

    extension = file_extension.lower().lstrip(".")

    # Read into a Polars DataFrame.
    # io.BytesIO wraps the raw bytes so Polars can stream-read.
    buffer = io.BytesIO(file_bytes)

    if extension == "csv":
        try:
            df = pl.read_csv(
                buffer,
                infer_schema_length=INFER_SCHEMA_LENGTH,
            )
        except Exception as e:
            logger.warning(f"Polars failed to parse CSV: {e}")
            raise ValueError(f"Could not parse CSV file: {e}") from e
    elif extension == "xlsx":
        try:
            df = pl.read_excel(
                buffer,
                # fastexcel reads everything as string by default
                # unless we ask it to infer. infer_schema_length
                # tells it to look at this many rows.
                infer_schema_length=INFER_SCHEMA_LENGTH,
            )
        except Exception as e:
            logger.warning(f"Polars failed to parse XLSX: {e}")
            raise ValueError(f"Could not parse Excel file: {e}") from e
    else:
        raise ValueError(
            f"Unsupported file format: '{extension}'. "
            f"Supported formats are 'csv' and 'xlsx'."
        )

    if len(df.columns) == 0:
        raise ValueError("Parsed file contains no columns.")

    # Build the response from the inferred schema.
    columns: List[SampleColumnResponse] = []
    for column_name in df.columns:
        dtype = df.schema[column_name]
        columns.append(
            SampleColumnResponse(
                column_name=column_name,
                data_type=_map_polars_dtype(dtype),
                sample_values=_extract_sample_values(df, column_name),
            )
        )

    return SampleParseResponse(
        columns=columns,
        total_rows_scanned=min(len(df), INFER_SCHEMA_LENGTH),
    )