"""
Unit tests for approval token validation.

Tests the four scenarios:
    - Valid token returns the approval
    - Non-existent token raises 404
    - Used token raises 410
    - Expired token raises 410

Uses an in-memory SQLite database for speed and isolation.
Each test gets a fresh database state.
"""

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Important: import Base from a place where ALL models are
# already imported, so SQLAlchemy registers all tables
from app.database.database import Base
from app.models import (
    Domain,
    Template,
    TemplateApproval,
    TemplateColumn,
    TemplateReviewer,
    UploadHistory,
    UploadValidationError,
)
from app.services.approval.validation import get_valid_approval_by_token


# --------------------------------------------------
# Fixtures
# --------------------------------------------------

@pytest.fixture
def db_session():
    """
    Provide a fresh in-memory database session for each test.

    SQLite in-memory is fast and gives full isolation between tests.
    Schema is created from SQLAlchemy models - matches our Postgres
    schema closely enough for unit testing token validation logic.
    """
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def setup_template_with_approval(db_session):
    """
    Create the parent template + a single approval row.

    Returns the approval object so tests can manipulate it.
    """
    # Create a domain (required parent)
    domain = Domain(
        name="Test Domain",
        uc_schema_name="test_domain",
    )
    db_session.add(domain)
    db_session.flush()

    # Create a template
    template = Template(
        name="test_template",
        display_name="Test Template",
        domain_id=domain.id,
        uc_table_name="test_template",
        fully_qualified_name="manualuploads.test_domain.test_template",
        bad_row_threshold=5.00,
        created_by="creator@test.com",
    )
    db_session.add(template)
    db_session.flush()

    # Create an approval row
    approval = TemplateApproval(
        template_id=template.id,
        reviewer_email="reviewer@test.com",
        reviewer_name="Test Reviewer",
        approval_token="valid-test-token-abc123",
        token_used=False,
        token_expires_at=datetime.now(timezone.utc) + timedelta(days=30),
    )
    db_session.add(approval)
    db_session.commit()

    return approval


# --------------------------------------------------
# Tests
# --------------------------------------------------

def test_valid_token_returns_approval(
    db_session, setup_template_with_approval
):
    """A valid, unused, unexpired token returns the approval row."""
    approval = setup_template_with_approval

    result = get_valid_approval_by_token(
        db_session,
        token="valid-test-token-abc123",
    )

    assert result.id == approval.id
    assert result.reviewer_email == "reviewer@test.com"


def test_nonexistent_token_raises_404(db_session):
    """A token that does not exist in the database raises 404."""
    with pytest.raises(HTTPException) as exc_info:
        get_valid_approval_by_token(db_session, token="does-not-exist")

    assert exc_info.value.status_code == 404
    assert "invalid" in exc_info.value.detail.lower()


def test_used_token_raises_410(
    db_session, setup_template_with_approval
):
    """A token that was already used raises 410 Gone."""
    approval = setup_template_with_approval
    approval.token_used = True
    approval.action = "approve"
    approval.actioned_at = datetime.now(timezone.utc)
    db_session.commit()

    with pytest.raises(HTTPException) as exc_info:
        get_valid_approval_by_token(
            db_session,
            token="valid-test-token-abc123",
        )

    assert exc_info.value.status_code == 410
    assert "already been used" in exc_info.value.detail.lower()


def test_expired_token_raises_410(
    db_session, setup_template_with_approval
):
    """A token whose expiry is in the past raises 410 Gone."""
    approval = setup_template_with_approval
    approval.token_expires_at = (
        datetime.now(timezone.utc) - timedelta(days=1)
    )
    db_session.commit()

    with pytest.raises(HTTPException) as exc_info:
        get_valid_approval_by_token(
            db_session,
            token="valid-test-token-abc123",
        )

    assert exc_info.value.status_code == 410
    assert "expired" in exc_info.value.detail.lower()