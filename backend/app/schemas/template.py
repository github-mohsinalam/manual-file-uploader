"""
Pydantic schemas for the Template resource.

Three shapes:
    TemplateCreate    - what the client sends to POST /templates
    TemplateUpdate    - what the client sends to PATCH /templates/{id}
    TemplateResponse  - what the server returns for GET /templates/{id}
"""

from datetime import datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.common import (
    ORMBase,
    IdentifierStr,
    DisplayNameStr,
    DescriptionStr,
)


# --------------------------------------------------
# Create
# --------------------------------------------------
# Sent to POST /templates to create a new Draft template.
# Only the fields the user provides in the first wizard step.
# The rest (id, status, created_by, etc.) are server generated.

class TemplateCreate(BaseModel):
    """Request body for creating a new template."""

    name: IdentifierStr = Field(
        ...,
        description="Technical name - used as table name. Lowercase alphanumeric + underscore, must start with a letter."
    )
    display_name: DisplayNameStr = Field(
        ...,
        description="Human-readable name shown in the UI."
    )
    description: Optional[DescriptionStr] = Field(
        None,
        description="Optional description of what this template is for."
    )
    domain_id: UUID = Field(
        ...,
        description="ID of the domain this template belongs to."
    )


# --------------------------------------------------
# Update
# --------------------------------------------------
# Sent to PATCH /templates/{id}. All fields optional - client
# only sends the ones being updated. A field not present in
# the request is left unchanged in the database.

class TemplateUpdate(BaseModel):
    """Request body for updating a template."""

    display_name: Optional[DisplayNameStr] = None
    description: Optional[DescriptionStr] = None
    file_format: Optional[str] = Field(
        None,
        pattern=r"^(csv|xlsx)$",
        description="File format accepted for uploads."
    )
    delimiter: Optional[str] = Field(
        None,
        max_length=1,
        description="Delimiter character for CSV uploads."
    )
    encoding: Optional[str] = Field(
        None,
        max_length=20,
        description="Character encoding."
    )
    write_mode: Optional[str] = Field(
        None,
        pattern=r"^(append|overwrite)$",
        description="How uploads are written to the Delta table."
    )
    bad_row_threshold: Optional[Decimal] = Field(
        None,
        ge=0,
        le=100,
        description="Maximum percentage of bad rows allowed (0-100)."
    )
    bad_row_action: Optional[str] = Field(
        None,
        pattern=r"^(drop|fail)$",
        description="What to do with bad rows under the threshold."
    )
    reader_group: Optional[str] = Field(
        None,
        max_length=255,
        description="Databricks group to grant SELECT access to."
    )


# --------------------------------------------------
# Response
# --------------------------------------------------
# Returned from GET /templates/{id} and GET /templates.
# Includes server-generated fields like id, status, timestamps.

class TemplateResponse(ORMBase):
    """Response shape for Template endpoints."""

    id: UUID
    name: str
    display_name: str
    description: str | None
    domain_id: UUID
    uc_table_name: str
    fully_qualified_name: str
    file_format: str
    delimiter: str | None
    encoding: str
    write_mode: str
    bad_row_threshold: Decimal
    bad_row_action: str
    reader_group: str | None
    status: str
    version: int
    parent_template_id: UUID | None
    created_by: str
    created_at: datetime
    updated_at: datetime