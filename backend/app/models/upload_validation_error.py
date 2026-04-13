"""UploadValidationError model - maps to the upload_validation_errors table."""

import uuid
from sqlalchemy import Column, String, Text, Integer, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.database.database import Base
from app.models.base import CreatedAtMixin


class UploadValidationError(Base, CreatedAtMixin):
    """
    Row level validation error from Polars Layer 1 validation.
    One row per bad cell found during file validation.
    Powers the error detail table shown in the upload progress UI.
    """

    __tablename__ = "upload_validation_errors"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    upload_id = Column(
        UUID(as_uuid=True),
        ForeignKey("upload_history.id", ondelete="CASCADE"),
        nullable=False
    )

    row_number = Column(Integer, nullable=False)
    column_name = Column(String(255), nullable=False)
    error_type = Column(String(50), nullable=False)
    error_message = Column(Text, nullable=False)
    raw_value = Column(Text, nullable=True)

    upload = relationship("UploadHistory", back_populates="validation_errors")

    def __repr__(self):
        return (
            f"<UploadValidationError "
            f"row={self.row_number} "
            f"column={self.column_name} "
            f"type={self.error_type}>"
        )