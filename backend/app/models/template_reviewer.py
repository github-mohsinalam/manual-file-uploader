"""TemplateReviewer model - maps to the template_reviewers table."""

import uuid
from sqlalchemy import Column, String, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.database.database import Base
from app.models.base import CreatedAtMixin


class TemplateReviewer(Base, CreatedAtMixin):
    """A reviewer configured for a template approval workflow."""

    __tablename__ = "template_reviewers"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    template_id = Column(
        UUID(as_uuid=True),
        ForeignKey("templates.id", ondelete="CASCADE"),
        nullable=False
    )

    reviewer_email = Column(String(255), nullable=False)
    reviewer_name = Column(String(255), nullable=True)
    reviewer_type = Column(String(10), nullable=False, default="required")

    template = relationship("Template", back_populates="reviewers")

    def __repr__(self):
        return (
            f"<TemplateReviewer "
            f"email={self.reviewer_email} "
            f"type={self.reviewer_type}>"
        )