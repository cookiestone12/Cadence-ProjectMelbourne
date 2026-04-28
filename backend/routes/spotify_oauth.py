"""HTTP routes for the project-owned Spotify Authorization-Code flow.

Mounted under ``/api/spotify/oauth``. The five endpoints are:

* ``POST /start-nonce`` (super-admin, Bearer JWT) — issues a 60-second
  single-use nonce so the admin UI can open the OAuth popup without
  smuggling the JWT through a query string.
* ``GET /start?nonce=<value>`` (nonce-bound) — 302 to Spotify's
  authorize page after re-validating that the nonce-bound user is
  still an active super-admin.
* ``GET /callback`` (public) — receives the ``code`` and ``state``,
  exchanges and persists tokens, then renders a self-closing HTML
  page that postMessages success/failure to the opener window.
* ``GET /status`` (admin) — JSON describing whether Spotify is hooked
  up and as whom.
* ``POST /disconnect`` (super-admin) — clears the stored token.

Why a nonce instead of ``?token=<jwt>``: the browser can't attach an
Authorization header to a top-level ``window.open`` navigation, but a
JWT in the query string would leak through browser history, intermediary
proxy logs, and Referer headers. The nonce flow keeps the actual JWT
on the XHR path and lets the popup carry only an opaque, one-shot,
60-second bearer that's also re-validated against the live UserSession
state on consumption.
"""
from __future__ import annotations

import logging
import json
from typing import Optional
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import RedirectResponse, JSONResponse, HTMLResponse
from sqlalchemy.orm import Session

from ..models import get_db, User
from ..utils.auth import (
    get_current_admin_user,
    get_current_super_admin,
)
from ..services import spotify_oauth

logger = logging.getLogger("cadence")

router = APIRouter(prefix="/api/spotify/oauth", tags=["Spotify OAuth"])

_RETURN_TO = "/admin?tab=api-config"


@router.post(
    "/start-nonce",
    summary="Issue a one-shot nonce for the OAuth popup",
    description=(
        "Returns a 60-second, single-use nonce the admin UI can pass "
        "to ``GET /start`` via a query parameter. This endpoint is the "
        "actual Bearer-authenticated authorization checkpoint — the "
        "subsequent ``/start`` call only verifies the nonce and "
        "re-confirms super-admin status against the live DB.\n\n"
        "**Auth:** Bearer JWT — super-admin only (also enforces "
        "``UserSession`` validity, so a revoked JWT can't mint a nonce)."
    ),
)
def issue_start_nonce(current_user: User = Depends(get_current_super_admin)):
    if not spotify_oauth.is_configured():
        raise HTTPException(
            status_code=400,
            detail=(
                "SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET must be set "
                "before connecting Spotify. Add them to project Secrets."
            ),
        )
    nonce = spotify_oauth.issue_start_nonce(current_user.id)
    return {"nonce": nonce, "expires_in": 60}


