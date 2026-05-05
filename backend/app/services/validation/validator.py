"""
Polars validation engine - Layer 1 of the upload pipeline.

What this module does
---------------------
Takes the raw bytes of an uploaded file plus the template
configuration that drives validation, and returns a
ValidationResult that holds:

  - the clean DataFrame (rows that passed every check)
  - the list of cell-level errors found
  - summary counts (total / valid / invalid)

What this module does NOT do
----------------------------
- Touch the database
- Touch ADLS (the caller already has the bytes in memory)
- Apply the bad-row threshold or write staging Parquet
- Trigger any Databricks job

This is a deliberate split. Keeping the validator pure makes
it trivially testable - construct a Template + columns in
Python, hand it some bytes, assert on the result. No fixtures,
no mocking ADLS, no DB session.

Validation order (per implementation_decisions.md section 5.3)
-------------------------------------------------------------
1. Read the file into Polars (CSV via native reader, XLSX via
   fastexcel under the hood).
2. SCHEMA validation - column names match the template exactly.
   On failure we bail immediately with SCHEMA_MISMATCH errors;
   constraint validation would be meaningless on a misaligned
   frame .
3. Drop columns where is_included=False, reorder to template
   order. Constraint validation only sees the columns the
   user actually configured.
4. TYPE validation - attempt to cast each non-STRING column
   to its target dtype. A cell that was non-null before the
   cast and null after it is a TYPE_MISMATCH.
5. NOT NULL validation - rows where is_nullable=False and
   the (post-cast) value is null. We do NOT double-report
   a cell that already failed TYPE_MISMATCH.
6. UNIQUE validation - rows in a duplicate group on a column
   marked is_unique=True. Nulls are excluded from the
   duplicate check, matching SQL's default UNIQUE semantics.

Error capping
-------------
A 1M-row file with every row bad would otherwise
write 1M rows to upload_validation_errors and blow up the
JSON response. We cap at MAX_ERRORS and set
errors_truncated=True so the caller can surface that fact.
The clean DataFrame is still computed correctly using the
full set of bad row numbers - the cap only affects what we
remember for reporting.
"""

import io
import logging
from dataclasses import dataclass, field
from typing import Optional

import polars as pl

from app.models.template import Template
from app.models.template_column import TemplateColumn
from app.schemas.validation import ValidationError

logger = logging.getLogger(__name__)


# ============================================================
# Constants
# ============================================================

# Mapping from template.data_type values (constrained by the
# SQL CHECK on template_columns.data_type) to Polars dtypes.
#
# Any data_type added to the SQL constraint must also appear
# here or schema validation will raise KeyError.
#
# Notes on choices:
# - INTEGER maps to Int32, BIGINT/LONG to Int64. This matches
#   how typical SQL engines size them.
# - DECIMAL uses precision=38, scale=18. Polars Decimal
#   requires precision and scale to be set explicitly in
#   1.38; these defaults are generous and rarely overflow.
#   The actual storage type in Unity Catalog is set by the
#   DDL job, not by us - we just need to confirm the string
#   parses as a decimal.
# - DATE and TIMESTAMP rely on Polars' built-in ISO-8601
#   parsers. Non-ISO formats (DD/MM/YYYY etc.) will surface
#   as TYPE_MISMATCH. Format flexibility is a future
#   improvement.
DTYPE_MAP: dict[str, pl.DataType] = {
    "STRING":    pl.String,
    "INTEGER":   pl.Int32,
    "BIGINT":    pl.Int64,
    "LONG":      pl.Int64,
    "DOUBLE":    pl.Float64,
    "DECIMAL":   pl.Decimal(precision=38, scale=18),
    "BOOLEAN":   pl.Boolean,  # Handled specially via _bool_cast_expr
    "DATE":      pl.Date,
    "TIMESTAMP": pl.Datetime,
}


# Strings accepted as boolean True. Compared against the
# lowercased, trimmed value so capitalisation and surrounding
# whitespace are forgiven. Anything outside this set (and the
# False set below) becomes null and surfaces as TYPE_MISMATCH.
BOOL_TRUE_TOKENS = ["true", "t", "yes", "y", "1"]
BOOL_FALSE_TOKENS = ["false", "f", "no", "n", "0"]


# Maximum number of cell-level errors to record per upload.
# Above this, we stop appending to the errors list and set
# errors_truncated=True. The clean DataFrame is still computed
# correctly using all bad rows - the cap only limits what we
# remember for the error report.
MAX_ERRORS = 1000


