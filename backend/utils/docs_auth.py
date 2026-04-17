"""HTTP Basic Auth gate for /docs, /redoc, /openapi.json in
production.

In development the docs are open so engineers can hit them without
extra setup. In production we require Basic Auth using
``DOCS_USERNAME`` / ``DOCS_PASSWORD`` from Replit Secrets so the
schema isn't a public discovery surface.

If the credentials env vars are missing in production we fail
*closed* — return 503 instead of leaving the docs unprotected.
"""
from __future__ import annotations

import logging
import os
import secrets

from fastapi import HTTPException, Request, status
from fastapi.security import HTTPBasicCredentials

from .settings import IS_PRODUCTION


_log = logging.getLogger("cadence")


def _get_creds() -> tuple[str, str] | None:
    user = os.getenv("DOCS_USERNAME")
    pw = os.getenv("DOCS_PASSWORD")
    if not user or not pw:
        return None
    return user, pw


def require_docs_auth(request: Request) -> None:
    """FastAPI dependency. No-op in development.

    In production:
      * 503 if DOCS_USERNAME / DOCS_PASSWORD are not configured.
      * 401 (with WWW-Authenticate: Basic) if credentials are
        missing or wrong, with a WARNING log line so brute-force
        attempts are visible in the ring buffer.
    """
    if not IS_PRODUCTION:
        return

    expected = _get_creds()
    if expected is None:
        _log.error(
            "Docs auth requested in production but DOCS_USERNAME / "
            "DOCS_PASSWORD are not set; refusing to serve docs."
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="API docs are temporarily unavailable.",
        )

    # Parse the Authorization header ourselves so this dependency
    # stays sync-callable from FastAPI's threadpool resolver.
    creds: HTTPBasicCredentials | None = None
    auth = request.headers.get("authorization", "")
    if auth.lower().startswith("basic "):
        import base64
        try:
            decoded = base64.b64decode(auth.split(" ", 1)[1]).decode("utf-8")
            user, sep, pw = decoded.partition(":")
            if sep:
                creds = HTTPBasicCredentials(username=user, password=pw)
        except Exception:
            creds = None

    expected_user, expected_pw = expected
    if creds is None or not (
        secrets.compare_digest(creds.username, expected_user)
        and secrets.compare_digest(creds.password, expected_pw)
    ):
        client = getattr(request, "client", None)
        ip = getattr(client, "host", None) if client else None
        _log.warning(
            "Docs auth rejected: ip=%s path=%s",
            ip, request.url.path,
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": 'Basic realm="Cadence API docs"'},
        )
