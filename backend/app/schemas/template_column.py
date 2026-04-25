"""
Pydantic schemas for TemplateColumn resources.

Columns are created as a batch for a template - not individually.
So the Create schema represents a single column, and the
endpoint accepts a list of these.
"""

from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.common import (
    ORMBase,
    IdentifierStr,
    DescriptionStr,
)


# Allowed Unity Catalog data types for template columns.
# Matches the subset of types we support in the DDL builder.
ALLOWED_DATA_TYPES = r"^(STRING|INTEGER|BIGINT|DOUBLE|DECIMAL|BOOLEAN|DATE|TIMESTAMP)$"


class TemplateColumnCreate(BaseModel):
    """
    Request body for creating a single column within a template.

    POST /templates/{id}/columns accepts a list of these.
    """

    column_name: IdentifierStr = Field(
        ...,
        description="Technical column name. Must match file header exactly."
    )
    display_name: Optional[str] = Field(
        None,
        max_length=100,
        description="Human-readable column name for the UI."
    )
    data_type: str = Field(
        ...,
        pattern=ALLOWED_DATA_TYPES,
        description="Unity Catalog data type. Must be one of the supported types."
    )
    description: Optional[DescriptionStr] = None
    is_included: bool = Field(
        True,
        description="Whether this column is included in the target table."
    )
    is_pii: bool = Field(
        False,
        description="Mark as PII to apply column masking."
    )
    is_nullable: bool = Field(
        True,
        description="Whether NULL values are allowed."
    )
    is_unique: bool = Field(
        False,
        description="Enforce uniqueness. Uniqueness is enforced at the Polars validation layer, not Delta."
    )
    column_order: int = Field(
        ...,
        ge=0,
        description="Zero-based position in the target table schema."
    )


class TemplateColumnResponse(ORMBase):
    """Response shape for template columns."""

    id: UUID
    template_id: UUID
    column_name: str
    display_name: str | None
    data_type: str
    description: str | None
    is_included: bool
    is_pii: bool
    is_nullable: bool
    is_unique: bool
    column_order: int