# Strings that should be treated as null in CSVs. Polars
# treats unquoted empty fields as null by default; this list
# also catches literal "NULL"/"null" tokens that some users
# put in mapping files.
CSV_NULL_TOKENS = ["", "NULL", "null"]


# Internal column name used to track 1-based row numbers
# through Polars transformations. Prefixed with __mfu_ so it
# cannot collide with a real user column.
ROW_INDEX_COL = "__mfu_row_idx"


# ============================================================
# Result type
# ============================================================

@dataclass
class ValidationResult:
    """
    In-memory result of running the Polars validation engine.

    This is a dataclass rather than a Pydantic model because it
    holds a polars.DataFrame, which is not JSON-serialisable
    and never crosses an API boundary. The Pydantic wire
    format for individual errors lives in
    app.schemas.validation.ValidationError.

    Fields:
        total_rows         input row count
        valid_rows         rows that passed every check
        invalid_rows       rows that failed at least one check
                           (= total_rows - valid_rows)
        errors             cell-level error rows (capped at
                           MAX_ERRORS)
        errors_truncated   True when the cap was hit and the
                           errors list does not contain every
                           bad cell. valid_rows / invalid_rows
                           remain accurate regardless.
        clean_dataframe    rows that passed every check, in
                           template column order, with
                           target dtypes applied. None when
                           schema validation failed.
        schema_failed      True when SCHEMA_MISMATCH errors
                           were raised and constraint
                           validation was skipped.
    """

    total_rows: int
    valid_rows: int
    invalid_rows: int
    errors: list[ValidationError] = field(default_factory=list)
    errors_truncated: bool = False
    clean_dataframe: Optional[pl.DataFrame] = None
    schema_failed: bool = False


# ============================================================
# Public entry point
# ============================================================

