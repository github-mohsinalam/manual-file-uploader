"""
Base model mixins with shared columns.

We have two mixins to handle the fact that not all tables
support updates:

CreatedAtMixin — for append-only tables that are never updated
after insert. Provides only created_at.

TimestampMixin — for tables whose rows can be updated over time.
Provides both created_at and updated_at.

This is more precise than giving every table an updated_at column
that has no real meaning for append-only tables.
"""

import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, DateTime
from sqlalchemy.dialects.postgresql import UUID
from app.database.database import Base


def generate_uuid():
    """Generate a new UUID4. Used as the default for primary key columns."""
    return str(uuid.uuid4())


def utc_now():
    """Return current UTC time. Used as default for timestamp columns."""
    return datetime.now(timezone.utc)


class CreatedAtMixin:
    """
    Mixin for append-only tables.
    Provides only created_at — set once on insert, never updated.

    Use this for tables like:
    - template_columns (column config is fixed after template creation)
    - template_reviewers (reviewer list is fixed after submission)
    - template_approvals (approval records are permanent audit entries)
    - upload_validation_errors (error records are never modified)
    """

    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        comment="Timestamp when this record was created (UTC)"
    )


class TimestampMixin(CreatedAtMixin):
    """
    Mixin for tables whose rows change state over time.
    Provides both created_at (inherited) and updated_at.

    updated_at is automatically refreshed by SQLAlchemy on every
    UPDATE operation via the onupdate hook.

    Use this for tables like:
    - domains (description could be updated)
    - templates (status changes throughout lifecycle)
    - upload_history (status updated as each pipeline step completes)
    """

    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        onupdate=utc_now,
        comment="Timestamp when this record was last updated (UTC)"
    )