@router.get(
    "/start",
    summary="Start the project-owned Spotify OAuth flow",
    description=(
        "Redirects the operator to Spotify's authorize page. Requires "
        "a one-shot ``?nonce=<value>`` minted by ``POST /start-nonce`` "
        "within the last 60 seconds. The nonce is consumed atomically "
        "and the user it was bound to is re-checked for active "
        "super-admin status.\n\n"
        "**Response:** 302 to ``accounts.spotify.com``."
    ),
)
def start_oauth(
    nonce: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    if not nonce:
        raise HTTPException(status_code=401, detail="Missing nonce")
    user_id = spotify_oauth.verify_and_consume_start_nonce(nonce)
    if user_id is None:
        raise HTTPException(status_code=401, detail="Invalid, replayed, or expired nonce")
    user = db.query(User).filter(User.id == user_id).first()
    if not user or not getattr(user, "is_active", True):
        raise HTTPException(status_code=401, detail="User no longer active")
    if not getattr(user, "is_super_admin", False):
        raise HTTPException(status_code=403, detail="Super-admin only")

    if not spotify_oauth.is_configured():
        raise HTTPException(
            status_code=400,
            detail=(
                "SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET must be set "
                "before connecting Spotify. Add them to project Secrets."
            ),
        )

    state = spotify_oauth.issue_state()
    url = spotify_oauth.build_authorize_url(state)
    return RedirectResponse(url=url, status_code=302)


def _popup_completion_page(success: bool, reason: Optional[str] = None) -> HTMLResponse:
    """Tiny HTML that postMessages the result to the opener and closes.

    Falls back to a 302 to the admin tab if there's no opener (e.g. the
    operator opened the URL directly). The message origin check on the
    opener side is what enforces trust — we can't restrict the
    ``targetOrigin`` here because the OAuth callback URL is fixed and
    the admin UI may be served from a different host (custom domain).
    """
    payload = json.dumps({
        "type": "spotify_oauth_result",
        "success": bool(success),
        "reason": reason,
    })
    return_to = _RETURN_TO + (
        "&spotify_oauth=connected" if success
        else f"&spotify_oauth=error&reason={quote((reason or 'unknown')[:200])}"
    )
    html = f"""<!doctype html>
<html><head><meta charset="utf-8"><title>Spotify connection</title></head>
<body style="font-family: system-ui, -apple-system, sans-serif; padding: 24px; color: #3D4A44">
<p>{'Spotify account connected.' if success else 'Spotify connection failed.'}</p>
<p style="color: #7A8580; font-size: 14px">You can close this window.</p>
<script>
(function() {{
  try {{
    if (window.opener && !window.opener.closed) {{
      window.opener.postMessage({payload}, '*');
      window.close();
      return;
    }}
  }} catch (e) {{}}
  window.location.replace({json.dumps(return_to)});
}})();
</script>
</body></html>
"""
    return HTMLResponse(content=html)


@router.get(
    "/callback",
    summary="Spotify OAuth callback — exchange code for tokens",
    description=(
        "Spotify calls this endpoint with ``?code=...&state=...`` (or "
        "``?error=...`` if the listener denied access). On success "
        "persists the tokens and renders a self-closing popup page "
        "that notifies the opener window. On failure renders the same "
        "page with an error reason so the UI can surface it.\n\n"
        "**Auth:** public — required by the OAuth spec; the ``state`` "
        "HMAC and the dev-app's redirect-URI allowlist are the security "
        "boundaries here."
    ),
)
def oauth_callback(
    code: Optional[str] = Query(None),
    state: Optional[str] = Query(None),
    error: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    if error:
        logger.warning("Spotify OAuth callback returned error: %s", error)
        return _popup_completion_page(False, error)
    if not code or not state:
        return _popup_completion_page(False, "missing_code_or_state")
    if not spotify_oauth.verify_state(state):
        logger.warning("Spotify OAuth callback rejected: bad/expired state")
        return _popup_completion_page(False, "invalid_state")

    try:
        payload = spotify_oauth.exchange_code_for_tokens(code)
        spotify_oauth.save_tokens_from_exchange(db, payload)
    except Exception as e:
        logger.error("Spotify OAuth callback failed: %s", e)
        return _popup_completion_page(False, str(e)[:200])

    return _popup_completion_page(True)


@router.get(
    "/status",
    summary="Spotify OAuth connection status",
    description=(
        "Reports whether the project-owned Spotify OAuth flow is "
        "connected, as which listener, and the redirect URI the "
        "operator must add to their Spotify dev app's Redirect URIs "
        "list. Safe to poll from the admin UI.\n\n"
        "**Auth:** Bearer JWT — admin only."
    ),
)
def oauth_status(current_user: User = Depends(get_current_admin_user)):
    return JSONResponse(spotify_oauth.get_status())


@router.post(
    "/disconnect",
    summary="Forget the connected Spotify account",
    description=(
        "Deletes the singleton ``spotify_oauth_tokens`` row so no "
        "Spotify-authenticated calls are made until a super-admin "
        "reconnects. Doesn't revoke the tokens on Spotify's side; the "
        "listener can do that from their account page if desired.\n\n"
        "**Auth:** Bearer JWT — super-admin only."
    ),
)
def oauth_disconnect(current_user: User = Depends(get_current_super_admin)):
    removed = spotify_oauth.disconnect()
    return {"disconnected": removed}
