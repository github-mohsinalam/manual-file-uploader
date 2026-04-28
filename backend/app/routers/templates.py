"""
Templates router - CRUD endpoints for template management.

Endpoints:
    POST   /templates                Create new Draft template
    GET    /templates                List templates with filters
    GET    /templates/{id}           Get single template
    PATCH  /templates/{id}           Update template fields
    DELETE /templates/{id}           Delete Draft template

Column, reviewer, submit, and approval endpoints are added
in subsequent tasks. This module focuses on the base CRUD.
"""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status, BackgroundTasks
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.auth.models import User
from app.database.database import get_db
from app.models.domain import Domain
from app.models.template_reviewer import TemplateReviewer
from app.services.approval.submission import submit_template_for_approval
from app.services.approval.emails import send_approval_request_emails
from app.models.template import Template
from app.schemas.template import (
    TemplateCreate,
    TemplateResponse,
    TemplateUpdate,
)


router = APIRouter(
    prefix="/templates",
    tags=["templates"],
)


# ================================================
# Helpers
# ================================================

def _get_template_or_404(db: Session, template_id: UUID) -> Template:
    """
    Fetch a template by ID or raise 404.

    Used by every endpoint that operates on a specific template.
    """
    template = db.query(Template).filter(Template.id == template_id).first()
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Template not found: {template_id}",
        )
    return template


def _check_template_name_unique(
    db: Session,
    name: str,
    exclude_id: Optional[UUID] = None,
) -> None:
    """
    Verify no other template uses the given name.

    Raises 400 if a duplicate exists. The exclude_id parameter
    lets us check uniqueness while ignoring an existing template
    (useful when updating).
    """
    query = db.query(Template).filter(Template.name == name)
    if exclude_id:
        query = query.filter(Template.id != exclude_id)
    if query.first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Template with name '{name}' already exists",
        )


# ================================================
# Endpoints
# ================================================

@router.post(
    "",
    response_model=TemplateResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_template(
    payload: TemplateCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Create a new Draft template.

    The user provides only the basic identification fields.
    The server fills in everything else with defaults that the
    user can edit later via PATCH /templates/{id}.
    """
    # Verify the domain exists - we need uc_schema_name
    domain = db.query(Domain).filter(Domain.id == payload.domain_id).first()
    if not domain:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Domain not found: {payload.domain_id}",
        )

    # Verify the template name is unique
    _check_template_name_unique(db, payload.name)

    # Build the SQLAlchemy model with derived and default fields
    template = Template(
        name=payload.name,
        display_name=payload.display_name,
        description=payload.description,
        domain_id=payload.domain_id,

        # Derived from the name and domain
        uc_table_name=payload.name,
        fully_qualified_name=f"manualuploads.{domain.uc_schema_name}.{payload.name}",

        # Default file format settings - user adjusts via PATCH later
        file_format="csv",
        delimiter=",",
        encoding="UTF-8",

        # Default write behavior
        write_mode="append",
        bad_row_threshold=5.00,
        bad_row_action="drop",

        # Reader group is null until set by the user
        reader_group=None,

        # Lifecycle defaults
        status="Draft",
        version=1,
        parent_template_id=None,

        # Audit
        created_by=current_user.email,
    )

    db.add(template)
    db.commit()
    db.refresh(template)

    return template


@router.get("", response_model=list[TemplateResponse])
def list_templates(
    db: Session = Depends(get_db),
    template_status: Optional[str] = Query(
        None,
        alias="status",
        description="Filter by status (Draft, Pending Approval, Active, etc.)",
    ),
    domain_id: Optional[UUID] = Query(
        None,
        description="Filter by domain.",
    ),
    created_by: Optional[str] = Query(
        None,
        description="Filter by creator email.",
    ),
    search: Optional[str] = Query(
        None,
        description="Partial match on template name or display_name.",
    ),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    """
    List templates with optional filters and pagination.

    Multiple filters can be combined - they apply with AND
    semantics. Results are ordered by created_at descending so
    the newest templates appear first.
    """
    query = db.query(Template)

    if template_status:
        query = query.filter(Template.status == template_status)

    if domain_id:
        query = query.filter(Template.domain_id == domain_id)

    if created_by:
        query = query.filter(Template.created_by == created_by)

    if search:
        # Case-insensitive partial match on name or display_name
        pattern = f"%{search.lower()}%"
        query = query.filter(
            (Template.name.ilike(pattern)) |
            (Template.display_name.ilike(pattern))
        )

    return (
        query
        .order_by(Template.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )


@router.get("/{template_id}", response_model=TemplateResponse)
def get_template(
    template_id: UUID,
    db: Session = Depends(get_db),
):
    """
    Get a single template by ID.
    
    Returns only the Template fields. Use the column and
    reviewer endpoints to fetch related data separately.
    """
    return _get_template_or_404(db, template_id)


@router.patch("/{template_id}", response_model=TemplateResponse)
def update_template(
    template_id: UUID,
    payload: TemplateUpdate,
    db: Session = Depends(get_db),
):
    """
    Update template fields.

    Only fields present in the request are updated. Other fields
    are left unchanged. Cannot update templates that are not in
    Draft status - use the new-version flow for approved templates.
    """
    template = _get_template_or_404(db, template_id)

    # Only Draft templates can be edited freely
    if template.status != "Draft":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Cannot update template in status '{template.status}'. "
                f"Only Draft templates can be edited. To edit an approved "
                f"template, create a new version."
            ),
        )

    # Apply only the fields the client actually sent
    updates = payload.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(template, field, value)

    db.commit()
    db.refresh(template)
    return template


@router.delete(
    "/{template_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_template(
    template_id: UUID,
    db: Session = Depends(get_db),
):
    """
    Delete a Draft template permanently.

    Only Draft templates can be deleted. Templates in any other
    status must go through proper lifecycle transitions
    (deprecation, etc.) and cannot be removed via DELETE.
    """
    template = _get_template_or_404(db, template_id)

    if template.status != "Draft":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Cannot delete template in status '{template.status}'. "
                f"Only Draft templates can be deleted."
            ),
        )

    db.delete(template)
    db.commit()
    # 204 returns no body

@router.post(
    "/{template_id}/submit",
    response_model=TemplateResponse,
)
def submit_template(
    template_id: UUID,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Submit a Draft template for approval.

    Validates the template has columns and at least one required
    reviewer, then:
        - Creates approval rows with secure single-use tokens
        - Transitions template status to Pending Approval
        - Sends approval request emails to all reviewers (async)

    Returns the updated template. Emails are dispatched in the
    background after the response is sent.
    """
    # Validate and submit - returns updated template + approval rows
    template, approvals = submit_template_for_approval(db, template_id)

    # Fetch the domain for the email content
    domain = db.query(Domain).filter(Domain.id == template.domain_id).first()

    # Fetch reviewers to know which are required vs optional
    reviewers = (
        db.query(TemplateReviewer)
        .filter(TemplateReviewer.template_id == template.id)
        .all()
    )
    reviewer_types_by_email = {
        r.reviewer_email: r.reviewer_type for r in reviewers
    }

    # Schedule emails to send in the background
    # The user's HTTP response goes out immediately - emails
    # are dispatched after that.
    background_tasks.add_task(
        send_approval_request_emails,
        template=template,
        approvals=approvals,
        creator_name=current_user.name,
        creator_email=current_user.email,
        domain=domain,
        reviewer_types_by_email=reviewer_types_by_email,
    )

    return template