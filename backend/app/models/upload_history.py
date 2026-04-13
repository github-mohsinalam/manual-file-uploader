"""UploadHistory model - maps to the upload_history table."""

import uuid
from sqlalchemy import Column, String, Text, Integer, BigInteger, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.database.database import Base
from app.models.base import TimestampMixin


class UploadHistory(Base, TimestampMixin):
    """
    Permanent audit record of every file upload attempt.
    Created at start of upload and updated as each step completes.
    """

    __tablename__ = "upload_history"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    template_id = Column(
        UUID(as_uuid=True),
        ForeignKey("templates.id", ondelete="RESTRICT"),
        nullable=False
    )

    uploaded_by = Column(String(255), nullable=False)
    uploaded_at = Column(DateTime(timezone=True), nullable=False)
    original_filename = Column(String(500), nullable=False)
    stored_filename = Column(String(500), nullable=True)
    storage_path = Column(String(500), nullable=True)
    file_size_bytes = Column(BigInteger, nullable=True)
    total_rows = Column(Integer, nullable=True)
    valid_rows = Column(Integer, nullable=True)
    invalid_rows = Column(Integer, nullable=True)
    dropped_rows = Column(Integer, nullable=True)
    status = Column(String(20), nullable=False, default="in_progress")
    error_summary = Column(Text, nullable=True)
    databricks_run_id = Column(String(100), nullable=True)
    dlt_rows_written = Column(Integer, nullable=True)
    dlt_rows_dropped = Column(Integer, nullable=True)
    dlt_event_log_path = Column(String(500), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    template = relationship("Template", back_populates="uploads")

    validation_errors = relationship(
        "UploadValidationError",
        back_populates="upload",
        cascade="all, delete-orphan",
        lazy="select"
    )

    def __repr__(self):
        return (
            f"<UploadHistory "
            f"id={self.id} "
            f"status={self.status}>"
        )