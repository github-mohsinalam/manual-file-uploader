"""
Template model - maps to the templates table in PostgreSQL.

A template defines the structure and configuration of a manual
mapping file and its corresponding Unity Catalog table.
"""

import uuid
from sqlalchemy import (
    Column, String, Text, Integer, Boolean,
    Numeric, ForeignKey, DateTime
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.database.database import Base
from app.models.base import TimestampMixin, generate_uuid, utc_now


class Template(Base, TimestampMixin):
    """Represents a manual file template and its UC table configuration."""

    __tablename__ = "templates"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    name = Column(String(255), nullable=False)
    display_name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)

    domain_id = Column(
        UUID(as_uuid=True),
        ForeignKey("domains.id", ondelete="RESTRICT"),
        nullable=False
    )

    uc_table_name = Column(String(255), nullable=False)
    fully_qualified_name = Column(String(500), nullable=False, unique=True)

    file_format = Column(String(10), nullable=False, default="csv")
    delimiter = Column(String(5), nullable=False, default=",")
    encoding = Column(String(20), nullable=False, default="UTF-8")
    write_mode = Column(String(10), nullable=False, default="append")

    bad_row_threshold = Column(Numeric(5, 2), nullable=False, default=0.00)
    bad_row_action = Column(String(10), nullable=False, default="fail")

    storage_path = Column(String(500), nullable=True)
    reader_group = Column(String(255), nullable=True)

    status = Column(String(50), nullable=False, default="Draft")
    version = Column(Integer, nullable=False, default=1)

    parent_template_id = Column(
        UUID(as_uuid=True),
        ForeignKey("templates.id", ondelete="RESTRICT"),
        nullable=True
    )

    created_by = Column(String(255), nullable=False)
    approved_at = Column(DateTime(timezone=True), nullable=True)
    databricks_ddl_run_id = Column(String(100), nullable=True)

    # Relationships
    domain = relationship("Domain", back_populates="templates")

    columns = relationship(
        "TemplateColumn",
        back_populates="template",
        cascade="all, delete-orphan",
        lazy="select"
    )

    reviewers = relationship(
        "TemplateReviewer",
        back_populates="template",
        cascade="all, delete-orphan",
        lazy="select"
    )

    approvals = relationship(
        "TemplateApproval",
        back_populates="template",
        cascade="all, delete-orphan",
        lazy="select"
    )

    uploads = relationship(
        "UploadHistory",
        back_populates="template",
        lazy="select"
    )

    # Self referential relationship for versioning
    parent_template = relationship(
        "Template",
        remote_side=[id],
        foreign_keys=[parent_template_id]
    )

    def __repr__(self):
        return (
            f"<Template id={self.id} "
            f"name={self.name} "
            f"status={self.status} "
            f"version={self.version}>"
        )