def validate_file(
    file_bytes: bytes,
    template: Template,
    columns: list[TemplateColumn],
) -> ValidationResult:
    """
    Run schema and constraint validation on uploaded file bytes.

    Args:
        file_bytes:  raw uploaded file content. The caller is
                     responsible for size enforcement; this
                     function does not check.
        template:    Template ORM row whose file_format,
                     delimiter, encoding fields drive how the
                     bytes are parsed.
        columns:     TemplateColumn ORM rows for this template.
                     The full list including is_included=False
                     entries; the validator filters them out
                     internally.

    Returns:
        ValidationResult. Always returned - this function does
        not raise on validation failure. Exceptions are reserved
        for unexpected programming errors.
    """
    logger.info(
        "Starting validation: format=%s columns=%d size=%d",
        template.file_format, len(columns), len(file_bytes),
    )

    # Step 1 - parse the file into Polars.
    # Two failure modes are surfaced here as schema failure:
    #   - Encoding mismatch (template says utf-8, file is
    #     utf-16 etc.) - reported as ENCODING_ERROR.
    #   - Anything else (corrupt CSV, ragged rows, malformed
    #     XLSX, mismatched quotes) - reported as PARSE_ERROR.
    # In both cases there is no DataFrame to validate, so we
    # treat the upload like schema failure: skip constraint
    # checks, terminate with a single error row.
    try:
        df = _read_file(file_bytes, template)
    except UnicodeDecodeError as e:
        logger.warning("Encoding error during file read: %s", e)
        return ValidationResult(
            total_rows=0,
            valid_rows=0,
            invalid_rows=0,
            errors=[ValidationError(
                row_number=0,
                column_name="",
                error_type="ENCODING_ERROR",
                error_message=(
                    f"File could not be decoded as "
                    f"{template.encoding}. Verify the template "
                    f"encoding matches the file."
                ),
                raw_value=None,
            )],
            schema_failed=True,
        )
    except Exception as e:
        # Catches polars.exceptions.ComputeError, fastexcel
        # errors, IO errors, and any other parse failure.
        # We deliberately catch broadly because Polars/fastexcel
        # do not expose a single base exception class we can
        # narrow on, and the user-facing outcome is the same
        # regardless of which library complained: the file
        # could not be parsed.
        #
        # The exception message is included verbatim in
        # error_message so the user sees what Polars said.
        # That can be technical (e.g. "found more fields than
        # defined in schema") but it is more useful than a
        # generic "parse failed".
        logger.warning(
            "Parse error during file read: %s", e, exc_info=True,
        )
        return ValidationResult(
            total_rows=0,
            valid_rows=0,
            invalid_rows=0,
            errors=[ValidationError(
                row_number=0,
                column_name="",
                error_type="PARSE_ERROR",
                error_message=(
                    f"File could not be parsed as "
                    f"{template.file_format}: {e}"
                ),
                raw_value=None,
            )],
            schema_failed=True,
        )
    
    total_rows = df.height
    logger.info("File parsed: rows=%d columns=%s", total_rows, df.columns)

    # Step 2 - schema validation; bail on failure
    schema_errors = _validate_schema(df, columns)
    if schema_errors:
        logger.warning(
            "Schema validation failed with %d errors", len(schema_errors)
        )
        return ValidationResult(
            total_rows=total_rows,
            valid_rows=0,
            invalid_rows=total_rows,
            errors=schema_errors,
            schema_failed=True,
        )

    # Step 3 - keep only included columns, in template order.
    # Templates can declare columns the user does not want
    # uploaded; constraint validation should not see them.
    included_columns = sorted(
        [c for c in columns if c.is_included],
        key=lambda c: c.column_order,
    )
    df = df.select([c.column_name for c in included_columns])

    # Add a 1-based row index that survives every subsequent
    # operation. Used to report row numbers in errors and to
    # build the clean DataFrame at the end.
    df = df.with_row_index(name=ROW_INDEX_COL, offset=1)

    # Step 4 - type validation + cast.
    # _apply_types returns the casted DataFrame and the list
    # of TYPE_MISMATCH errors discovered.
    df_typed, type_errors = _apply_types(df, included_columns)

    # Step 5 - NOT NULL.
    # Excluding cells already flagged as TYPE_MISMATCH avoids
    # double-reporting the same broken cell.
    type_error_keys = {(e.row_number, e.column_name) for e in type_errors}
    null_errors = _validate_not_null(
        df_typed, included_columns, type_error_keys
    )

    # Step 6 - UNIQUE.
    unique_errors = _validate_unique(df_typed, included_columns)

    # Combine errors with the cap. We collect ALL bad row
    # numbers for the clean-frame filter even if we drop some
    # error rows for the report.
    all_errors_iter = type_errors + null_errors + unique_errors
    bad_row_numbers = {e.row_number for e in all_errors_iter}

    if len(all_errors_iter) > MAX_ERRORS:
        errors = all_errors_iter[:MAX_ERRORS]
        errors_truncated = True
        logger.warning(
            "Validation errors truncated: %d found, %d kept",
            len(all_errors_iter), MAX_ERRORS,
        )
    else:
        errors = all_errors_iter
        errors_truncated = False

    # Step 7 - build clean DataFrame.
    # Drop the row-index column so downstream consumers see
    # only the template's columns.
    clean_df = (
        df_typed
        .filter(~pl.col(ROW_INDEX_COL).is_in(list(bad_row_numbers)))
        .drop(ROW_INDEX_COL)
    )

    invalid_rows = len(bad_row_numbers)
    valid_rows = total_rows - invalid_rows

    logger.info(
        "Validation complete: total=%d valid=%d invalid=%d errors=%d (truncated=%s)",
        total_rows, valid_rows, invalid_rows, len(errors), errors_truncated,
    )

    return ValidationResult(
        total_rows=total_rows,
        valid_rows=valid_rows,
        invalid_rows=invalid_rows,
        errors=errors,
        errors_truncated=errors_truncated,
        clean_dataframe=clean_df,
    )


# ============================================================
# File parsing
# ============================================================

def _read_file(file_bytes: bytes, template: Template) -> pl.DataFrame:
    """
    Parse the raw bytes into a Polars DataFrame with every
    column typed as String.

    Reading everything as String first gives the type-validation
    step a uniform starting point - we attempt every cast
    ourselves so we can pinpoint which cell failed. Letting
    Polars infer types up front would hide that information.

    For CSV: uses the native reader with the delimiter and
    encoding from the template. Empty fields and the literal
    tokens NULL/null are treated as null so downstream
    NOT NULL checks fire correctly.

    For XLSX: read with default Polars/fastexcel behaviour,
    then cast every column to String. Excel cells already
    carry typed values so we cannot avoid the round-trip
    through native types - but we normalise immediately.
    """
    buf = io.BytesIO(file_bytes)

    if template.file_format == "csv":
        return pl.read_csv(
            buf,
            separator=template.delimiter,
            encoding=template.encoding,
            # infer_schema_length=0 forces every column to be
            # String. Polars then leaves the values exactly as
            # they appear in the file (modulo null_values).
            infer_schema_length=0,
            null_values=CSV_NULL_TOKENS,
            # Quote handling: standard double-quote, allowing
            # embedded delimiters in quoted fields.
            quote_char='"',
        )

    if template.file_format == "xlsx":
        df = pl.read_excel(buf)
        # Normalise to all-String. read_excel returns native
        # types because that is how Excel stores them; we want
        # the same starting point as CSV so the type-validation
        # step is uniform.
        return df.with_columns([
            pl.col(c).cast(pl.String) for c in df.columns
        ])

    # Should never reach here - the SQL CHECK constraint on
    # templates.file_format restricts to csv/xlsx, but defend
    # against drift.
    raise ValueError(
        f"Unsupported file_format on template: {template.file_format}"
    )


