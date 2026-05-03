"""
Uploads router - file upload endpoints.

Endpoints:
    POST /uploads               Upload a file for an Approved template

"""

import logging
from pathlib import Path
from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    UploadFile,
    status,
)
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.auth.models import User
from app.core.config import settings
from app.database.database import get_db
from app.models.domain import Domain
from app.models.template import Template
from app.models.upload_history import UploadHistory
from app.schemas.upload_history import UploadSummary
from app.services.storage.storage_service import (
    build_upload_path,
    storage_service,
)

from app.services.validation import run_validation_phase

logger = logging.getLogger(__name__)


router = APIRouter(
    prefix="/uploads",
    tags=["uploads"],
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


def _ensure_template_approved(template: Template) -> None:
    """
    Verify the template is in Approved status.

    Only Approved templates have their UC table provisioned and
    are ready to receive uploads.
    """
    if template.status != "Approved":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Template is in status '{template.status}'. "
                f"Only Approved templates can receive file uploads."
            ),
        )


def _validate_file_extension(
    filename: str, expected_format: str
) -> None:
    """
    Verify the uploaded file extension matches the template format.

    Args:
        filename: The original filename (e.g. "regions.csv")
        expected_format: The template's file_format (e.g. "csv")

    Raises 400 if the extension does not match.
    """
    if not filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file has no name",
        )

    ext = Path(filename).suffix.lower().lstrip(".")
    if ext != expected_format.lower():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Template expects '{expected_format}' files but the "
                f"uploaded file has extension '.{ext}'"
            ),
        )


def _enforce_size_limit(file_bytes: bytes) -> None:
    """
    Verify the uploaded file is under the configured size limit.
    """
    size_mb = len(file_bytes) / (1024 * 1024)
    if size_mb > settings.max_file_size_mb:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=(
                f"File is {size_mb:.1f} MB - exceeds the limit of "
                f"{settings.max_file_size_mb} MB."
            ),
        )


# ================================================
# Endpoints
# ================================================

@router.post(
    "",
    response_model=UploadSummary,
    status_code=status.HTTP_201_CREATED,
)
def upload_file(
    template_id: UUID = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Upload a file against an Approved template.
    
    """
    # Step 1: Validate template
    template = _get_template_or_404(db, template_id)
    _ensure_template_approved(template)

    # Step 2: Validate file format matches template
    _validate_file_extension(file.filename, template.file_format)

    # Step 3: Read file into memory and enforce size
    file_bytes = file.file.read()
    _enforce_size_limit(file_bytes)

    # Step 4: Create upload_history row
    upload = UploadHistory(
        template_id=template.id,
        uploaded_by=current_user.email,
        original_filename=file.filename,
        file_size_bytes=len(file_bytes),
        status="in_progress",
    )
    db.add(upload)
    db.commit()
    db.refresh(upload)

    logger.info(
        f"Upload started: id={upload.id} template={template.id} "
        f"user={current_user.email} filename={file.filename} "
        f"size={len(file_bytes)} bytes"
    )

    # Step 5: Upload to ADLS Gen2 storage
    domain = (
        db.query(Domain).filter(Domain.id == template.domain_id).first()
    )

    storage_path = build_upload_path(
        domain_uc_schema_name=domain.uc_schema_name,
        template_id=str(template.id),
        upload_id=str(upload.id),
        original_filename=file.filename,
    )

    try:
        storage_service.upload_file(
            file_bytes=file_bytes,
            destination_path=storage_path,
        )
    except Exception as e:
        logger.error(
            f"Upload {upload.id} - storage upload failed: {e}",
            exc_info=True,
        )
        upload.status = "failed"
        upload.error_summary = f"Storage upload failed: {e}"
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save uploaded file: {e}",
        )

    # Step 6: Update upload_history with storage info and status
    upload.storage_path = storage_path
    upload.stored_filename = file.filename
    upload.status = "file_uploaded"
    db.commit()
    db.refresh(upload)

    logger.info(
        f"Upload {upload.id} - file saved to: {storage_path}"
    )

    # Step 7: Run Polars validation and persist results.
    
    run_validation_phase(
        db=db,
        upload=upload,
        template=template,
        columns=template.columns,
        file_bytes=file_bytes,
    )
    db.refresh(upload)

    # NOTE: Subsequent tasks add steps here:
    #   - Apply bad row threshold logic (Task 7.6)
    #   - Trigger Databricks write job (Task 7.8)

    return upload