"""TemplateApproval model - maps to the template_approvals table."""

import uuid
from sqlalchemy import Column, String, Text, Boolean, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.database.database import Base
from app.models.base import CreatedAtMixin


class TemplateApproval(Base, CreatedAtMixin):
    """
    Records an approval or rejection action taken by a reviewer.
    Also stores the secure token sent in the approval email link.
    """

    __tablename__ = "template_approvals"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    template_id = Column(
        UUID(as_uuid=True),
        ForeignKey("templates.id", ondelete="CASCADE"),
        nullable=False
    )

    reviewer_email = Column(String(255), nullable=False)
    reviewer_name = Column(String(255), nullable=True)

    # action is NULL until the reviewer acts
    action = Column(String(10), nullable=True)
    comment = Column(Text, nullable=True)

    approval_token = Column(String(500), nullable=False, unique=True)
    token_used = Column(Boolean, nullable=False, default=False)
    token_expires_at = Column(DateTime(timezone=True), nullable=False)
    actioned_at = Column(DateTime(timezone=True), nullable=True)

    template = relationship("Template", back_populates="approvals")

    def __repr__(self):
        return (
            f"<TemplateApproval "
            f"reviewer={self.reviewer_email} "
            f"action={self.action}>"
        )