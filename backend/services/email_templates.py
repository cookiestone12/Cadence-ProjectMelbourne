"""Admin-editable outreach email templates.

The two lead-outreach emails (waitlist qualifier and demo confirmation) used to
be hardcoded in ``backend/routes/leads.py``. They now live in the
``email_templates`` table so platform admins can edit the subject, header, and
body from the admin UI without a code change.

Template bodies are stored as **plain text**: blank lines separate paragraphs,
single newlines become line breaks, and ``{first_name}`` is substituted with
the lead's first name (or "there"). Bodies are HTML-escaped before rendering, so
admins cannot inject markup and don't need to know HTML. ``render_template``
wraps the body in the standard branded HTML shell (gradient header + footer).

``DEFAULT_TEMPLATES`` is the single source of truth for the seed content and
also acts as a safety fallback if a template row is missing.
"""
from html import escape as html_escape
from typing import Optional

from sqlalchemy.orm import Session

from ..models import EmailTemplate, Lead


_EMAIL_FOOTER = (
    '<p style="color: #9CA3A0; font-size: 12px; margin: 24px 0 0; '
    'text-align: center;">Cadence Catalog Intelligence Co. | '
    'communication@cadence-ci.com</p>'
)


DEFAULT_TEMPLATES = {
    "qualify": {
        "template_key": "qualify",
        "lead_type": "WAITLIST",
        "name": "Waitlist qualifier",
        "subject": "You're on the Cadence waitlist",
        "header": "You're on the list",
        "body": (
            "Hi {first_name},\n\n"
            "Thank you for joining the Cadence waitlist. We are glad you are here.\n\n"
            "Cadence is a catalog management and royalty intelligence platform built "
            "for music companies that are serious about their rights data. We help "
            "labels, publishers, and creators keep their catalog, royalties, and "
            "rights organized and working harder.\n\n"
            "Before we reach out to schedule a call, we want to make sure Cadence is "
            "the right fit for you. Two quick questions:\n\n"
            "1. What best describes your organization (label, publisher, production "
            "company, independent artist, or other)?\n"
            "2. Roughly how many songs or works are in your active catalog?\n\n"
            "Hit reply and let us know. We read every response.\n\n"
            "The Cadence Team"
        ),
    },
    "demo_schedule": {
        "template_key": "demo_schedule",
        "lead_type": "DEMO_REQUEST",
        "name": "Demo confirmation",
        "subject": "We received your Cadence demo request",
        "header": "Your demo request is in",
        "body": (
            "Hi {first_name},\n\n"
            "Thank you for requesting a demo of Cadence. We have your information and "
            "you are next on the list.\n\n"
            "Expect an email from our team shortly with a link to book your "
            "walkthrough. The session runs about 30 minutes and covers catalog "
            "management, royalty processing, and rights administration, tailored to "
            "your organization type.\n\n"
            "If you have any questions in the meantime, just reply to this email.\n\n"
            "The Cadence Team"
        ),
    },
}


def first_name(lead: Lead) -> str:
    """First name of a lead, falling back to "there" — already HTML-escaped."""
    name = (lead.name or "").strip()
    if name:
        return html_escape(name.split()[0])
    return "there"


def _render_body_html(body: str, lead: Lead) -> str:
    """Turn a plain-text body into safe, styled HTML paragraphs.

    Escapes everything first (so admin input can't inject markup), substitutes
    the ``{first_name}`` placeholder with the escaped first name, splits on
    blank lines into ``<p>`` blocks, and converts single newlines to ``<br>``.
    """
    escaped = html_escape(body or "")
    escaped = escaped.replace("{first_name}", first_name(lead))

    paragraphs = [p.strip() for p in escaped.replace("\r\n", "\n").split("\n\n")]
    blocks = []
    for para in paragraphs:
        if not para:
            continue
        para_html = para.replace("\n", "<br>")
        blocks.append(
            '<p style="color: #3D4A44; font-size: 16px; margin: 0 0 16px; '
            f'line-height: 1.6;">{para_html}</p>'
        )
    return "\n".join(blocks)


def render_template(template, lead: Lead):
    """Render a template (ORM row or dict) into ``(subject, html)`` for a lead."""
    if isinstance(template, dict):
        subject = template["subject"]
        header = template["header"]
        body = template["body"]
    else:
        subject = template.subject
        header = template.header
        body = template.body

    body_html = _render_body_html(body, lead)
    html = f"""
    <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 600px; margin: 0 auto;">
        <div style="background: linear-gradient(135deg, #5B8A72, #7BA594); padding: 30px; border-radius: 12px 12px 0 0;">
            <h1 style="color: white; margin: 0; font-size: 24px;">{html_escape(header)}</h1>
        </div>
        <div style="background: #f9fafb; padding: 30px; border-radius: 0 0 12px 12px;">
            {body_html}
            {_EMAIL_FOOTER}
        </div>
    </div>
    """
    return subject, html


def get_template(db: Session, template_key: str) -> Optional[EmailTemplate]:
    """Fetch a template row by key (no fallback)."""
    return (
        db.query(EmailTemplate)
        .filter(EmailTemplate.template_key == template_key)
        .first()
    )


def ensure_seeded(db: Session) -> None:
    """Insert any missing default templates. Safe to call repeatedly."""
    changed = False
    for key, default in DEFAULT_TEMPLATES.items():
        existing = (
            db.query(EmailTemplate)
            .filter(EmailTemplate.template_key == key)
            .first()
        )
        if existing is None:
            db.add(EmailTemplate(
                template_key=default["template_key"],
                lead_type=default["lead_type"],
                name=default["name"],
                subject=default["subject"],
                header=default["header"],
                body=default["body"],
                is_active=True,
            ))
            changed = True
    if changed:
        db.commit()
