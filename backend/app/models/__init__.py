"""
Models package.

Importing all models here ensures they are registered with
SQLAlchemy's Base metadata when this package is imported.
SQLAlchemy needs to know about all models before it can
create relationships between them correctly.

If a model is not imported here its relationships will not
resolve and you will get errors like:
    "Mapper could not assemble any primary key columns"
"""

from app.models.domain import Domain
from app.models.template import Template
from app.models.template_column import TemplateColumn
from app.models.template_reviewer import TemplateReviewer
from app.models.template_approval import TemplateApproval
from app.models.upload_history import UploadHistory
from app.models.upload_validation_error import UploadValidationError

__all__ = [
    "Domain",
    "Template",
    "TemplateColumn",
    "TemplateReviewer",
    "TemplateApproval",
    "UploadHistory",
    "UploadValidationError",
]