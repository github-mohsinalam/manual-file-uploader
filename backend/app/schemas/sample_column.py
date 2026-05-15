"""
Pydantic schemas for sample-file parsing.

Returned by POST /templates/parse-sample - the endpoint that
accepts an uploaded sample CSV/XLSX and returns inferred column
metadata for the frontend to prefill the wizard's columns step.

This is a one-shot response. Nothing about it is persisted; the
frontend uses the result to pre-populate form rows that the
user can then edit before saving via the existing
POST /templates/{id}/columns endpoint.
"""

from typing import List

from pydantic import BaseModel, Field


class SampleColumnResponse(BaseModel):
    """A single inferred column from a parsed sample file."""

    column_name: str = Field(
        ...,
        description="Column header as it appears in the file."
    )
    data_type: str = Field(
        ...,
        description=(
            "Inferred data type, mapped to our supported set "
            "(STRING, INTEGER, BIGINT, DOUBLE, BOOLEAN, DATE, TIMESTAMP). "
            "Falls back to STRING for unrecognized types."
        )
    )
    sample_values: List[str] = Field(
        default_factory=list,
        description=(
            "Up to 3 example values from the first rows of the file. "
            "Empty list if the column has no readable values."
        )
    )


class SampleParseResponse(BaseModel):
    """
    Top-level response from POST /templates/parse-sample.

    Wraps the column list in a top-level object so we can extend
    with metadata later (e.g. total row count, parse warnings)
    without breaking the wire shape.
    """

    columns: List[SampleColumnResponse]
    total_rows_scanned: int = Field(
        ...,
        description=(
            "How many rows Polars read for type inference. "
            "Useful for the UI to disclose that inference is "
            "based on a sample, not the full file."
        )
    )