# ============================================================
# Step 2 - schema validation
# ============================================================

def _validate_schema(
    df: pl.DataFrame, columns: list[TemplateColumn]
) -> list[ValidationError]:
    """
    Verify the file has exactly the columns the template
    expects.

    Two failure modes:
      - missing columns (template wants a column the file
        does not have)
      - extra columns (file has a column the template never
        configured)

    We do NOT compare order.The template stores its own column_order; we honour
    that on output regardless of how the input was ordered.

    Returns one ValidationError per offending column. If both
    sides have offenders, both lists are returned.
    """
    file_cols = set(df.columns)
    template_cols = {c.column_name for c in columns}

    missing = template_cols - file_cols
    extra = file_cols - template_cols

    errors: list[ValidationError] = []

    for col_name in sorted(missing):
        errors.append(ValidationError(
            row_number=0,
            column_name=col_name,
            error_type="SCHEMA_MISMATCH",
            error_message=(
                f"Column '{col_name}' is required by the template "
                f"but is missing from the file."
            ),
            raw_value=None,
        ))

    for col_name in sorted(extra):
        errors.append(ValidationError(
            row_number=0,
            column_name=col_name,
            error_type="SCHEMA_MISMATCH",
            error_message=(
                f"Column '{col_name}' is present in the file but "
                f"is not configured on the template."
            ),
            raw_value=None,
        ))

    return errors


# ============================================================
# Step 4 - type validation
# ============================================================

def _bool_cast_expr(col_name: str) -> pl.Expr:
    """
    Build a Polars Expression that casts a String column to
    Boolean by recognising common truthy and falsy tokens.

    Comparison is done on the lowercased, whitespace-trimmed
    value, so 'TRUE', 'true', '  Yes ', '0' are all handled.
    Tokens outside both sets become null - which the cell-diff
    logic in _apply_types catches and reports as TYPE_MISMATCH.

    Polars 1.38 does not support a direct Utf8 -> Boolean cast,
    so we cannot rely on the same .cast(strict=False) pattern
    used for numeric and temporal types.
    """
    lower = (
        pl.col(col_name)
        .str.to_lowercase()
        .str.strip_chars()
    )
    return (
        pl.when(lower.is_in(BOOL_TRUE_TOKENS)).then(pl.lit(True))
        .when(lower.is_in(BOOL_FALSE_TOKENS)).then(pl.lit(False))
        .otherwise(pl.lit(None, dtype=pl.Boolean))
        .alias(col_name)
    )


