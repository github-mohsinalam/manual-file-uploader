"""
Template columns router - column configuration management.

Endpoints:
    POST   /templates/{template_id}/columns        Replace all columns
    GET    /templates/{template_id}/columns        List columns
    DELETE /templates/{template_id}/columns/{column_id}    Remove single column

The POST endpoint replaces the entire column list. This matches
the wizard UX where the user can re-upload the sample file mid-flow
and the column configuration starts fresh.

All write endpoints require the template to be in Draft status.
Once submitted, column configuration is locked. Editing columns
of an Active template requires creating a new template version.
"""

from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database.database import get_db
from app.models.template import Template
from app.models.template_column import TemplateColumn
from app.schemas.template_column import (
    TemplateColumnCreate,
    TemplateColumnResponse,
)


router = APIRouter(
    prefix="/templates/{template_id}/columns",
    tags=["template-columns"],
)


# ================================================
# Helpers
# ================================================

def _get_template_or_404(db: Session, template_id: UUID) -> Template:
    """Fetch a template by ID or raise 404."""
    template = db.query(Template).filter(Template.id == template_id).first()
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Template not found: {template_id}",
        )
    return template


def _ensure_draft_status(template: Template) -> None:
    """
    Verify the template is in Draft status.

    Raises 400 if not. Used by all write endpoints.
    """
    if template.status != "Draft":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Cannot modify columns of template in status '{template.status}'. "
                f"Only Draft templates can have columns edited. To edit an "
                f"approved template, create a new version."
            ),
        )


def _check_column_names_unique(columns: List[TemplateColumnCreate]) -> None:
    """
    Verify the submitted columns do not contain duplicate column names.

    The DDL we generate later requires unique column names within
    the table.
    """
    names = [col.column_name for col in columns]
    seen = set()
    duplicates = set()
    for name in names:
        if name in seen:
            duplicates.add(name)
        seen.add(name)

    if duplicates:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Duplicate column names: {sorted(duplicates)}",
        )


# ================================================
# Endpoints
# ================================================

@router.post(
    "",
    response_model=List[TemplateColumnResponse],
    status_code=status.HTTP_201_CREATED,
)
def replace_columns(
    template_id: UUID,
    payload: List[TemplateColumnCreate],
    db: Session = Depends(get_db),
):
    """
    Replace the column list for a template.

    Existing columns are deleted and the provided list is saved.
    column_order is auto-assigned based on position in the list -
    the first column gets order 0, second gets 1, etc.
    """
    template = _get_template_or_404(db, template_id)
    _ensure_draft_status(template)

    if not payload:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Column list cannot be empty",
        )

    _check_column_names_unique(payload)

    # Replace strategy: delete all existing columns first
    db.query(TemplateColumn).filter(
        TemplateColumn.template_id == template_id
    ).delete()

    # Insert the new columns with auto-assigned order
    new_columns = []
    for index, col_data in enumerate(payload):
        column = TemplateColumn(
            template_id=template_id,
            column_name=col_data.column_name,
            display_name=col_data.display_name,
            data_type=col_data.data_type,
            description=col_data.description,
            is_included=col_data.is_included,
            is_pii=col_data.is_pii,
            is_nullable=col_data.is_nullable,
            is_unique=col_data.is_unique,
            column_order=index,
        )
        db.add(column)
        new_columns.append(column)

    db.commit()

    # Refresh each column to get DB-generated values like id
    for column in new_columns:
        db.refresh(column)

    return new_columns


@router.get(
    "",
    response_model=List[TemplateColumnResponse],
)
def list_columns(
    template_id: UUID,
    db: Session = Depends(get_db),
):
    """
    Return all columns for a template, ordered by column_order.

    Available for templates in any status.
    """
    # Verify the template exists - returns 404 if not
    _get_template_or_404(db, template_id)

    return (
        db.query(TemplateColumn)
        .filter(TemplateColumn.template_id == template_id)
        .order_by(TemplateColumn.column_order)
        .all()
    )


@router.delete(
    "/{column_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_column(
    template_id: UUID,
    column_id: UUID,
    db: Session = Depends(get_db),
):
    """
    Delete a single column from a template.

    Only allowed on Draft templates. After deletion the
    column_order values are NOT renumbered - gaps are
    acceptable since position in the DDL is determined by
    sorting on column_order.
    """
    template = _get_template_or_404(db, template_id)
    _ensure_draft_status(template)

    column = (
        db.query(TemplateColumn)
        .filter(
            TemplateColumn.id == column_id,
            TemplateColumn.template_id == template_id,
        )
        .first()
    )

    if not column:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Column not found: {column_id}",
        )

    db.delete(column)
    db.commit()