"""Project-owned Spotify Authorization-Code OAuth flow.

Replaces the Replit Spotify connector for user-authenticated calls.
The connector is hard-bound to a Spotify dev app Replit owns, whose
Users-and-Access list we cannot edit, so it can never satisfy
Spotify's Development-Mode allowlist requirement for our own dev app.

This module owns the full Authorization-Code lifecycle against the
operator's own Spotify Developer app (configured via
``SPOTIFY_CLIENT_ID`` / ``SPOTIFY_CLIENT_SECRET`` secrets):

* Build the authorize URL.
* Exchange a returned ``code`` for access + refresh tokens.
* Persist them in the singleton ``spotify_oauth_tokens`` row.
* Hand out a still-valid access token, refreshing transparently
  when fewer than 60 seconds remain on the cached one.
* Disconnect (clear the row).

The persisted refresh token is long-lived per Spotify's docs and
will be reused indefinitely until the operator clicks Disconnect or
the listener revokes the app on Spotify's side.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import logging
import os
import secrets
import time
from datetime import datetime, timedelta
from typing import Optional, Tuple

import requests

logger = logging.getLogger("cadence")

SPOTIFY_AUTHORIZE_URL = "https://accounts.spotify.com/authorize"
SPOTIFY_TOKEN_URL = "https://accounts.spotify.com/api/token"
SPOTIFY_ME_URL = "https://api.spotify.com/v1/me"

DEFAULT_SCOPES = "playlist-read-private playlist-read-collaborative user-read-email"

STATE_TTL_SECONDS = 600


def _client_id() -> Optional[str]:
    return os.getenv("SPOTIFY_CLIENT_ID")


def _client_secret() -> Optional[str]:
    return os.getenv("SPOTIFY_CLIENT_SECRET")


def _state_secret() -> str:
    return os.environ.get("SESSION_SECRET", "cadence-fallback-state-secret")


def get_redirect_uri() -> str:
    """Resolve the OAuth callback URL.

    Priority:
    1. ``SPOTIFY_REDIRECT_URI`` env var (operator override).
    2. ``{REPLIT_DEV_DOMAIN}/api/spotify/oauth/callback`` when running in
       a Replit workspace dev environment.
    3. Production fallback ``https://rythm-app.replit.app/api/spotify/oauth/callback``.

    Whichever value this returns must be added verbatim to the dev
    app's Redirect URIs list on developer.spotify.com.
    """
    explicit = os.getenv("SPOTIFY_REDIRECT_URI")
    if explicit:
        return explicit
    dev_domain = os.getenv("REPLIT_DEV_DOMAIN")
    if dev_domain:
        return f"https://{dev_domain}/api/spotify/oauth/callback"
    return "https://rythm-app.replit.app/api/spotify/oauth/callback"


def is_configured() -> bool:
    """True iff the dev-app credentials needed to OAuth are present."""
    return bool(_client_id() and _client_secret())


# ---------------------------------------------------------------------------
# Signed state cookie helpers (CSRF defense for the OAuth round-trip)
# ---------------------------------------------------------------------------

def issue_state() -> str:
    """Mint a signed, time-bounded ``state`` value.

    Format: ``<nonce>.<issued_at>.<hmac>`` — base64url(no padding).
    Verified by :func:`verify_state` on the callback. Never trust the
    ``state`` value to identify a user; it's only an integrity tag
    proving the request started from this server.
    """
    nonce = secrets.token_urlsafe(16)
    issued_at = str(int(time.time()))
    payload = f"{nonce}.{issued_at}"
    sig = hmac.new(
        _state_secret().encode("utf-8"),
        payload.encode("utf-8"),
        hashlib.sha256,
    ).digest()
    sig_b64 = base64.urlsafe_b64encode(sig).rstrip(b"=").decode("ascii")
    return f"{payload}.{sig_b64}"


def verify_state(value: str) -> bool:
    if not value or value.count(".") != 2:
        return False
    nonce, issued_at_s, sig_b64 = value.split(".", 2)
    payload = f"{nonce}.{issued_at_s}"
    expected = hmac.new(
        _state_secret().encode("utf-8"),
        payload.encode("utf-8"),
        hashlib.sha256,
    ).digest()
    expected_b64 = base64.urlsafe_b64encode(expected).rstrip(b"=").decode("ascii")
    if not hmac.compare_digest(expected_b64, sig_b64):
        return False
    try:
        issued_at = int(issued_at_s)
    except ValueError:
        return False
    # 10-minute TTL is plenty for an OAuth round-trip.
    if int(time.time()) - issued_at > 600:
        return False
    return True


# ---------------------------------------------------------------------------
# Start-flow nonce — short-lived, single-use bearer for the popup hop
# ---------------------------------------------------------------------------
#
# The browser cannot attach an Authorization header to a top-level
# ``window.open`` navigation, so the admin UI first issues a nonce via
# an XHR (which IS Bearer-auth + UserSession-checked via
# ``get_current_super_admin``), then opens
# ``/start?nonce=<value>``. The nonce is HMAC-signed, time-bounded
# (60s), and consumed exactly once via an in-process used-nonce set.
# Putting the JWT in the query string is what we explicitly avoid.

_used_start_nonces: set = set()
_used_start_nonces_capacity: int = 1024


def issue_start_nonce(user_id: int) -> str:
    """Mint a 60-second, single-use nonce binding the popup to a user."""
    rand = secrets.token_urlsafe(16)
    issued_at = str(int(time.time()))
    payload = f"{user_id}.{rand}.{issued_at}"
    sig = hmac.new(
        _state_secret().encode("utf-8"),
        payload.encode("utf-8"),
        hashlib.sha256,
    ).digest()
    sig_b64 = base64.urlsafe_b64encode(sig).rstrip(b"=").decode("ascii")
    return f"{payload}.{sig_b64}"


def verify_and_consume_start_nonce(value: str) -> Optional[int]:
    """Validate a start-flow nonce and atomically mark it used.

    Returns the embedded ``user_id`` on success, ``None`` on any
    failure (bad signature, replay, expired, malformed). The 60s TTL
    matches the time it takes a human to click *Connect* and reach
    Spotify's authorize page.
    """
    if not value or value.count(".") != 3:
        return None
    user_id_s, rand, issued_at_s, sig_b64 = value.split(".", 3)
    payload = f"{user_id_s}.{rand}.{issued_at_s}"
    expected = hmac.new(
        _state_secret().encode("utf-8"),
        payload.encode("utf-8"),
        hashlib.sha256,
    ).digest()
    expected_b64 = base64.urlsafe_b64encode(expected).rstrip(b"=").decode("ascii")
    if not hmac.compare_digest(expected_b64, sig_b64):
        return None
    try:
        issued_at = int(issued_at_s)
        user_id = int(user_id_s)
    except ValueError:
        return None
    # 60s TTL — the popup hop is supposed to be immediate.
    if int(time.time()) - issued_at > 60:
        return None
    # Replay defense: each nonce works exactly once.
    if value in _used_start_nonces:
        return None
    _used_start_nonces.add(value)
    # Bound the in-memory set — drop oldest entries when we cross
    # the cap. The 60s TTL means a churn cap of ~1k is plenty.
    if len(_used_start_nonces) > _used_start_nonces_capacity:
        _used_start_nonces.clear()
    return user_id


# ---------------------------------------------------------------------------
# Authorize URL
# ---------------------------------------------------------------------------

def build_authorize_url(state: str, scopes: str = DEFAULT_SCOPES) -> str:
    cid = _client_id()
    if not cid:
        raise RuntimeError(
            "SPOTIFY_CLIENT_ID is not set. Add it to the project's "
            "Secrets before connecting Spotify."
        )
    params = {
        "client_id": cid,
        "response_type": "code",
        "redirect_uri": get_redirect_uri(),
        "scope": scopes,
        "state": state,
        "show_dialog": "true",
    }
    from urllib.parse import urlencode
    return f"{SPOTIFY_AUTHORIZE_URL}?{urlencode(params)}"


# ---------------------------------------------------------------------------
# Token exchange + refresh
# ---------------------------------------------------------------------------

def _basic_auth_header() -> str:
    raw = f"{_client_id()}:{_client_secret()}".encode("utf-8")
    return "Basic " + base64.b64encode(raw).decode("ascii")


def exchange_code_for_tokens(code: str) -> dict:
    """Trade an OAuth ``code`` for ``access_token`` + ``refresh_token``."""
    if not is_configured():
        raise RuntimeError(
            "Spotify dev-app credentials are not set. "
            "Configure SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET first."
        )
    resp = requests.post(
        SPOTIFY_TOKEN_URL,
        data={
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": get_redirect_uri(),
        },
        headers={"Authorization": _basic_auth_header()},
        timeout=15,
    )
    if resp.status_code != 200:
        logger.error(
            "Spotify OAuth code exchange failed: %s %s",
            resp.status_code, resp.text[:300],
        )
        raise RuntimeError(
            f"Spotify rejected the OAuth code: HTTP {resp.status_code}. "
            "If the message mentions 'INVALID_CLIENT: Invalid redirect URI', "
            "the redirect URI in your Spotify dev app's Redirect URIs list "
            f"must exactly match: {get_redirect_uri()}"
        )
    return resp.json()


def refresh_access_token(refresh_token: str) -> dict:
    """Exchange a refresh token for a fresh access token."""
    if not is_configured():
        raise RuntimeError("Spotify dev-app credentials are not set.")
    resp = requests.post(
        SPOTIFY_TOKEN_URL,
        data={
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
        },
        headers={"Authorization": _basic_auth_header()},
        timeout=15,
    )
    if resp.status_code != 200:
        logger.error(
            "Spotify OAuth refresh failed: %s %s",
            resp.status_code, resp.text[:300],
        )
        raise RuntimeError(
            f"Spotify refused the refresh token (HTTP {resp.status_code}). "
            "Ask an admin to reconnect Spotify in the Integrations panel."
        )
    return resp.json()


def fetch_user_profile(access_token: str) -> dict:
    """Fetch the listener profile so we can show 'connected as' in the UI."""
    try:
        resp = requests.get(
            SPOTIFY_ME_URL,
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=10,
        )
        if resp.status_code == 200:
            return resp.json()
        logger.warning(
            "Spotify /me returned %s: %s", resp.status_code, resp.text[:200]
        )
    except Exception as e:  # pragma: no cover - defensive
        logger.warning("Spotify /me lookup failed: %s", e)
    return {}


# ---------------------------------------------------------------------------
# Persistence (singleton row)
# ---------------------------------------------------------------------------

def _get_token_row(db):
    from ..models import SpotifyOAuthToken
    return db.query(SpotifyOAuthToken).order_by(SpotifyOAuthToken.id.desc()).first()


def save_tokens_from_exchange(db, token_payload: dict) -> "object":
    """Persist a fresh authorization_code exchange result.

    Replaces any existing row so there's at most one connected listener
    at a time, matching the prior single-connector behaviour.
    """
    from ..models import SpotifyOAuthToken

    access_token = token_payload.get("access_token")
    refresh_token = token_payload.get("refresh_token")
    expires_in = int(token_payload.get("expires_in", 3600))
    scope = token_payload.get("scope")

    if not access_token or not refresh_token:
        raise RuntimeError(
            "Spotify token response was missing access_token or refresh_token"
        )

    profile = fetch_user_profile(access_token)
    display_name = profile.get("display_name")
    email = profile.get("email")
    spotify_id = profile.get("id")

    expires_at = datetime.utcnow() + timedelta(seconds=expires_in - 30)

    existing = _get_token_row(db)
    if existing:
        existing.access_token = access_token
        existing.refresh_token = refresh_token
        existing.scope = scope
        existing.token_expires_at = expires_at
        existing.connected_user_display_name = display_name
        existing.connected_user_email = email
        existing.connected_user_spotify_id = spotify_id
        existing.connected_at = datetime.utcnow()
        existing.updated_at = datetime.utcnow()
        row = existing
    else:
        row = SpotifyOAuthToken(
            access_token=access_token,
            refresh_token=refresh_token,
            scope=scope,
            token_expires_at=expires_at,
            connected_user_display_name=display_name,
            connected_user_email=email,
            connected_user_spotify_id=spotify_id,
            connected_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        db.add(row)
    db.commit()
    db.refresh(row)
    logger.info(
        "Spotify OAuth: connected as %s (%s)",
        display_name or "<unknown>", email or "<no email>",
    )
    return row


def _save_refreshed_access_token(db, row, payload: dict) -> None:
    """Update an existing row with the result of a refresh exchange.

    Spotify usually does NOT return a new refresh_token on a refresh,
    so we keep the existing one unless a new one is supplied.
    """
    access_token = payload.get("access_token")
    if not access_token:
        raise RuntimeError("Spotify refresh response missing access_token")
    expires_in = int(payload.get("expires_in", 3600))
    new_refresh = payload.get("refresh_token")
    row.access_token = access_token
    if new_refresh:
        row.refresh_token = new_refresh
    row.token_expires_at = datetime.utcnow() + timedelta(seconds=expires_in - 30)
    row.updated_at = datetime.utcnow()
    db.commit()


def get_valid_access_token() -> Optional[str]:
    """Return a still-valid access token, refreshing if needed.

    Returns ``None`` (logged at INFO, not ERROR) when no Spotify
    account has been connected yet — callers fall back to other token
    sources in that case.
    """
    if not is_configured():
        return None
    from ..models.database import engine
    from sqlalchemy.orm import sessionmaker
    Session = sessionmaker(bind=engine)
    db = Session()
    try:
        row = _get_token_row(db)
        if not row:
            logger.info("Spotify OAuth: no connected account yet")
            return None
        # Refresh if <60s remaining
        now = datetime.utcnow()
        near_expiry = row.token_expires_at and row.token_expires_at <= now + timedelta(seconds=60)
        if near_expiry:
            try:
                payload = refresh_access_token(row.refresh_token)
                _save_refreshed_access_token(db, row, payload)
                logger.info("Spotify OAuth: refreshed access token")
            except Exception as e:
                logger.error("Spotify OAuth: refresh failed: %s", e)
                # If the existing token is already past its expiry,
                # returning it would just produce 401s and would also
                # short-circuit the connector / client-credentials
                # fallback in spotify_service. Surface "no token" so
                # the chain falls through cleanly.
                if row.token_expires_at and row.token_expires_at <= now:
                    return None
        return row.access_token
    finally:
        db.close()


def get_status() -> dict:
    """Read-only summary of the connection for the admin UI."""
    if not is_configured():
        return {
            "configured": False,
            "connected": False,
            "redirect_uri": get_redirect_uri(),
        }
    from ..models.database import engine
    from sqlalchemy.orm import sessionmaker
    Session = sessionmaker(bind=engine)
    db = Session()
    try:
        row = _get_token_row(db)
        if not row:
            return {
                "configured": True,
                "connected": False,
                "redirect_uri": get_redirect_uri(),
            }
        return {
            "configured": True,
            "connected": True,
            "redirect_uri": get_redirect_uri(),
            "connected_as": row.connected_user_display_name or row.connected_user_email,
            "connected_email": row.connected_user_email,
            "connected_at": row.connected_at.isoformat() if row.connected_at else None,
            "token_expires_at": row.token_expires_at.isoformat() if row.token_expires_at else None,
            "scope": row.scope,
        }
    finally:
        db.close()


def disconnect() -> bool:
    """Delete the connected listener row. Returns True if anything was removed."""
    from ..models.database import engine
    from sqlalchemy.orm import sessionmaker
    Session = sessionmaker(bind=engine)
    db = Session()
    try:
        row = _get_token_row(db)
        if not row:
            return False
        db.delete(row)
        db.commit()
        logger.info("Spotify OAuth: disconnected")
        return True
    finally:
        db.close()
