"""
Email-sending helpers for the upload pipeline.

One function per distinct email, each renders a Jinja template and dispatches
it via the configured email service. Functions are designed
to be invoked from FastAPI BackgroundTasks so they run after
the response has been sent (or, in the poller's case, after
the Databricks run terminates).

Three terminal upload states each map to one email:
    completed -> send_upload_completed_email
    partial   -> send_upload_partial_email
    failed    -> send_upload_failed_email

A single dispatch helper picks the right sender based on
upload.status, so callers do not have to switch on status
themselves.
"""

import logging

from app.core.config import settings
from app.models.template import Template
from app.models.upload_history import UploadHistory
from app.services.email.service_factory import get_email_service
from app.services.email.templates_loader import render_template


logger = logging.getLogger(__name__)


def send_upload_result_email(
    upload: UploadHistory, template: Template
) -> None:
    """
    Dispatch the upload-result email for a terminal upload.

    Looks at upload.status and picks the right sender.
    Non-terminal statuses are ignored (logged and dropped) -
    we never want to email about an in-flight upload.

    Best-effort. All failures are logged; nothing raises.
    """
    status = upload.status
    if status == "completed":
        send_upload_completed_email(upload, template)
    elif status == "partial":
        send_upload_partial_email(upload, template)
    elif status == "failed":
        send_upload_failed_email(upload, template)
    else:
        logger.warning(
            "send_upload_result_email called for non-terminal "
            "upload %s (status=%s) - skipping",
            upload.id, status,
        )


# ============================================================
# Per-status senders
# ============================================================

def send_upload_completed_email(
    upload: UploadHistory, template: Template
) -> None:
    """
    Notify the uploader that every row landed in the table.

    Rendered from upload_completed.html. The user sees how
    many rows were written and where to find the data.
    """
    context = {
        "uploaded_by": upload.uploaded_by,
        "template_display_name": template.display_name,
        "fully_qualified_name": template.fully_qualified_name,
        "original_filename": upload.original_filename,
        "total_rows": upload.total_rows,
        "valid_rows": upload.valid_rows,
        "upload_id": str(upload.id),
        "app_base_url": settings.app_base_url,
    }
    _send(
        upload=upload,
        template_name="upload_completed.html",
        subject=f"Upload completed: {template.display_name}",
        context=context,
    )


def send_upload_partial_email(
    upload: UploadHistory, template: Template
) -> None:
    """
    Notify the uploader that the upload succeeded but some
    rows were dropped during validation.

    The dropped count comes from upload.invalid_rows - those
    were the rows that failed validation. Under
    bad_row_action='drop' the threshold step let the upload
    proceed; the Databricks write succeeded with the clean
    subset.
    """
    context = {
        "uploaded_by": upload.uploaded_by,
        "template_display_name": template.display_name,
        "fully_qualified_name": template.fully_qualified_name,
        "original_filename": upload.original_filename,
        "total_rows": upload.total_rows,
        "valid_rows": upload.valid_rows,
        "invalid_rows": upload.invalid_rows,
        "upload_id": str(upload.id),
        "app_base_url": settings.app_base_url,
    }
    _send(
        upload=upload,
        template_name="upload_partial.html",
        subject=f"Upload completed with warnings: {template.display_name}",
        context=context,
    )


def send_upload_failed_email(
    upload: UploadHistory, template: Template
) -> None:
    """
    Notify the uploader that the upload terminated as failed.

    Surfaces upload.error_summary so the user sees the
    reason without opening the app. The summary is populated
    by whichever phase produced the failure - schema, parse,
    threshold, trigger, or polling.
    """
    context = {
        "uploaded_by": upload.uploaded_by,
        "template_display_name": template.display_name,
        "fully_qualified_name": template.fully_qualified_name,
        "original_filename": upload.original_filename,
        "total_rows": upload.total_rows,
        "valid_rows": upload.valid_rows,
        "invalid_rows": upload.invalid_rows,
        "error_summary": upload.error_summary or "No detail available.",
        "upload_id": str(upload.id),
        "app_base_url": settings.app_base_url,
    }
    _send(
        upload=upload,
        template_name="upload_failed.html",
        subject=f"Upload failed: {template.display_name}",
        context=context,
    )


# ============================================================
# Shared dispatch
# ============================================================

def _send(
    upload: UploadHistory,
    template_name: str,
    subject: str,
    context: dict,
) -> None:
    """
    Render and send one upload-result email.

    Centralised so the three per-status senders share their
    error handling and logging. Best-effort - exceptions are
    caught and logged but not re-raised, matching every
    other email function in the project.
    """
    email_service = get_email_service()

    try:
        html_body = render_template(template_name, context)
        email_service.send(
            to_email=upload.uploaded_by,
            to_name=upload.uploaded_by,
            subject=subject,
            html_body=html_body,
        )
        logger.info(
            "Upload %s - %s email sent to %s",
            upload.id, template_name, upload.uploaded_by,
        )
    except Exception as e:
        logger.error(
            "Failed to send %s for upload %s to %s: %s",
            template_name, upload.id, upload.uploaded_by, e,
            exc_info=True,
        )