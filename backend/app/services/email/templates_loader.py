"""
Jinja2 template loader for email HTML.

Templates live in backend/app/email_templates/ as .html files.
They use Jinja2 syntax for placeholders:

    Hello {{ recipient_name }},
    Your template "{{ template_name }}" is ready.

Caller passes a dict of context. Template is rendered to a
string of HTML ready for sending.
"""

from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, select_autoescape


# Resolve the templates folder path
# Goes from this file (backend/app/services/email/templates_loader.py)
# up four levels to the project root, then into the templates folder
_TEMPLATES_DIR = (
    Path(__file__).parent.parent.parent / "email_templates"
)

# Create one shared Jinja2 environment
# autoescape protects against XSS by HTML-escaping template
# variables - critical when rendering user-provided content
# like template descriptions or comments
_jinja_env = Environment(
    loader=FileSystemLoader(_TEMPLATES_DIR),
    autoescape=select_autoescape(["html"]),
    trim_blocks=True,
    lstrip_blocks=True,
)


def render_template(template_name: str, context: dict[str, Any]) -> str:
    """
    Render an email template to HTML.

    Args:
        template_name: Name of the .html file in email_templates/
            (e.g. "approval_request.html")
        context: Dict of variables to substitute into the template

    Returns:
        Rendered HTML as a string.

    Raises:
        TemplateNotFound if the template file does not exist.
    """
    template = _jinja_env.get_template(template_name)
    return template.render(**context)