def _apply_types(
    df: pl.DataFrame, columns: list[TemplateColumn]
) -> tuple[pl.DataFrame, list[ValidationError]]:
    """
    Attempt to cast each non-STRING column to its target dtype.
    Returns the casted DataFrame plus a list of TYPE_MISMATCH
    errors for cells that could not be cast.

    Detection strategy:
      pre  = original String value
      post = cast(target_dtype, strict=False)
      A cell is a TYPE_MISMATCH iff pre is non-null and post
      is null. The non-null check on pre is what distinguishes
      'value present but malformed' (TYPE_MISMATCH) from
      'value missing' (handled by the NOT NULL step).

    The casted DataFrame keeps the row-index column so later
    steps can still address rows by number.
    """
    # Pass 1 - build the casted DataFrame using only Expressions.
    cast_exprs: list[pl.Expr] = [pl.col(ROW_INDEX_COL)]
    for col in columns:
        if col.data_type == "STRING":
            cast_exprs.append(pl.col(col.column_name))
            continue

        if col.data_type == "BOOLEAN":
            # Polars cannot cast String -> Boolean directly in
            # 1.38. Map known truthy/falsy tokens explicitly;
            # anything else becomes null and is reported as
            # TYPE_MISMATCH below by the same diff logic that
            # handles every other type.
            cast_exprs.append(_bool_cast_expr(col.column_name))
            continue

        target_dtype = DTYPE_MAP[col.data_type]
        cast_exprs.append(
            pl.col(col.column_name)
            .cast(target_dtype, strict=False)
            .alias(col.column_name)
        )

    df_typed = df.select(cast_exprs)

    # Pass 2 - diff pre and post per column to find casts that
    # silently produced a null. Done after the full DataFrame
    # is built so each iteration is a simple two-Series
    # comparison rather than a per-column DataFrame rebuild.
    errors: list[ValidationError] = []
    for col in columns:
        if col.data_type == "STRING":
            continue

        pre = df.get_column(col.column_name)         # String
        post = df_typed.get_column(col.column_name)  # target dtype

        bad_mask = pre.is_not_null() & post.is_null()
        if not bad_mask.any():
            continue

        bad_row_nums = df.get_column(ROW_INDEX_COL).filter(bad_mask)
        bad_raw_values = pre.filter(bad_mask)

        for row_num, raw in zip(bad_row_nums, bad_raw_values):
            errors.append(ValidationError(
                row_number=int(row_num),
                column_name=col.column_name,
                error_type="TYPE_MISMATCH",
                error_message=(
                    f"Value cannot be parsed as {col.data_type}."
                ),
                raw_value=raw,
            ))

    return df_typed, errors


# ============================================================
# Step 5 - NOT NULL validation
# ============================================================

def _validate_not_null(
    df: pl.DataFrame,
    columns: list[TemplateColumn],
    type_error_keys: set[tuple[int, str]],
) -> list[ValidationError]:
    """
    For each column where is_nullable=False, find rows whose
    value is null and emit a NOT_NULL error.

    Cells already flagged as TYPE_MISMATCH (in type_error_keys)
    are skipped to avoid double-reporting. The user fixes the
    type and the null disappears; reporting both is just noise.
    """
    errors: list[ValidationError] = []

    for col in columns:
        if col.is_nullable:
            continue

        series = df.get_column(col.column_name)
        null_mask = series.is_null()

        if not null_mask.any():
            continue

        bad_indices = df.filter(null_mask).get_column(ROW_INDEX_COL)
        for row_num in bad_indices:
            row_num_int = int(row_num)
            if (row_num_int, col.column_name) in type_error_keys:
                # Already reported as TYPE_MISMATCH - skip.
                continue

            errors.append(ValidationError(
                row_number=row_num_int,
                column_name=col.column_name,
                error_type="NOT_NULL",
                error_message=(
                    f"Column '{col.column_name}' is required but "
                    f"the value is empty."
                ),
                raw_value=None,
            ))

    return errors


# ============================================================
# Step 6 - UNIQUE validation
# ============================================================

def _validate_unique(
    df: pl.DataFrame, columns: list[TemplateColumn]
) -> list[ValidationError]:
    """
    For each column where is_unique=True, find rows that are
    part of a duplicate group and emit a UNIQUE error per
    affected row.

    Nulls are excluded from the duplicate check, matching the
    SQL convention that NULL values are distinct under a
    UNIQUE constraint. Multiple null rows do NOT count as
    duplicates of each other. If the user also wants null to
    be rejected they should set is_nullable=False as well.

    All members of a duplicate group are flagged - we do not
    keep the first and reject the rest, because the user
    needs to see the full set to decide which to keep.
    """
    errors: list[ValidationError] = []

    for col in columns:
        if not col.is_unique:
            continue

        series = df.get_column(col.column_name)

        # is_duplicated returns True for every row whose value
        # appears more than once. Combined with is_not_null we
        # get exactly the rows we want to flag.
        dup_mask = series.is_duplicated() & series.is_not_null()

        if not dup_mask.any():
            continue

        bad_rows = df.filter(dup_mask)
        for row_num, raw in zip(
            bad_rows.get_column(ROW_INDEX_COL),
            bad_rows.get_column(col.column_name),
        ):
            errors.append(ValidationError(
                row_number=int(row_num),
                column_name=col.column_name,
                error_type="UNIQUE",
                error_message=(
                    f"Duplicate value in column '{col.column_name}'. "
                    f"This column is configured to be unique."
                ),
                # Cast post-cast value back to string for
                # reporting. The dtype could be anything
                # (Int64, Decimal, Date) so str() is the
                # simplest universal representation.
                raw_value=str(raw),
            ))

    return errors