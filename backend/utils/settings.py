"""Centralized runtime settings.

Single source of truth for environment-conditional behavior. Read once
at import time so we never drift between modules. All env-conditional
code in the rest of the backend should branch on the constants here,
not call ``os.getenv`` directly.
"""
import os
import logging

_log = logging.getLogger("cadence")

_RAW_APP_ENV = os.getenv("APP_ENV", "").strip().lower()
if _RAW_APP_ENV == "":
    APP_ENV = "development"
elif _RAW_APP_ENV in ("development", "production"):
    APP_ENV = _RAW_APP_ENV
else:
    # Fail-safe: unknown explicit value is fail-CLOSED to production
    # rather than silently falling back to development. This prevents
    # a typo like APP_ENV=staging from disabling HTTPS enforcement
    # and leaking tracebacks. Operators must use the documented values.
    _log.error(
        f"APP_ENV={_RAW_APP_ENV!r} is not a recognized value "
        f"('development' or 'production'). Defaulting to 'production' "
        f"to fail closed. Set APP_ENV explicitly."
    )
    APP_ENV = "production"

IS_PRODUCTION: bool = APP_ENV == "production"
IS_DEVELOPMENT: bool = APP_ENV == "development"

BUILD_VERSION: str = (
    os.getenv("BUILD_VERSION")
    or os.getenv("REPLIT_DEPLOYMENT_ID")
    or os.getenv("REPL_SLUG")
    or "unknown"
)

CORS_ORIGINS_RAW: str = os.getenv("CORS_ORIGINS") or os.getenv("ALLOWED_ORIGINS") or ""


def parse_cors_origins() -> list[str]:
    """Parse the CORS env var into a clean list. Returns ['*'] if unset
    in development, or an empty list if unset in production (which
    means: lock everything out — caller should warn loudly)."""
    raw = CORS_ORIGINS_RAW.strip()
    if not raw:
        return ["*"] if IS_DEVELOPMENT else []
    return [o.strip() for o in raw.split(",") if o.strip()]
