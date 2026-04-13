"""TemplateColumn model - maps to the template_columns table."""

import uuid
from sqlalchemy import Column, String, Text, Integer, Boolean, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.database.database import Base
from app.models.base import CreatedAtMixin


class TemplateColumn(Base, CreatedAtMixin):
    """Column level configuration for a template."""

    __tablename__ = "template_columns"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    template_id = Column(
        UUID(as_uuid=True),
        ForeignKey("templates.id", ondelete="CASCADE"),
        nullable=False
    )

    column_name = Column(String(255), nullable=False)
    display_name = Column(String(255), nullable=True)
    data_type = Column(String(50), nullable=False, default="STRING")
    description = Column(Text, nullable=True)
    is_included = Column(Boolean, nullable=False, default=True)
    is_pii = Column(Boolean, nullable=False, default=False)
    is_nullable = Column(Boolean, nullable=False, default=True)
    is_unique = Column(Boolean, nullable=False, default=False)
    column_order = Column(Integer, nullable=False, default=0)

    template = relationship("Template", back_populates="columns")

    def __repr__(self):
        return (
            f"<TemplateColumn "
            f"name={self.column_name} "
            f"type={self.data_type} "
            f"pii={self.is_pii}>"
        )