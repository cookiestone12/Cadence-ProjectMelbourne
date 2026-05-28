"""Task #212 — regression guard for the broken-logo email bug.

The welcome/invite/digest templates used to hardcode a stale
`https://cadence-catalog-intelligence.replit.app/cadence-logo.png` URL
that 404'd in real mail clients, leaving a broken-image placeholder at
the top of every transactional email. These tests pin the templates to
the centralised `get_logo_url()` helper and to the production host as
the default.
"""
import os
from importlib import reload

import backend.templates.email_base as email_base


def _reload_base():
    reload(email_base)


def test_default_logo_url_uses_production_host(monkeypatch):
    monkeypatch.delenv("FRONTEND_URL", raising=False)
    monkeypatch.delenv("PLATFORM_URL", raising=False)
    _reload_base()
    assert email_base.get_logo_url() == "https://cadence-ci.com/cadence-logo.png"


def test_logo_url_respects_frontend_url_env(monkeypatch):
    monkeypatch.setenv("FRONTEND_URL", "https://staging.example.com/")
    monkeypatch.delenv("PLATFORM_URL", raising=False)
    _reload_base()
    assert email_base.get_logo_url() == "https://staging.example.com/cadence-logo.png"


def test_logo_url_falls_back_to_platform_url(monkeypatch):
    monkeypatch.delenv("FRONTEND_URL", raising=False)
    monkeypatch.setenv("PLATFORM_URL", "https://preview.example.com")
    _reload_base()
    assert email_base.get_logo_url() == "https://preview.example.com/cadence-logo.png"


def test_welcome_email_has_no_stale_replit_logo(monkeypatch):
    monkeypatch.delenv("FRONTEND_URL", raising=False)
    monkeypatch.delenv("PLATFORM_URL", raising=False)
    _reload_base()
    # Re-import templates so they see the reloaded base module.
    import backend.templates.email_templates as templates
    reload(templates)
    html = templates.welcome_email(
        recipient_name="New Admin",
        recipient_username="newadmin",
        recipient_email="new@example.com",
        org_name="Acme Music",
        org_role="ADMIN",
    )
    assert "cadence-ci.com/cadence-logo.png" in html
    assert "cadence-catalog-intelligence.replit.app" not in html
    # Both header (50px) and footer (30px) marks must render.
    assert html.count("cadence-logo.png") >= 2


def test_digest_email_has_no_stale_replit_logo(monkeypatch):
    monkeypatch.delenv("FRONTEND_URL", raising=False)
    monkeypatch.delenv("PLATFORM_URL", raising=False)
    _reload_base()
    import backend.templates.email_digest as digest
    reload(digest)
    html = digest.generate_digest_html(
        "Test",
        {},
        {"total": 0, "critical": 0, "high": 0, "medium": 0, "low": 0, "overdue": 0},
    )
    assert "cadence-ci.com/cadence-logo.png" in html
    assert "cadence-catalog-intelligence.replit.app" not in html
    assert html.count("cadence-logo.png") >= 2
