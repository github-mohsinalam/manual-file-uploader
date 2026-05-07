"""
Uploads router - file upload endpoints.

Endpoints:
    POST /uploads               Upload a file for an Approved template
    GET  /uploads               List uploads with filters
    GET  /uploads/{id}          Get single upload
    GET  /uploads/{id}/errors   List validation errors for an upload

"""

import logging
from pathlib import Path
from uuid import UUID
from datetime import datetime, timezone
from typing import Optional

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    UploadFile,
    status,
    BackgroundTasks,
    Query
)
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.auth.models import User
from app.core.config import settings
from app.database.database import get_db
from app.models.domain import Domain
from app.models.template import Template
from app.models.upload_history import UploadHistory
from app.models.upload_validation_error import UploadValidationError
from app.schemas.upload_history import UploadSummary, UploadHistoryResponse
from app.schemas.upload_validation_error import UploadValidationErrorResponse
from app.services.storage.storage_service import (
    build_upload_path,
    storage_service,
)

from app.services.databricks.client import trigger_upload_write_job
from app.services.validation import (
    apply_threshold_and_stage,
    poll_upload_run_and_finalize,
    run_validation_phase,
)
from app.services.validation.emails import send_upload_result_email

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
    background_tasks: BackgroundTasks,
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
        upload.completed_at = datetime.now(timezone.utc)
        db.commit()
        send_upload_result_email(upload, template)
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
    
    result = run_validation_phase(
        db=db,
        upload=upload,
        template=template,
        columns=template.columns,
        file_bytes=file_bytes,
    )
    db.refresh(upload)

    # Step 8: Apply threshold and stage clean Parquet.
    # Skipped when validation already terminated the upload
    # (schema failure leaves status='failed'). On the happy
    # path this either flips status to 'failed' (threshold
    # breach) or stages the Parquet for the Databricks job.
    
    if upload.status == "constraints_checked":
        apply_threshold_and_stage(
            db=db,
            upload=upload,
            template=template,
            domain=domain,
            result=result,
        )
        db.refresh(upload)

    # Step 9: Trigger Databricks write job and schedule
    # polling. Only reached on the happy path - if any
    # earlier step set status='failed', skip the Databricks
    # round trip entirely.
    if upload.status == "constraints_checked":
        try:
            run_id = trigger_upload_write_job(
                template_id=str(template.id),
                upload_id=str(upload.id),
                uploaded_by=current_user.email,
            )
        except Exception as e:
            # The trigger itself failed - Databricks unreachable,
            # auth issue, job_id misconfigured. Mark the upload
            # failed before returning so the user sees the
            # problem; no point pretending the job is running.
            logger.error(
                "Upload %s - trigger failed: %s",
                upload.id, e, exc_info=True,
            )
            upload.status = "failed"
            upload.error_summary = (
                f"Failed to trigger Databricks write job: {e}"
            )
            from datetime import datetime, timezone
            upload.completed_at = datetime.now(timezone.utc)
            db.commit()
            db.refresh(upload)
            send_upload_result_email(upload, template)
            return upload

        upload.databricks_run_id = str(run_id)
        upload.status = "writing_to_catalog"
        db.commit()
        db.refresh(upload)

        # Schedule polling AFTER the response is sent.
        # BackgroundTask runs poll_upload_run_and_finalize in its own
        # thread with its own DB session.
        background_tasks.add_task(
            poll_upload_run_and_finalize,
            upload_id=upload.id,
        )

    return upload

# ================================================
# GET endpoints 
# ================================================

@router.get("", response_model=list[UploadHistoryResponse])
def list_uploads(
    db: Session = Depends(get_db),
    template_id: Optional[UUID] = Query(
        None,
        description="Filter by template.",
    ),
    uploaded_by: Optional[str] = Query(
        None,
        description="Filter by uploader email.",
    ),
    upload_status: Optional[str] = Query(
        None,
        alias="status",
        description=(
            "Filter by status (in_progress, file_uploaded, "
            "schema_validated, constraints_checked, "
            "writing_to_catalog, completed, partial, failed)."
        ),
    ),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    """
    List uploads with optional filters and pagination.

    Multiple filters apply with AND semantics. Results are
    ordered by uploaded_at descending so the newest uploads
    appear first - matches the templates list convention.

    Authorization is open: any authenticated user can list
    any upload. Scoping by uploader is parked in
    future_improvements.md.
    """
    query = db.query(UploadHistory)

    if template_id:
        query = query.filter(UploadHistory.template_id == template_id)

    if uploaded_by:
        query = query.filter(UploadHistory.uploaded_by == uploaded_by)

    if upload_status:
        query = query.filter(UploadHistory.status == upload_status)

    return (
        query
        .order_by(UploadHistory.uploaded_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )


@router.get("/{id}", response_model=UploadHistoryResponse)
def get_upload(
    id: UUID,
    db: Session = Depends(get_db),
):
    """
    Get a single upload by ID.

    Returns the full UploadHistoryResponse - drives the
    progress stepper UI in the frontend, which polls this
    endpoint every 2-3 seconds while watching status.
    """
    upload = (
        db.query(UploadHistory)
        .filter(UploadHistory.id == id)
        .first()
    )
    if not upload:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Upload not found: {id}",
        )
    return upload


@router.get(
    "/{id}/errors",
    response_model=list[UploadValidationErrorResponse],
)
def list_upload_errors(
    id: UUID,
    db: Session = Depends(get_db),
    error_type: Optional[str] = Query(
        None,
        description=(
            "Filter by error type (NOT_NULL, UNIQUE, "
            "TYPE_MISMATCH, SCHEMA_MISMATCH, ENCODING_ERROR, "
            "PARSE_ERROR)."
        ),
    ),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    """
    List validation errors for an upload, paginated.

    Errors are ordered by row_number ascending then
    column_name ascending - users typically read errors
    top-down through their file. The validator caps total
    errors at 1000 per upload, so a single result page can
    return up to 500.

    Returns 404 if the upload itself does not exist (helps
    distinguish "no errors" from "no such upload").
    """
    # Confirm the upload exists - otherwise an empty list
    # would mean both "valid upload, no errors" and "bogus
    # upload_id". The 404 disambiguates.
    upload_exists = (
        db.query(UploadHistory.id)
        .filter(UploadHistory.id == id)
        .first()
    )
    if not upload_exists:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Upload not found: {id}",
        )

    query = (
        db.query(UploadValidationError)
        .filter(UploadValidationError.upload_id == id)
    )

    if error_type:
        query = query.filter(UploadValidationError.error_type == error_type)

    return (
        query
        .order_by(
            UploadValidationError.row_number.asc(),
            UploadValidationError.column_name.asc(),
        )
        .offset(offset)
        .limit(limit)
        .all()
    )