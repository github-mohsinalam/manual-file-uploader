"""
Health check endpoints.

These endpoints are used by:
- Load balancers to decide routing
- Container orchestrators to decide restarts
- Monitoring tools to detect outages
- Deployment pipelines to verify successful deployments

Two endpoints are provided:
    /health/live    - is the process alive? (liveness probe)
    /health/ready   - is the service ready to serve? (readiness probe)
"""

import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.orm import Session
from app.auth.dependencies import get_current_user
from app.auth.models import User

from app.database.database import get_db

logger = logging.getLogger(__name__)

# APIRouter is FastAPI's way of grouping related routes
# Think of it like a mini-application that gets plugged into
# the main app via app.include_router()
# prefix="/health" means all routes in this file start with /health
# tags=["Health"] groups these endpoints in the Swagger UI
router = APIRouter(
    prefix="/health",
    tags=["Health"]
)


@router.get(
    "/live",
    summary="Liveness probe",
    description="Returns 200 if the process is running. "
                "Does not check external dependencies.",
    status_code=status.HTTP_200_OK
)
def liveness_check():
    """
    Liveness check - is the process alive?

    This endpoint deliberately does NOT check the database
    or any external service. If the process is running enough
    to respond to this request it is considered alive.

    Why separate from readiness?
    A brief database blip should not cause the container to be
    killed and restarted. Kubernetes policy typically restarts
    containers that fail liveness but only stops routing
    traffic to containers that fail readiness.
    """
    return {"status": "alive"}


@router.get(
    "/ready",
    summary="Readiness probe",
    description="Returns 200 if the service is ready to handle "
                "requests. Verifies the database is reachable."
)
def readiness_check(db: Session = Depends(get_db)):
    """
    Readiness check - is the service ready to handle traffic?

    This endpoint verifies that critical dependencies are reachable:
    - PostgreSQL database

    If any dependency is unreachable this returns 503 Service
    Unavailable - telling load balancers and orchestrators to
    stop routing traffic here until the dependency recovers.

    Depends(get_db) is FastAPI's dependency injection system.
    FastAPI calls get_db() automatically, gets a database
    session, and injects it into the `db` parameter.
    When the endpoint finishes FastAPI ensures the session
    is properly closed via the finally block in get_db().
    """
    checks = {}

    # Check 1: Database connectivity
    try:
        # text() wraps a raw SQL string so SQLAlchemy knows
        # it is literal SQL and not an ORM expression
        # SELECT 1 is the universally accepted "ping" query
        # for databases - minimal work, just proves connectivity
        db.execute(text("SELECT 1"))
        checks["database"] = {"status": "healthy"}
        logger.debug("Readiness check: database is healthy")

    except Exception as e:
        # If the database check fails we log the error but
        # return a structured response showing what failed
        # We use 503 to signal "not ready" - different from 500
        # which would indicate an unexpected server error
        logger.error(f"Readiness check: database is unhealthy - {e}")
        checks["database"] = {
            "status": "unhealthy",
            "error": str(e)
        }

        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "status": "not_ready",
                "checks": checks
            }
        )

    # All checks passed
    return {
        "status": "ready",
        "checks": checks
    }

@router.get("/me")
def whoami(current_user: User = Depends(get_current_user)):
    """
    Return the currently authenticated user.
    """
    return current_user

@router.post("/test-email")
def send_test_email(
    to_email: str,
    current_user: User = Depends(get_current_user),
):
    """
    Send a test email to verify the email infrastructure works.

    TEMPORARY ENDPOINT - to be removed after Phase 6 is complete.

    Send a POST to this endpoint with ?to_email=your@email.com
    and check your inbox.
    """
    from datetime import datetime
    from app.services.email.service_factory import get_email_service
    from app.services.email.templates_loader import render_template

    email_service = get_email_service()

    html_body = render_template(
        "test_email.html",
        context={
            "subject": "Test email from Manual File Uploader",
            "recipient_name": "Test Recipient",
            "sent_at": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC"),
        },
    )

    message_id = email_service.send(
        to_email=to_email,
        to_name="Test Recipient",
        subject="Test email from Manual File Uploader",
        html_body=html_body,
    )

    return {
        "status": "sent",
        "to": to_email,
        "message_id": message_id,
    }