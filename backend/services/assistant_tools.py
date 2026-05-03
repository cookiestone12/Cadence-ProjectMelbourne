"""Tool registry for the Cadence in-app assistant.

Exposes:
  * ``TOOL_SCHEMAS`` — OpenAI tool definitions (function calling) the
    chat route hands to ``client.chat.completions.create(tools=...)``.
  * ``dispatch_tool(name, args, db, org_id, user_id)`` — runs a tool by
    name, returning a JSON-serialisable ``dict``. Read tools execute
    immediately. Write tools build a :class:`ProposedAction`, store it,
    and return its id + summary so the user can confirm or cancel
    before any DB mutation happens.
  * ``execute_proposed_action(action_id, db, user)`` — performs the
    actual mutation associated with a stored proposed action and
    writes an audit-log entry tagged ``source="assistant"``.

Org scoping: every tool requires ``org_id`` and refuses to operate
without one. Tools that take an entity id (song / creator / etc) re-
verify ``organization_id == org_id`` before returning anything.

================================================================
PERMANENTLY DISALLOWED through the assistant — DO NOT add tools for
these no matter how natural the user's request feels:
  * Bulk delete of any kind.
  * Bulk status change across many rows in one call.
  * Royalty statement ingestion / re-parsing / re-allocation.
  * Royalty allocation rewrites or override of computed earnings.
  * Multi-payment posting or any payment beyond a single recorded
    cash disbursement.
  * Org-settings mutations (plan, branding, access codes, billing).
  * User or role management (invite, remove, reassign).
  * Anything that touches Stripe IDs, password hashes, super-admin
    flags, or computed totals — see ``BLOCKED_PAYLOAD_FIELDS``.
The assistant is a single-step admin helper, not a batch processor.
================================================================
"""

from __future__ import annotations

import logging
import re
import threading
from datetime import datetime, timedelta, date
from typing import Any, Callable
from uuid import uuid4

from sqlalchemy import or_, and_, desc, func
from sqlalchemy.orm import Session

from ..models import (
    Song,
    SongCredit,
    Creator,
    Contract,
    ContractParty,
    Placement,
    ActionItem,
    OrganizationMember,
    User,
    SongStreamingMetrics,
    RoyaltyStatement,
    RoyaltyStatementLine,
    Payment,
)
from ..models.catalog import SongRegistration
from ..models.releases import Release
from ..models.royalties import Fee

logger = logging.getLogger("cadence")

PROPOSED_ACTION_TTL_SECONDS = 600  # 10 minutes
PLACEMENT_STATUSES = {
    "PITCHED", "IN_REVIEW", "IN_NEGOTIATION", "SECURED",
    "DELIVERED", "AIRED", "PAID", "DECLINED", "CANCELLED",
}

# ---- Static-choice enums for the new write tools (Task #196 Phase 3B) ----
REGISTRY_TYPES = {"BMI", "ASCAP", "SESAC", "GMR", "MLC", "SOUNDEXCHANGE", "HFA"}
REGISTRATION_STATUSES = {"NOT_STARTED", "PENDING", "REGISTERED",
                          "REJECTED", "NOT_APPLICABLE"}
FEE_TYPES = {"MANAGEMENT_FEE", "ADMIN_FEE", "DISTRIBUTION_FEE",
             "SYNC_FEE", "LEGAL_FEE", "OTHER"}
# Cadence stores Song.release_status as lowercase strings
# ("unreleased" / "released" / "archived"); the tool surface uses the
# friendlier UPPERCASE labels and maps on the way in.
SONG_STATUSES = {"DRAFT", "RELEASED", "ARCHIVED"}
SONG_STATUS_TO_DB = {"DRAFT": "unreleased", "RELEASED": "released",
                      "ARCHIVED": "archived"}
CREATOR_PROS = {"BMI", "ASCAP", "SESAC", "GMR", "SOCAN",
                "PRS", "PRO_OTHER", "NONE"}
RELEASE_STATUSES = {"DRAFT", "READY", "SUBMITTED", "RELEASED"}
RELEASE_TYPES = {"SINGLE", "EP", "ALBUM", "COMPILATION", "MIXTAPE", "OTHER"}
CONTRACT_STATUSES = {"DRAFT", "PENDING", "ACTIVE", "EXPIRED", "TERMINATED"}
# Action items in the codebase use these literals; the tool also accepts
# the friendly aliases OPEN (= PENDING) and DONE (= COMPLETED).
ACTION_ITEM_STATUSES = {"PENDING", "IN_PROGRESS", "COMPLETED", "CANCELLED"}
ACTION_ITEM_STATUS_ALIASES = {
    "OPEN": "PENDING",
    "DONE": "COMPLETED",
    "PENDING": "PENDING",
    "IN_PROGRESS": "IN_PROGRESS",
    "COMPLETED": "COMPLETED",
    "CANCELLED": "CANCELLED",
}

# ---- Security: payload field blocklist (Task #196 Phase 4 step 20) ----
# Any of these keys are stripped from a ProposedAction.payload before any
# executor runs. Belt-and-braces — no current tool builds payloads with
# these keys, but a malicious or buggy tool definition (or a future one)
# could, and we want a single chokepoint to enforce it.
BLOCKED_PAYLOAD_FIELDS = frozenset({
    "organization_id", "user_id", "is_admin", "is_super_admin",
    "password_hash", "total_revenue_cents", "valuation_amount",
    "stripe_customer_id", "stripe_connect_id",
})

# ---- Security: per-user rate limit (Task #196 Phase 4 step 19) ----
WRITE_RATE_LIMIT = 20  # confirmed actions
WRITE_RATE_WINDOW_SECONDS = 3600  # rolling 1 hour
_RATE_LOG: dict[int, list[datetime]] = {}
_RATE_LOCK = threading.Lock()


class RateLimitExceeded(Exception):
    """Raised by ``execute_proposed_action`` when the per-user write
    rate limit (20/hour) is exceeded. The chat route maps this to HTTP
    429 with a retry-after-style message."""


class BlockedPayloadField(Exception):
    """Raised when a ProposedAction.payload contains a field on the
    BLOCKED_PAYLOAD_FIELDS deny-list. The mutation is aborted before any
    DB write happens — the platform refuses to silently sanitise."""


def _check_rate_limit(user_id: int) -> None:
    """Inspect the per-user counter — RAISE if the user is at the cap,
    but do **not** record this attempt. Recording happens post-commit
    via :func:`_record_successful_write` so failed confirms don't burn
    quota."""
    now = datetime.utcnow()
    cutoff = now - timedelta(seconds=WRITE_RATE_WINDOW_SECONDS)
    with _RATE_LOCK:
        bucket = _RATE_LOG.get(user_id) or []
        bucket = [t for t in bucket if t > cutoff]
        _RATE_LOG[user_id] = bucket
        if len(bucket) >= WRITE_RATE_LIMIT:
            oldest = bucket[0]
            retry_in = WRITE_RATE_WINDOW_SECONDS - int(
                (now - oldest).total_seconds()
            )
            retry_in = max(retry_in, 1)
            raise RateLimitExceeded(
                f"You've confirmed {WRITE_RATE_LIMIT} assistant write actions "
                f"in the last hour. Please wait about {retry_in // 60 + 1} "
                "minute(s) before confirming another."
            )


def _record_successful_write(user_id: int) -> None:
    """Append `now` to the user's bucket. Called only after the executor
    + commit succeed, so the 20/hr cap counts *confirmed* writes only."""
    now = datetime.utcnow()
    cutoff = now - timedelta(seconds=WRITE_RATE_WINDOW_SECONDS)
    with _RATE_LOCK:
        bucket = _RATE_LOG.get(user_id) or []
        bucket = [t for t in bucket if t > cutoff]
        bucket.append(now)
        _RATE_LOG[user_id] = bucket


def _assert_no_blocked_fields(payload: dict | None) -> None:
    if not payload:
        return
    offenders = sorted(set(payload.keys()) & BLOCKED_PAYLOAD_FIELDS)
    if offenders:
        raise BlockedPayloadField(
            "Refusing to execute this action — the proposed payload contains "
            f"protected field(s): {', '.join(offenders)}. The assistant is "
            "not permitted to set these directly."
        )


# ----------------------------------------------------------------------
# Proposed-action store (process-memory; rebooting clears it)
# ----------------------------------------------------------------------

class ProposedAction:
    __slots__ = ("id", "kind", "summary", "payload", "org_id", "user_id",
                 "created_at", "expires_at")

    def __init__(self, *, kind: str, summary: str, payload: dict,
                 org_id: int, user_id: int):
        self.id = str(uuid4())
        self.kind = kind
        self.summary = summary
        self.payload = payload
        self.org_id = org_id
        self.user_id = user_id
        self.created_at = datetime.utcnow()
        self.expires_at = self.created_at + timedelta(
            seconds=PROPOSED_ACTION_TTL_SECONDS
        )

    def is_expired(self) -> bool:
        return datetime.utcnow() >= self.expires_at

    def to_public_dict(self) -> dict:
        return {
            "id": self.id,
            "kind": self.kind,
            "summary": self.summary,
            "payload": self.payload,
            "expires_at": self.expires_at.isoformat() + "Z",
        }


# Production runs gunicorn with workers=1 (see backend/gunicorn_config.py),
# so a process-memory store is safe — every confirm hits the same worker
# that produced the proposed_action. The lock below makes the
# pop-and-execute critical section atomic across threads / async tasks
# inside that worker, so a double-clicked Confirm button cannot execute
# the same action twice.
_STORE: dict[str, ProposedAction] = {}
_CLAIM_LOCK = threading.Lock()


def _gc_locked() -> None:
    """Drop expired actions. Caller holds ``_CLAIM_LOCK``."""
    now = datetime.utcnow()
    expired = [k for k, v in _STORE.items() if v.expires_at <= now]
    for k in expired:
        _STORE.pop(k, None)


def store_proposed_action(action: ProposedAction) -> None:
    with _CLAIM_LOCK:
        _gc_locked()
        _STORE[action.id] = action


def get_proposed_action(action_id: str) -> ProposedAction | None:
    with _CLAIM_LOCK:
        _gc_locked()
        return _STORE.get(action_id)


def remove_proposed_action(action_id: str) -> None:
    with _CLAIM_LOCK:
        _STORE.pop(action_id, None)


def _claim_proposed_action(action_id: str, user_id: int) -> ProposedAction:
    """Atomically pop a proposed action so concurrent confirms can't double-
    execute. Raises ``LookupError`` if missing/expired or
    ``PermissionError`` if owned by a different user.
    """
    with _CLAIM_LOCK:
        _gc_locked()
        pa = _STORE.get(action_id)
        if pa is None:
            raise LookupError("Proposed action not found.")
        if pa.is_expired():
            _STORE.pop(action_id, None)
            raise LookupError("Proposed action has expired.")
        if pa.user_id != user_id:
            raise PermissionError(
                "This action was proposed by a different user."
            )
        # Pop here — one winner, all subsequent confirms see "not found".
        return _STORE.pop(action_id)


def clear_proposed_actions_for_test() -> None:
    """Test hook — wipes the store."""
    with _CLAIM_LOCK:
        _STORE.clear()


# ----------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------

def _truncate(value: str | None, n: int = 80) -> str | None:
    if not value:
        return value
    return value if len(value) <= n else value[: n - 1] + "…"


def _song_brief(song: Song) -> dict:
    return {
        "id": song.id,
        "title": song.title,
        "primary_artist": song.primary_artist,
        "isrc": song.isrc,
        "iswc": song.iswc,
        "release_status": song.release_status,
        "is_released": bool(song.is_released),
        "health_score": round(song.status_health_score or 0.0, 1),
    }


def _creator_brief(c: Creator) -> dict:
    name = getattr(c, "name", None) or getattr(c, "display_name", None) or f"Creator #{c.id}"
    return {
        "id": c.id,
        "name": name,
        "email": getattr(c, "email", None),
        "creator_type": getattr(c, "creator_type", None) or getattr(c, "type", None),
    }


def _contract_brief(c: Contract) -> dict:
    return {
        "id": c.id,
        "title": c.title,
        "contract_type": c.contract_type,
        "status": c.status,
        "start_date": c.start_date.isoformat() if c.start_date else None,
        "end_date": c.end_date.isoformat() if c.end_date else None,
        "advance_amount": c.advance_amount,
        "advance_currency": c.advance_currency,
    }


def _placement_brief(p: Placement) -> dict:
    return {
        "id": p.id,
        "title": p.title,
        "status": p.status,
        "placement_type": p.placement_type,
        "client_name": p.client_name,
        "project_name": p.project_name,
        "license_fee": p.license_fee,
        "license_currency": p.license_currency,
        "song_id": p.song_id,
    }


# ----------------------------------------------------------------------
# READ TOOLS
# ----------------------------------------------------------------------

_SONG_SEARCH_STOPWORDS = {
    "by", "feat", "feat.", "ft", "ft.", "featuring", "with",
    "the", "a", "an", "and", "&", "song", "track",
}


def _read_search_songs(db: Session, org_id: int, user_id: int,
                       query: str | None = None, limit: int = 10) -> dict:
    limit = max(1, min(int(limit or 10), 25))
    q = db.query(Song).filter(Song.organization_id == org_id)
    if query and query.strip():
        # Tokenize on whitespace + common punctuation so a query like
        # "Down by T-Pain feat. T.I." matches a row whose title is
        # "Down" and artist is "T-Pain feat. T.I." (the tokens live in
        # different columns). Each non-stopword token must match at
        # least one searchable field; tokens are AND-ed together.
        raw = query.strip()
        tokens = [
            t for t in re.split(r"[\s,;/]+", raw) if t
        ]
        meaningful = [
            t for t in tokens if t.lower() not in _SONG_SEARCH_STOPWORDS
        ] or tokens  # fall back to the raw tokens if all were stopwords
        for tok in meaningful:
            like = f"%{tok}%"
            q = q.filter(or_(
                Song.title.ilike(like),
                Song.primary_artist.ilike(like),
                Song.isrc.ilike(like),
                Song.iswc.ilike(like),
            ))
        # Also try the original full phrase as a single ILIKE — if a
        # title literally contains "Down by T-Pain", surface it first.
        rows = q.order_by(desc(Song.updated_at)).limit(limit).all()
        if not rows:
            like = f"%{raw}%"
            rows = (
                db.query(Song)
                .filter(Song.organization_id == org_id)
                .filter(or_(
                    Song.title.ilike(like),
                    Song.primary_artist.ilike(like),
                    Song.isrc.ilike(like),
                    Song.iswc.ilike(like),
                ))
                .order_by(desc(Song.updated_at))
                .limit(limit)
                .all()
            )
    else:
        rows = q.order_by(desc(Song.updated_at)).limit(limit).all()
    return {"count": len(rows), "results": [_song_brief(s) for s in rows]}


def _read_get_song_health(db: Session, org_id: int, user_id: int,
                          song_id: int) -> dict:
    song = db.query(Song).filter(
        Song.id == song_id, Song.organization_id == org_id
    ).first()
    if not song:
        # Actionable error: tell the model exactly what to do next so a
        # bad/hallucinated song_id doesn't dead-end the turn. The chat
        # UI was producing flat "Song not found" replies even when the
        # song clearly existed in the catalog because the model never
        # fell back to search_songs.
        return {
            "error": (
                f"No song with id={song_id} exists in this organization. "
                "Do NOT tell the user the song is missing. Instead call "
                "the `search_songs` tool with the song title and/or "
                "artist from the user's message (or the page context) "
                "to find the correct song_id, then retry get_song_health."
            ),
            "next_action": "search_songs",
        }

    gaps = []
    if not song.isrc:
        gaps.append("Missing ISRC")
    if not song.iswc:
        gaps.append("Missing ISWC")
    if not song.has_contract_executed:
        gaps.append("No executed contract on file")
    if not song.is_registered_with_pro:
        gaps.append("Not registered with PRO")
    if song.is_released and not song.is_paid:
        gaps.append("Released but no payment recorded")

    credit_count = db.query(func.count(SongCredit.id)).filter(
        SongCredit.song_id == song.id
    ).scalar() or 0

    return {
        **_song_brief(song),
        "label": song.label,
        "publishing_percentage": song.publishing_percentage,
        "master_percentage": song.master_percentage,
        "credit_count": int(credit_count),
        "gaps": gaps,
    }


def _read_search_creators(db: Session, org_id: int, user_id: int,
                          query: str | None = None, limit: int = 10) -> dict:
    limit = max(1, min(int(limit or 10), 25))
    q = db.query(Creator).filter(Creator.organization_id == org_id)
    if query:
        like = f"%{query.strip()}%"
        # Creator schema names vary — try common columns defensively.
        clauses = []
        for col_name in ("name", "display_name", "stage_name", "legal_name", "email"):
            col = getattr(Creator, col_name, None)
            if col is not None:
                clauses.append(col.ilike(like))
        if clauses:
            q = q.filter(or_(*clauses))
    rows = q.limit(limit).all()
    return {"count": len(rows), "results": [_creator_brief(c) for c in rows]}


def _read_get_creator_summary(db: Session, org_id: int, user_id: int,
                              creator_id: int) -> dict:
    c = db.query(Creator).filter(
        Creator.id == creator_id, Creator.organization_id == org_id
    ).first()
    if not c:
        return {"error": "Creator not found in your organization."}

    song_ids = [
        sid for (sid,) in db.query(SongCredit.song_id)
        .filter(SongCredit.creator_id == creator_id)
        .distinct()
        .all()
    ]
    song_count = len(song_ids)

    contract_count = db.query(func.count(Contract.id)).filter(
        Contract.organization_id == org_id,
        Contract.creator_id == creator_id,
    ).scalar() or 0

    open_actions = db.query(func.count(ActionItem.id)).filter(
        ActionItem.organization_id == org_id,
        ActionItem.creator_id == creator_id,
        ActionItem.status != "COMPLETED",
    ).scalar() or 0

    return {
        **_creator_brief(c),
        "song_count": song_count,
        "contract_count": int(contract_count),
        "open_action_items": int(open_actions),
    }


def _read_search_contracts(db: Session, org_id: int, user_id: int,
                           query: str | None = None,
                           status: str | None = None,
                           limit: int = 10) -> dict:
    limit = max(1, min(int(limit or 10), 25))
    q = db.query(Contract).filter(Contract.organization_id == org_id)
    if query:
        like = f"%{query.strip()}%"
        q = q.filter(or_(
            Contract.title.ilike(like),
            Contract.reference_number.ilike(like),
        ))
    if status:
        q = q.filter(Contract.status == status.upper())
    rows = q.order_by(desc(Contract.updated_at)).limit(limit).all()
    return {"count": len(rows), "results": [_contract_brief(c) for c in rows]}


def _read_list_expiring_contracts(db: Session, org_id: int, user_id: int,
                                  days: int = 90) -> dict:
    days = max(1, min(int(days or 90), 365))
    cutoff = date.today() + timedelta(days=days)
    rows = (
        db.query(Contract)
        .filter(
            Contract.organization_id == org_id,
            Contract.end_date.isnot(None),
            Contract.end_date <= cutoff,
            Contract.end_date >= date.today(),
            Contract.status.in_(["ACTIVE", "PENDING"]),
        )
        .order_by(Contract.end_date.asc())
        .limit(25)
        .all()
    )
    return {
        "count": len(rows),
        "window_days": days,
        "results": [_contract_brief(c) for c in rows],
    }


_PERIOD_SHORTCUTS = {
    "last_30d", "last_30_days",
    "last_90d", "last_90_days",
    "last_quarter", "last_q", "qtd",
    "ytd", "year_to_date",
    "last_year", "prior_year",
    "all_time", "all",
}


def _resolve_period(period: str | None,
                    period_start: str | None,
                    period_end: str | None) -> tuple[date | None, date | None, str]:
    """Return (start, end, label). Explicit start/end win over the shortcut.
    Falls back to (None, None, 'all_time') if nothing was passed.
    """
    def _parse(d: str | None) -> date | None:
        if not d:
            return None
        try:
            return datetime.fromisoformat(str(d).replace("Z", "")).date()
        except Exception:
            try:
                return date.fromisoformat(str(d)[:10])
            except Exception:
                return None

    s = _parse(period_start)
    e = _parse(period_end)
    if s or e:
        label = f"{s.isoformat() if s else '...'} → {e.isoformat() if e else '...'}"
        return s, e, label

    today = date.today()
    key = (period or "").strip().lower()
    if key in {"last_30d", "last_30_days"}:
        return today - timedelta(days=30), today, "last 30 days"
    if key in {"last_90d", "last_90_days"}:
        return today - timedelta(days=90), today, "last 90 days"
    if key in {"last_quarter", "last_q", "qtd"}:
        # The full prior calendar quarter, e.g. May → Jan-Mar.
        q = (today.month - 1) // 3  # 0..3 for current quarter
        if q == 0:
            start = date(today.year - 1, 10, 1)
            end = date(today.year - 1, 12, 31)
        else:
            start_month = (q - 1) * 3 + 1
            start = date(today.year, start_month, 1)
            # last day of month start_month+2
            end_month = start_month + 2
            if end_month == 12:
                end = date(today.year, 12, 31)
            else:
                end = date(today.year, end_month + 1, 1) - timedelta(days=1)
        return start, end, "last quarter"
    if key in {"ytd", "year_to_date"}:
        return date(today.year, 1, 1), today, "year to date"
    if key in {"last_year", "prior_year"}:
        return (date(today.year - 1, 1, 1),
                date(today.year - 1, 12, 31),
                f"{today.year - 1}")
    return None, None, "all time"


def _read_get_royalty_summary_for_song(db: Session, org_id: int, user_id: int,
                                       song_id: int,
                                       period: str | None = None,
                                       period_start: str | None = None,
                                       period_end: str | None = None) -> dict:
    song = db.query(Song).filter(
        Song.id == song_id, Song.organization_id == org_id
    ).first()
    if not song:
        return {
            "error": (
                f"No song with id={song_id} exists in this organization. "
                "Do NOT tell the user the song is missing. Call "
                "`search_songs` with the song title and/or artist first "
                "to find the correct song_id, then retry this tool."
            ),
            "next_action": "search_songs",
        }

    p_start, p_end, p_label = _resolve_period(period, period_start, period_end)

    total_streams = db.query(
        func.coalesce(func.sum(SongStreamingMetrics.total_streams), 0)
    ).filter(SongStreamingMetrics.song_id == song.id).scalar() or 0

    line_q = (
        db.query(
            func.coalesce(func.sum(RoyaltyStatementLine.net_amount), 0.0),
            func.count(RoyaltyStatementLine.id),
        )
        .join(RoyaltyStatement,
              RoyaltyStatement.id == RoyaltyStatementLine.statement_id)
        .filter(
            RoyaltyStatement.organization_id == org_id,
            RoyaltyStatementLine.matched_song_id == song.id,
        )
    )
    if p_start is not None:
        # Period overlap: statement.period_end >= window.start
        line_q = line_q.filter(or_(
            RoyaltyStatement.period_end.is_(None),
            RoyaltyStatement.period_end >= p_start,
        ))
    if p_end is not None:
        line_q = line_q.filter(or_(
            RoyaltyStatement.period_start.is_(None),
            RoyaltyStatement.period_start <= p_end,
        ))
    net_amount, line_count = line_q.first() or (0.0, 0)

    return {
        "song_id": song.id,
        "song_title": song.title,
        "period": p_label,
        "period_start": p_start.isoformat() if p_start else None,
        "period_end": p_end.isoformat() if p_end else None,
        "total_streams": int(total_streams or 0),
        "matched_statement_lines": int(line_count or 0),
        "net_royalties": round(float(net_amount or 0.0), 2),
        "currency": "USD",
    }


def _read_list_action_items_for_user(db: Session, org_id: int, user_id: int,
                                     status: str = "PENDING",
                                     limit: int = 10) -> dict:
    limit = max(1, min(int(limit or 10), 25))
    q = db.query(ActionItem).filter(
        ActionItem.organization_id == org_id,
    )
    status = (status or "PENDING").upper()
    if status == "OPEN":
        q = q.filter(ActionItem.status != "COMPLETED")
    elif status:
        q = q.filter(ActionItem.status == status)
    q = q.filter(or_(
        ActionItem.assigned_to_user_id == user_id,
        ActionItem.assigned_to_user_id.is_(None),
    ))
    rows = q.order_by(
        ActionItem.priority.asc(),
        ActionItem.deadline.is_(None).asc(),
        ActionItem.deadline.asc(),
        desc(ActionItem.created_at),
    ).limit(limit).all()
    return {
        "count": len(rows),
        "results": [
            {
                "id": a.id,
                "title": a.title,
                "description": _truncate(a.description, 140),
                "priority": a.priority,
                "status": a.status,
                "deadline": a.deadline.isoformat() if a.deadline else None,
                "creator_id": a.creator_id,
                "song_id": a.song_id,
            }
            for a in rows
        ],
    }


# ----------------------------------------------------------------------
# WRITE TOOLS — these only build a ProposedAction, never mutate.
# ----------------------------------------------------------------------

def _write_create_song(db: Session, org_id: int, user_id: int,
                       title: str, primary_artist: str | None = None,
                       isrc: str | None = None,
                       iswc: str | None = None,
                       notes: str | None = None) -> dict:
    if not title or not title.strip():
        return {"error": "title is required."}
    payload = {
        "title": title.strip(),
        "primary_artist": (primary_artist or "Unknown").strip() or "Unknown",
        "isrc": (isrc or "").strip() or None,
        "iswc": (iswc or "").strip() or None,
        "notes": (notes or "").strip() or None,
    }
    summary = (
        f"Add song \"{payload['title']}\" by {payload['primary_artist']} "
        "to the catalog."
    )
    pa = ProposedAction(
        kind="create_song", summary=summary, payload=payload,
        org_id=org_id, user_id=user_id,
    )
    store_proposed_action(pa)
    return {"proposed_action": pa.to_public_dict()}


def _write_create_placement(db: Session, org_id: int, user_id: int,
                            title: str,
                            song_id: int | None = None,
                            placement_type: str = "SYNC",
                            client_name: str | None = None,
                            project_name: str | None = None,
                            license_fee: float | None = None,
                            notes: str | None = None) -> dict:
    if not title or not title.strip():
        return {"error": "title is required."}
    if song_id is not None:
        song = db.query(Song).filter(
            Song.id == song_id, Song.organization_id == org_id
        ).first()
        if not song:
            return {"error": "song_id does not belong to your organization."}
    payload = {
        "title": title.strip(),
        "song_id": song_id,
        "placement_type": (placement_type or "SYNC").upper(),
        "client_name": (client_name or "").strip() or None,
        "project_name": (project_name or "").strip() or None,
        "license_fee": float(license_fee) if license_fee is not None else None,
        "notes": (notes or "").strip() or None,
    }
    summary_bits = [f"Create a {payload['placement_type']} placement \"{payload['title']}\""]
    if payload["client_name"]:
        summary_bits.append(f"with {payload['client_name']}")
    if payload["license_fee"]:
        summary_bits.append(f"for ${payload['license_fee']:,.0f}")
    summary = " ".join(summary_bits) + "."
    pa = ProposedAction(
        kind="create_placement", summary=summary, payload=payload,
        org_id=org_id, user_id=user_id,
    )
    store_proposed_action(pa)
    return {"proposed_action": pa.to_public_dict()}


def _write_update_placement_status(db: Session, org_id: int, user_id: int,
                                   placement_id: int,
                                   new_status: str) -> dict:
    placement = db.query(Placement).filter(
        Placement.id == placement_id,
        Placement.organization_id == org_id,
    ).first()
    if not placement:
        return {"error": "Placement not found in your organization."}
    new_status = (new_status or "").upper()
    if new_status not in PLACEMENT_STATUSES:
        return {"error": f"Invalid status. Allowed: {sorted(PLACEMENT_STATUSES)}"}
    payload = {
        "placement_id": placement_id,
        "from_status": placement.status,
        "to_status": new_status,
        "title": placement.title,
    }
    summary = (
        f"Move placement \"{placement.title}\" "
        f"from {placement.status} to {new_status}."
    )
    pa = ProposedAction(
        kind="update_placement_status", summary=summary, payload=payload,
        org_id=org_id, user_id=user_id,
    )
    store_proposed_action(pa)
    return {"proposed_action": pa.to_public_dict()}


def _write_create_action_item(db: Session, org_id: int, user_id: int,
                              title: str,
                              description: str | None = None,
                              priority: int = 2,
                              creator_id: int | None = None,
                              song_id: int | None = None,
                              deadline: str | None = None) -> dict:
    if not title or not title.strip():
        return {"error": "title is required."}
    if creator_id is not None:
        ok = db.query(Creator.id).filter(
            Creator.id == creator_id, Creator.organization_id == org_id
        ).first()
        if not ok:
            return {"error": "creator_id does not belong to your organization."}
    if song_id is not None:
        ok = db.query(Song.id).filter(
            Song.id == song_id, Song.organization_id == org_id
        ).first()
        if not ok:
            return {"error": "song_id does not belong to your organization."}
    parsed_deadline = None
    if deadline:
        try:
            parsed_deadline = datetime.fromisoformat(deadline.replace("Z", "+00:00"))
        except ValueError:
            return {"error": "deadline must be ISO-8601 (e.g. 2026-06-01)."}
    try:
        priority_i = int(priority)
    except (TypeError, ValueError):
        priority_i = 2
    if priority_i not in (1, 2, 3):
        priority_i = 2
    payload = {
        "title": title.strip(),
        "description": (description or "").strip() or None,
        "priority": priority_i,
        "creator_id": creator_id,
        "song_id": song_id,
        "deadline": parsed_deadline.isoformat() if parsed_deadline else None,
    }
    summary = f"Create action item \"{payload['title']}\"."
    pa = ProposedAction(
        kind="create_action_item", summary=summary, payload=payload,
        org_id=org_id, user_id=user_id,
    )
    store_proposed_action(pa)
    return {"proposed_action": pa.to_public_dict()}


def _write_mark_song_released(db: Session, org_id: int, user_id: int,
                              song_id: int,
                              release_date: str | None = None) -> dict:
    song = db.query(Song).filter(
        Song.id == song_id, Song.organization_id == org_id
    ).first()
    if not song:
        return {"error": "Song not found in your organization."}
    parsed_date = None
    if release_date:
        try:
            parsed_date = date.fromisoformat(str(release_date)[:10])
        except ValueError:
            return {"error": "release_date must be ISO-8601 (YYYY-MM-DD)."}
    payload = {
        "song_id": song.id,
        "title": song.title,
        "release_date": parsed_date.isoformat() if parsed_date else None,
        "from_release_status": song.release_status,
        "from_is_released": bool(song.is_released),
    }
    summary_bits = [f"Mark song \"{song.title}\" as released"]
    if parsed_date:
        summary_bits.append(f"with release date {parsed_date.isoformat()}")
    summary = " ".join(summary_bits) + "."
    pa = ProposedAction(
        kind="mark_song_released", summary=summary, payload=payload,
        org_id=org_id, user_id=user_id,
    )
    store_proposed_action(pa)
    return {"proposed_action": pa.to_public_dict()}


def _write_update_song_metadata(db: Session, org_id: int, user_id: int,
                                song_id: int,
                                title: str | None = None,
                                isrc: str | None = None,
                                iswc: str | None = None) -> dict:
    song = db.query(Song).filter(
        Song.id == song_id, Song.organization_id == org_id
    ).first()
    if not song:
        return {"error": "Song not found in your organization."}

    changes: dict = {}
    if title is not None:
        new_title = (title or "").strip()
        if not new_title:
            return {"error": "title cannot be blank."}
        if new_title != (song.title or ""):
            changes["title"] = {"old": song.title, "new": new_title}
    if isrc is not None:
        new_isrc = (isrc or "").strip() or None
        if new_isrc != song.isrc:
            changes["isrc"] = {"old": song.isrc, "new": new_isrc}
    if iswc is not None:
        new_iswc = (iswc or "").strip() or None
        if new_iswc != song.iswc:
            changes["iswc"] = {"old": song.iswc, "new": new_iswc}

    if not changes:
        return {"error": "No metadata fields changed."}

    payload = {
        "song_id": song.id,
        "title": song.title,
        "changes": changes,
    }
    fields = ", ".join(sorted(changes.keys()))
    summary = f"Update {fields} on song \"{song.title}\"."
    pa = ProposedAction(
        kind="update_song_metadata", summary=summary, payload=payload,
        org_id=org_id, user_id=user_id,
    )
    store_proposed_action(pa)
    return {"proposed_action": pa.to_public_dict()}


def _write_assign_action_item(db: Session, org_id: int, user_id: int,
                              action_item_id: int,
                              assignee_user_id: int | None) -> dict:
    item = db.query(ActionItem).filter(
        ActionItem.id == action_item_id,
        ActionItem.organization_id == org_id,
    ).first()
    if not item:
        return {"error": "Action item not found in your organization."}

    new_assignee: int | None = None
    new_name: str | None = None
    if assignee_user_id is not None:
        try:
            assignee_id_int = int(assignee_user_id)
        except (TypeError, ValueError):
            return {"error": "assignee_user_id must be an integer or null."}
        member = db.query(OrganizationMember).filter(
            OrganizationMember.user_id == assignee_id_int,
            OrganizationMember.organization_id == org_id,
        ).first()
        if not member:
            return {"error": "assignee_user_id is not a member of your organization."}
        assignee = db.query(User).filter(User.id == assignee_id_int).first()
        if not assignee:
            return {"error": "Assignee user not found."}
        new_assignee = assignee_id_int
        new_name = (
            getattr(assignee, "username", None)
            or getattr(assignee, "email", None)
            or f"User #{assignee_id_int}"
        )

    payload = {
        "action_item_id": item.id,
        "title": item.title,
        "from_assignee_user_id": item.assigned_to_user_id,
        "to_assignee_user_id": new_assignee,
    }
    if new_assignee is None:
        summary = f"Unassign action item \"{item.title}\"."
    else:
        summary = (
            f"Assign action item \"{item.title}\" to {new_name}."
        )
    pa = ProposedAction(
        kind="assign_action_item", summary=summary, payload=payload,
        org_id=org_id, user_id=user_id,
    )
    store_proposed_action(pa)
    return {"proposed_action": pa.to_public_dict()}


def _write_add_song_credit(db: Session, org_id: int, user_id: int,
                           song_id: int,
                           creator_id: int,
                           role: str,
                           pub_share: float | None = None,
                           master_share: float | None = None) -> dict:
    if not role or not str(role).strip():
        return {"error": "role is required."}
    song = db.query(Song).filter(
        Song.id == song_id, Song.organization_id == org_id
    ).first()
    if not song:
        return {"error": "Song not found in your organization."}
    creator = db.query(Creator).filter(
        Creator.id == creator_id, Creator.organization_id == org_id
    ).first()
    if not creator:
        return {"error": "Creator not found in your organization."}

    def _coerce_share(name: str, val) -> tuple[float | None, str | None]:
        if val is None:
            return None, None
        try:
            f = float(val)
        except (TypeError, ValueError):
            return None, f"{name} must be a number between 0 and 100."
        if f < 0 or f > 100:
            return None, f"{name} must be between 0 and 100."
        return f, None

    pub, err = _coerce_share("pub_share", pub_share)
    if err:
        return {"error": err}
    mas, err = _coerce_share("master_share", master_share)
    if err:
        return {"error": err}

    creator_name = (
        getattr(creator, "display_name", None)
        or getattr(creator, "name", None)
        or f"Creator #{creator.id}"
    )
    payload = {
        "song_id": song.id,
        "song_title": song.title,
        "creator_id": creator.id,
        "creator_name": creator_name,
        "role": str(role).strip(),
        "pub_share": pub,
        "master_share": mas,
    }
    summary_bits = [
        f"Add credit: {creator_name} as {payload['role']} on \"{song.title}\""
    ]
    extras: list[str] = []
    if pub is not None:
        extras.append(f"pub {pub:g}%")
    if mas is not None:
        extras.append(f"master {mas:g}%")
    if extras:
        summary_bits.append(f"({', '.join(extras)})")
    summary = " ".join(summary_bits) + "."
    pa = ProposedAction(
        kind="add_song_credit", summary=summary, payload=payload,
        org_id=org_id, user_id=user_id,
    )
    store_proposed_action(pa)
    return {"proposed_action": pa.to_public_dict()}


def _write_record_payment(db: Session, org_id: int, user_id: int,
                          payee_id: int,
                          amount_cents: int,
                          currency: str = "USD",
                          contract_id: int | None = None,
                          payment_method: str | None = None,
                          payment_reference: str | None = None,
                          notes: str | None = None) -> dict:
    payee = db.query(Creator).filter(
        Creator.id == payee_id, Creator.organization_id == org_id
    ).first()
    if not payee:
        return {"error": "payee_id does not belong to your organization."}
    try:
        amount_int = int(amount_cents)
    except (TypeError, ValueError):
        return {"error": "amount_cents must be an integer (in cents)."}
    if amount_int <= 0:
        return {"error": "amount_cents must be positive."}
    if contract_id is not None:
        contract = db.query(Contract).filter(
            Contract.id == contract_id, Contract.organization_id == org_id
        ).first()
        if not contract:
            return {"error": "contract_id does not belong to your organization."}

    payee_name = (
        getattr(payee, "display_name", None)
        or getattr(payee, "name", None)
        or f"Creator #{payee.id}"
    )
    payload = {
        "payee_id": payee.id,
        "payee_name": payee_name,
        "amount_cents": amount_int,
        "currency": (currency or "USD").upper(),
        "contract_id": contract_id,
        "payment_method": (payment_method or "").strip() or None,
        "payment_reference": (payment_reference or "").strip() or None,
        "notes": (notes or "").strip() or None,
    }
    summary = (
        f"Record a {payload['currency']} "
        f"${amount_int / 100.0:,.2f} payment to {payee_name}."
    )
    pa = ProposedAction(
        kind="record_payment", summary=summary, payload=payload,
        org_id=org_id, user_id=user_id,
    )
    store_proposed_action(pa)
    return {"proposed_action": pa.to_public_dict()}


def _write_create_contract_stub(db: Session, org_id: int, user_id: int,
                                title: str,
                                contract_type: str = "OTHER",
                                creator_id: int | None = None,
                                notes: str | None = None) -> dict:
    if not title or not title.strip():
        return {"error": "title is required."}
    if creator_id is not None:
        ok = db.query(Creator.id).filter(
            Creator.id == creator_id, Creator.organization_id == org_id
        ).first()
        if not ok:
            return {"error": "creator_id does not belong to your organization."}
    payload = {
        "title": title.strip(),
        "contract_type": (contract_type or "OTHER").upper(),
        "creator_id": creator_id,
        "notes": (notes or "").strip() or None,
    }
    summary = (
        f"Draft a {payload['contract_type']} contract \"{payload['title']}\" "
        "(status DRAFT — you can fill in parties, dates, and terms after)."
    )
    pa = ProposedAction(
        kind="create_contract_stub", summary=summary, payload=payload,
        org_id=org_id, user_id=user_id,
    )
    store_proposed_action(pa)
    return {"proposed_action": pa.to_public_dict()}


# ----------------------------------------------------------------------
# Confirm-side executors — actually mutate the DB.
# ----------------------------------------------------------------------

def _exec_create_song(pa: ProposedAction, db: Session, user: User) -> dict:
    p = pa.payload
    song = Song(
        organization_id=pa.org_id,
        title=p["title"],
        primary_artist=p.get("primary_artist") or "Unknown",
        isrc=p.get("isrc"),
        iswc=p.get("iswc"),
        notes=p.get("notes"),
        is_released=False,
        release_status="unreleased",
        entry_type="Song",
    )
    db.add(song)
    db.flush()
    return {
        "kind": "create_song",
        "entity_type": "SONG",
        "entity_id": song.id,
        "entity_name": song.title,
        "result": {"id": song.id, "title": song.title},
    }


def _exec_create_placement(pa: ProposedAction, db: Session, user: User) -> dict:
    p = pa.payload
    placement = Placement(
        organization_id=pa.org_id,
        title=p["title"],
        placement_type=p.get("placement_type", "SYNC"),
        status="PITCHED",
        song_id=p.get("song_id"),
        client_name=p.get("client_name"),
        project_name=p.get("project_name"),
        license_fee=p.get("license_fee"),
        license_currency="USD",
        notes=p.get("notes"),
        created_by_user_id=user.id,
    )
    db.add(placement)
    db.flush()
    return {
        "kind": "create_placement",
        "entity_type": "PLACEMENT",
        "entity_id": placement.id,
        "entity_name": placement.title,
        "result": {"id": placement.id, "title": placement.title,
                   "status": placement.status},
    }


def _exec_update_placement_status(pa: ProposedAction, db: Session,
                                  user: User) -> dict:
    p = pa.payload
    placement = db.query(Placement).filter(
        Placement.id == p["placement_id"],
        Placement.organization_id == pa.org_id,
    ).first()
    if not placement:
        raise ValueError("Placement no longer exists.")
    placement.status = p["to_status"]
    placement.updated_at = datetime.utcnow()
    return {
        "kind": "update_placement_status",
        "entity_type": "PLACEMENT",
        "entity_id": placement.id,
        "entity_name": placement.title,
        "result": {
            "id": placement.id,
            "from_status": p["from_status"],
            "to_status": placement.status,
        },
    }


def _exec_create_action_item(pa: ProposedAction, db: Session,
                             user: User) -> dict:
    p = pa.payload
    deadline = None
    if p.get("deadline"):
        try:
            deadline = datetime.fromisoformat(p["deadline"])
        except ValueError:
            deadline = None
    item = ActionItem(
        organization_id=pa.org_id,
        title=p["title"],
        description=p.get("description"),
        priority=int(p.get("priority") or 2),
        status="PENDING",
        action_type="GENERAL",
        creator_id=p.get("creator_id"),
        song_id=p.get("song_id"),
        deadline=deadline,
        created_by_user_id=user.id,
    )
    db.add(item)
    db.flush()
    return {
        "kind": "create_action_item",
        "entity_type": "ACTION_ITEM",
        "entity_id": item.id,
        "entity_name": item.title,
        "result": {"id": item.id, "title": item.title, "priority": item.priority},
    }


def _exec_create_contract_stub(pa: ProposedAction, db: Session,
                               user: User) -> dict:
    p = pa.payload
    contract = Contract(
        organization_id=pa.org_id,
        title=p["title"],
        contract_type=p.get("contract_type", "OTHER"),
        status="DRAFT",
        creator_id=p.get("creator_id"),
        notes=p.get("notes"),
        created_by_user_id=user.id,
    )
    db.add(contract)
    db.flush()
    return {
        "kind": "create_contract_stub",
        "entity_type": "CONTRACT",
        "entity_id": contract.id,
        "entity_name": contract.title,
        "result": {"id": contract.id, "title": contract.title,
                   "status": contract.status},
    }


def _exec_mark_song_released(pa: ProposedAction, db: Session,
                             user: User) -> dict:
    p = pa.payload
    song = db.query(Song).filter(
        Song.id == p["song_id"],
        Song.organization_id == pa.org_id,
    ).first()
    if not song:
        raise ValueError("Song no longer exists.")
    song.is_released = True
    song.release_status = "released"
    if p.get("release_date"):
        try:
            song.release_date = date.fromisoformat(p["release_date"])
        except ValueError:
            pass
    return {
        "kind": "mark_song_released",
        "entity_type": "SONG",
        "entity_id": song.id,
        "entity_name": song.title,
        "result": {
            "id": song.id,
            "is_released": song.is_released,
            "release_status": song.release_status,
            "release_date": song.release_date.isoformat()
                if song.release_date else None,
        },
    }


def _exec_update_song_metadata(pa: ProposedAction, db: Session,
                               user: User) -> dict:
    p = pa.payload
    song = db.query(Song).filter(
        Song.id == p["song_id"],
        Song.organization_id == pa.org_id,
    ).first()
    if not song:
        raise ValueError("Song no longer exists.")
    changes = p.get("changes") or {}
    applied: dict = {}
    for field in ("title", "isrc", "iswc"):
        spec = changes.get(field)
        if not spec:
            continue
        new_val = spec.get("new")
        setattr(song, field, new_val)
        applied[field] = {"old": spec.get("old"), "new": new_val}
    song.updated_at = datetime.utcnow()
    return {
        "kind": "update_song_metadata",
        "entity_type": "SONG",
        "entity_id": song.id,
        "entity_name": song.title,
        "result": {"id": song.id, "changes": applied},
    }


def _exec_assign_action_item(pa: ProposedAction, db: Session,
                             user: User) -> dict:
    p = pa.payload
    item = db.query(ActionItem).filter(
        ActionItem.id == p["action_item_id"],
        ActionItem.organization_id == pa.org_id,
    ).first()
    if not item:
        raise ValueError("Action item no longer exists.")
    new_assignee = p.get("to_assignee_user_id")
    if new_assignee is not None:
        member = db.query(OrganizationMember).filter(
            OrganizationMember.user_id == int(new_assignee),
            OrganizationMember.organization_id == pa.org_id,
        ).first()
        if not member:
            raise ValueError(
                "Assignee is no longer a member of this organization."
            )
    item.assigned_to_user_id = int(new_assignee) if new_assignee is not None else None
    item.updated_at = datetime.utcnow()
    return {
        "kind": "assign_action_item",
        "entity_type": "ACTION_ITEM",
        "entity_id": item.id,
        "entity_name": item.title,
        "result": {
            "id": item.id,
            "from_assignee_user_id": p.get("from_assignee_user_id"),
            "to_assignee_user_id": item.assigned_to_user_id,
        },
    }


def _exec_add_song_credit(pa: ProposedAction, db: Session,
                          user: User) -> dict:
    p = pa.payload
    song = db.query(Song).filter(
        Song.id == p["song_id"],
        Song.organization_id == pa.org_id,
    ).first()
    if not song:
        raise ValueError("Song no longer exists.")
    creator = db.query(Creator).filter(
        Creator.id == p["creator_id"],
        Creator.organization_id == pa.org_id,
    ).first()
    if not creator:
        raise ValueError("Creator no longer exists.")
    credit = SongCredit(
        song_id=song.id,
        creator_id=creator.id,
        role=p["role"],
        pub_share=p.get("pub_share"),
        master_share=p.get("master_share"),
    )
    db.add(credit)
    db.flush()
    return {
        "kind": "add_song_credit",
        "entity_type": "SONG_CREDIT",
        "entity_id": credit.id,
        "entity_name": f"{p.get('creator_name')} on \"{song.title}\"",
        "result": {
            "id": credit.id,
            "song_id": song.id,
            "creator_id": creator.id,
            "role": credit.role,
            "pub_share": credit.pub_share,
            "master_share": credit.master_share,
        },
    }


def _exec_record_payment(pa: ProposedAction, db: Session,
                         user: User) -> dict:
    p = pa.payload
    payment = Payment(
        organization_id=pa.org_id,
        payee_id=p["payee_id"],
        contract_id=p.get("contract_id"),
        amount_cents=int(p["amount_cents"]),
        currency=p.get("currency", "USD"),
        status="PENDING",
        payment_method=p.get("payment_method"),
        payment_reference=p.get("payment_reference"),
        notes=p.get("notes"),
        created_by_user_id=user.id,
    )
    db.add(payment)
    db.flush()
    return {
        "kind": "record_payment",
        "entity_type": "PAYMENT",
        "entity_id": payment.id,
        "entity_name": f"Payment to {p.get('payee_name')}",
        "result": {
            "id": payment.id,
            "amount_cents": payment.amount_cents,
            "currency": payment.currency,
            "status": payment.status,
        },
    }


# ----------------------------------------------------------------------
# Task #196 Phase 3B — additional write tools (covers MLC + the static
# enums for song/release/contract/creator/action-item status changes).
# Each follows the same pattern: a `_write_*` builder that validates and
# stores a ProposedAction, and a `_exec_*` that mutates on confirm.
# ----------------------------------------------------------------------

def _write_mark_song_registered(db: Session, org_id: int, user_id: int,
                                song_id: int,
                                registry: str,
                                status: str = "REGISTERED",
                                registration_id: str | None = None) -> dict:
    song = db.query(Song).filter(
        Song.id == song_id, Song.organization_id == org_id,
    ).first()
    if not song:
        return {"error": "Song not found in your organization."}
    reg = (registry or "").upper()
    if reg not in REGISTRY_TYPES:
        return {"error": f"Invalid registry. Allowed: {sorted(REGISTRY_TYPES)}"}
    st = (status or "REGISTERED").upper()
    if st not in REGISTRATION_STATUSES:
        return {"error": f"Invalid status. Allowed: {sorted(REGISTRATION_STATUSES)}"}

    existing = db.query(SongRegistration).filter(
        SongRegistration.song_id == song.id,
        SongRegistration.registry_type == reg,
        SongRegistration.organization_id == org_id,
    ).first()
    payload = {
        "song_id": song.id,
        "song_title": song.title,
        "registry": reg,
        "to_status": st,
        "registration_id": (registration_id or "").strip() or None,
        "from_status": existing.registration_status if existing else None,
    }
    summary = (
        f"Mark \"{song.title}\" as {st} with {reg}"
        + (f" (id {payload['registration_id']})" if payload["registration_id"] else "")
        + "."
    )
    pa = ProposedAction(
        kind="mark_song_registered", summary=summary, payload=payload,
        org_id=org_id, user_id=user_id,
    )
    store_proposed_action(pa)
    return {"proposed_action": pa.to_public_dict()}


def _exec_mark_song_registered(pa: ProposedAction, db: Session,
                               user: User) -> dict:
    p = pa.payload
    song = db.query(Song).filter(
        Song.id == p["song_id"], Song.organization_id == pa.org_id,
    ).first()
    if not song:
        raise ValueError("Song no longer exists.")
    reg = db.query(SongRegistration).filter(
        SongRegistration.song_id == song.id,
        SongRegistration.registry_type == p["registry"],
        SongRegistration.organization_id == pa.org_id,
    ).first()
    set_today = p["to_status"] == "REGISTERED"
    if reg is None:
        reg = SongRegistration(
            song_id=song.id,
            organization_id=pa.org_id,
            registry_type=p["registry"],
            registration_status=p["to_status"],
            registration_id=p.get("registration_id"),
            registered_date=date.today() if set_today else None,
            registered_by_user_id=user.id if set_today else None,
        )
        db.add(reg)
    else:
        reg.registration_status = p["to_status"]
        if p.get("registration_id"):
            reg.registration_id = p["registration_id"]
        if set_today and not reg.registered_date:
            reg.registered_date = date.today()
            reg.registered_by_user_id = user.id
    db.flush()
    return {
        "kind": "mark_song_registered",
        "entity_type": "SONG_REGISTRATION",
        "entity_id": reg.id,
        "entity_name": f"{p['registry']} on \"{song.title}\"",
        "result": {
            "song_id": song.id,
            "registry": p["registry"],
            "from_status": p.get("from_status"),
            "to_status": reg.registration_status,
            "registration_id": reg.registration_id,
        },
    }


def _write_add_fee_to_song(db: Session, org_id: int, user_id: int,
                           song_id: int,
                           creator_id: int,
                           fee_type: str,
                           amount: float,
                           description: str | None = None) -> dict:
    song = db.query(Song).filter(
        Song.id == song_id, Song.organization_id == org_id,
    ).first()
    if not song:
        return {"error": "Song not found in your organization."}
    creator = db.query(Creator).filter(
        Creator.id == creator_id, Creator.organization_id == org_id,
    ).first()
    if not creator:
        return {"error": "Creator not found in your organization."}
    ftype = (fee_type or "").upper()
    if ftype not in FEE_TYPES:
        return {"error": f"Invalid fee_type. Allowed: {sorted(FEE_TYPES)}"}
    try:
        amount_f = float(amount)
    except (TypeError, ValueError):
        return {"error": "amount must be a number (in dollars)."}
    if amount_f <= 0:
        return {"error": "amount must be positive."}

    creator_name = (
        getattr(creator, "display_name", None)
        or getattr(creator, "name", None)
        or f"Creator #{creator.id}"
    )
    payload = {
        "song_id": song.id,
        "song_title": song.title,
        "creator_id": creator.id,
        "creator_name": creator_name,
        "fee_type": ftype,
        "amount_dollars": amount_f,
        "description": (description or "").strip() or None,
    }
    summary = (
        f"Log a {ftype} fee of ${amount_f:,.2f} against \"{song.title}\" "
        f"to {creator_name}."
    )
    pa = ProposedAction(
        kind="add_fee_to_song", summary=summary, payload=payload,
        org_id=org_id, user_id=user_id,
    )
    store_proposed_action(pa)
    return {"proposed_action": pa.to_public_dict()}


def _exec_add_fee_to_song(pa: ProposedAction, db: Session,
                          user: User) -> dict:
    p = pa.payload
    song = db.query(Song).filter(
        Song.id == p["song_id"], Song.organization_id == pa.org_id,
    ).first()
    if not song:
        raise ValueError("Song no longer exists.")
    creator = db.query(Creator).filter(
        Creator.id == p["creator_id"], Creator.organization_id == pa.org_id,
    ).first()
    if not creator:
        raise ValueError("Creator no longer exists.")
    amount_cents = int(round(float(p["amount_dollars"]) * 100))
    fee = Fee(
        organization_id=pa.org_id,
        creator_id=creator.id,
        song_id=song.id,
        fee_type=p["fee_type"],
        amount_cents=amount_cents,
        description=p.get("description"),
    )
    db.add(fee)
    db.flush()
    return {
        "kind": "add_fee_to_song",
        "entity_type": "FEE",
        "entity_id": fee.id,
        "entity_name": f"{p['fee_type']} on \"{song.title}\"",
        "result": {
            "id": fee.id,
            "song_id": song.id,
            "creator_id": creator.id,
            "fee_type": p["fee_type"],
            "amount_cents": amount_cents,
            "amount_dollars": float(p["amount_dollars"]),
        },
    }


def _write_update_song_status(db: Session, org_id: int, user_id: int,
                              song_id: int,
                              new_status: str) -> dict:
    song = db.query(Song).filter(
        Song.id == song_id, Song.organization_id == org_id,
    ).first()
    if not song:
        return {"error": "Song not found in your organization."}
    incoming = (new_status or "").upper()
    if incoming not in SONG_STATUSES:
        return {"error": f"Invalid status. Allowed: {sorted(SONG_STATUSES)}"}
    db_value = SONG_STATUS_TO_DB[incoming]
    payload = {
        "song_id": song.id,
        "song_title": song.title,
        "from_status": song.release_status,
        "to_status": incoming,
        "to_status_db": db_value,
    }
    summary = (
        f"Set status of \"{song.title}\" "
        f"from {song.release_status} to {incoming}."
    )
    pa = ProposedAction(
        kind="update_song_status", summary=summary, payload=payload,
        org_id=org_id, user_id=user_id,
    )
    store_proposed_action(pa)
    return {"proposed_action": pa.to_public_dict()}


def _exec_update_song_status(pa: ProposedAction, db: Session,
                             user: User) -> dict:
    p = pa.payload
    song = db.query(Song).filter(
        Song.id == p["song_id"], Song.organization_id == pa.org_id,
    ).first()
    if not song:
        raise ValueError("Song no longer exists.")
    song.release_status = p["to_status_db"]
    if p["to_status"] == "RELEASED":
        song.is_released = True
    elif p["to_status"] in ("DRAFT", "ARCHIVED"):
        song.is_released = False
    song.updated_at = datetime.utcnow()
    return {
        "kind": "update_song_status",
        "entity_type": "SONG",
        "entity_id": song.id,
        "entity_name": song.title,
        "result": {
            "id": song.id,
            "from_status": p.get("from_status"),
            "to_status": p["to_status"],
            "release_status": song.release_status,
            "is_released": bool(song.is_released),
        },
    }


def _write_update_creator_pro(db: Session, org_id: int, user_id: int,
                              creator_id: int,
                              new_pro: str) -> dict:
    creator = db.query(Creator).filter(
        Creator.id == creator_id, Creator.organization_id == org_id,
    ).first()
    if not creator:
        return {"error": "Creator not found in your organization."}
    incoming = (new_pro or "").upper().strip()
    if incoming == "OTHER":
        incoming = "PRO_OTHER"
    if incoming not in CREATOR_PROS:
        return {"error": f"Invalid PRO. Allowed: {sorted(CREATOR_PROS)} (OTHER is accepted as PRO_OTHER)."}
    creator_name = (
        getattr(creator, "display_name", None)
        or getattr(creator, "name", None)
        or f"Creator #{creator.id}"
    )
    db_value = None if incoming == "NONE" else incoming
    payload = {
        "creator_id": creator.id,
        "creator_name": creator_name,
        "from_pro": creator.primary_pro,
        "to_pro": incoming,
        "to_pro_db": db_value,
    }
    summary = f"Set {creator_name}'s PRO from {creator.primary_pro or 'none'} to {incoming}."
    pa = ProposedAction(
        kind="update_creator_pro", summary=summary, payload=payload,
        org_id=org_id, user_id=user_id,
    )
    store_proposed_action(pa)
    return {"proposed_action": pa.to_public_dict()}


def _exec_update_creator_pro(pa: ProposedAction, db: Session,
                             user: User) -> dict:
    p = pa.payload
    creator = db.query(Creator).filter(
        Creator.id == p["creator_id"], Creator.organization_id == pa.org_id,
    ).first()
    if not creator:
        raise ValueError("Creator no longer exists.")
    creator.primary_pro = p.get("to_pro_db")
    return {
        "kind": "update_creator_pro",
        "entity_type": "CREATOR",
        "entity_id": creator.id,
        "entity_name": p.get("creator_name") or f"Creator #{creator.id}",
        "result": {
            "id": creator.id,
            "from_pro": p.get("from_pro"),
            "to_pro": p["to_pro"],
        },
    }


def _write_update_release_status(db: Session, org_id: int, user_id: int,
                                 release_id: int,
                                 new_status: str) -> dict:
    release = db.query(Release).filter(
        Release.id == release_id, Release.organization_id == org_id,
    ).first()
    if not release:
        return {"error": "Release not found in your organization."}
    incoming = (new_status or "").upper()
    if incoming not in RELEASE_STATUSES:
        return {"error": f"Invalid status. Allowed: {sorted(RELEASE_STATUSES)}"}
    payload = {
        "release_id": release.id,
        "release_title": release.title,
        "from_status": release.status,
        "to_status": incoming,
    }
    summary = (
        f"Move release \"{release.title}\" from {release.status} to {incoming}."
    )
    pa = ProposedAction(
        kind="update_release_status", summary=summary, payload=payload,
        org_id=org_id, user_id=user_id,
    )
    store_proposed_action(pa)
    return {"proposed_action": pa.to_public_dict()}


def _exec_update_release_status(pa: ProposedAction, db: Session,
                                user: User) -> dict:
    p = pa.payload
    release = db.query(Release).filter(
        Release.id == p["release_id"], Release.organization_id == pa.org_id,
    ).first()
    if not release:
        raise ValueError("Release no longer exists.")
    release.status = p["to_status"]
    return {
        "kind": "update_release_status",
        "entity_type": "RELEASE",
        "entity_id": release.id,
        "entity_name": release.title,
        "result": {
            "id": release.id,
            "from_status": p.get("from_status"),
            "to_status": release.status,
        },
    }


def _write_update_release_type(db: Session, org_id: int, user_id: int,
                               release_id: int,
                               new_type: str) -> dict:
    release = db.query(Release).filter(
        Release.id == release_id, Release.organization_id == org_id,
    ).first()
    if not release:
        return {"error": "Release not found in your organization."}
    incoming = (new_type or "").upper()
    if incoming not in RELEASE_TYPES:
        return {"error": f"Invalid release_type. Allowed: {sorted(RELEASE_TYPES)}"}
    payload = {
        "release_id": release.id,
        "release_title": release.title,
        "from_type": release.release_type,
        "to_type": incoming,
    }
    summary = (
        f"Set release \"{release.title}\" type from "
        f"{release.release_type} to {incoming}."
    )
    pa = ProposedAction(
        kind="update_release_type", summary=summary, payload=payload,
        org_id=org_id, user_id=user_id,
    )
    store_proposed_action(pa)
    return {"proposed_action": pa.to_public_dict()}


def _exec_update_release_type(pa: ProposedAction, db: Session,
                              user: User) -> dict:
    p = pa.payload
    release = db.query(Release).filter(
        Release.id == p["release_id"], Release.organization_id == pa.org_id,
    ).first()
    if not release:
        raise ValueError("Release no longer exists.")
    release.release_type = p["to_type"]
    return {
        "kind": "update_release_type",
        "entity_type": "RELEASE",
        "entity_id": release.id,
        "entity_name": release.title,
        "result": {
            "id": release.id,
            "from_type": p.get("from_type"),
            "to_type": release.release_type,
        },
    }


def _write_update_contract_status(db: Session, org_id: int, user_id: int,
                                  contract_id: int,
                                  new_status: str) -> dict:
    contract = db.query(Contract).filter(
        Contract.id == contract_id, Contract.organization_id == org_id,
    ).first()
    if not contract:
        return {"error": "Contract not found in your organization."}
    incoming = (new_status or "").upper()
    if incoming not in CONTRACT_STATUSES:
        return {"error": f"Invalid status. Allowed: {sorted(CONTRACT_STATUSES)}"}
    payload = {
        "contract_id": contract.id,
        "contract_title": contract.title,
        "from_status": contract.status,
        "to_status": incoming,
    }
    summary = (
        f"Move contract \"{contract.title}\" from "
        f"{contract.status} to {incoming}."
    )
    pa = ProposedAction(
        kind="update_contract_status", summary=summary, payload=payload,
        org_id=org_id, user_id=user_id,
    )
    store_proposed_action(pa)
    return {"proposed_action": pa.to_public_dict()}


def _exec_update_contract_status(pa: ProposedAction, db: Session,
                                 user: User) -> dict:
    p = pa.payload
    contract = db.query(Contract).filter(
        Contract.id == p["contract_id"], Contract.organization_id == pa.org_id,
    ).first()
    if not contract:
        raise ValueError("Contract no longer exists.")
    contract.status = p["to_status"]
    return {
        "kind": "update_contract_status",
        "entity_type": "CONTRACT",
        "entity_id": contract.id,
        "entity_name": contract.title,
        "result": {
            "id": contract.id,
            "from_status": p.get("from_status"),
            "to_status": contract.status,
        },
    }


def _write_update_action_item_status(db: Session, org_id: int, user_id: int,
                                     action_item_id: int,
                                     new_status: str) -> dict:
    item = db.query(ActionItem).filter(
        ActionItem.id == action_item_id,
        ActionItem.organization_id == org_id,
    ).first()
    if not item:
        return {"error": "Action item not found in your organization."}
    raw = (new_status or "").upper()
    canonical = ACTION_ITEM_STATUS_ALIASES.get(raw)
    if canonical is None:
        return {"error": (
            "Invalid status. Allowed: OPEN / IN_PROGRESS / DONE / CANCELLED "
            "(aliases: OPEN→PENDING, DONE→COMPLETED)."
        )}
    payload = {
        "action_item_id": item.id,
        "action_item_title": item.title,
        "from_status": item.status,
        "to_status_label": raw,
        "to_status": canonical,
    }
    summary = (
        f"Move action item \"{item.title}\" from "
        f"{item.status or 'PENDING'} to {raw}."
    )
    pa = ProposedAction(
        kind="update_action_item_status", summary=summary, payload=payload,
        org_id=org_id, user_id=user_id,
    )
    store_proposed_action(pa)
    return {"proposed_action": pa.to_public_dict()}


def _exec_update_action_item_status(pa: ProposedAction, db: Session,
                                    user: User) -> dict:
    p = pa.payload
    item = db.query(ActionItem).filter(
        ActionItem.id == p["action_item_id"],
        ActionItem.organization_id == pa.org_id,
    ).first()
    if not item:
        raise ValueError("Action item no longer exists.")
    item.status = p["to_status"]
    item.updated_at = datetime.utcnow()
    if p["to_status"] == "COMPLETED":
        item.completed_at = datetime.utcnow()
        item.completed_by_user_id = user.id
    return {
        "kind": "update_action_item_status",
        "entity_type": "ACTION_ITEM",
        "entity_id": item.id,
        "entity_name": item.title,
        "result": {
            "id": item.id,
            "from_status": p.get("from_status"),
            "to_status": item.status,
        },
    }


_EXECUTORS: dict[str, Callable[[ProposedAction, Session, User], dict]] = {
    "create_song": _exec_create_song,
    "create_placement": _exec_create_placement,
    "update_placement_status": _exec_update_placement_status,
    "create_action_item": _exec_create_action_item,
    "create_contract_stub": _exec_create_contract_stub,
    "mark_song_released": _exec_mark_song_released,
    "update_song_metadata": _exec_update_song_metadata,
    "assign_action_item": _exec_assign_action_item,
    "add_song_credit": _exec_add_song_credit,
    "record_payment": _exec_record_payment,
    # Phase 3B additions — v2 placement alias reuses the existing executor
    "update_placement_status_v2": _exec_update_placement_status,
    "mark_song_registered": _exec_mark_song_registered,
    "add_fee_to_song": _exec_add_fee_to_song,
    "update_song_status": _exec_update_song_status,
    "update_creator_pro": _exec_update_creator_pro,
    "update_release_status": _exec_update_release_status,
    "update_release_type": _exec_update_release_type,
    "update_contract_status": _exec_update_contract_status,
    "update_action_item_status": _exec_update_action_item_status,
}


def execute_proposed_action(action_id: str, db: Session, user: User) -> dict:
    """Confirm + execute a proposed write tool. Atomically claims the
    proposal (so a double-clicked Confirm can't run twice), then verifies
    org membership before mutating.
    """
    # Atomic claim — also enforces ownership + expiry. The action is
    # removed from the store before the executor runs, so any concurrent
    # caller sees "not found" instead of executing it again.
    pa = _claim_proposed_action(action_id, user.id)

    membership = db.query(OrganizationMember).filter(
        OrganizationMember.user_id == user.id,
        OrganizationMember.organization_id == pa.org_id,
    ).first()
    if not membership and not getattr(user, "is_super_admin", False):
        raise PermissionError("Not authorized to act in that organization.")

    # Phase 4 — rate-limit gate. Read-only check; the counter is bumped
    # only after the executor + commit succeed (failed confirms must not
    # burn quota).
    _check_rate_limit(user.id)

    # Phase 4 — hard reject (do NOT silently strip) any payload that
    # contains a deny-listed field. Aborts before any DB write happens.
    _assert_no_blocked_fields(pa.payload)

    fn = _EXECUTORS.get(pa.kind)
    if fn is None:
        raise ValueError(f"Unknown action kind: {pa.kind}")
    try:
        result = fn(pa, db, user)
        from .audit_service import log_action
        log_action(
            db=db,
            organization_id=pa.org_id,
            user_id=user.id,
            action="ASSISTANT_" + pa.kind.upper(),
            entity_type=result["entity_type"],
            entity_id=result["entity_id"],
            entity_name=result["entity_name"],
            details={"source": "assistant", "summary": pa.summary,
                     "payload": pa.payload},
        )
        db.commit()
    except Exception:
        db.rollback()
        raise
    # Phase 4 — only confirmed, fully-committed writes count toward the
    # per-user 20/hr cap.
    _record_successful_write(user.id)
    return result


# ----------------------------------------------------------------------
# Tool schemas (OpenAI function-calling format)
# ----------------------------------------------------------------------

TOOL_SCHEMAS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "search_songs",
            "description": (
                "Search the user's catalog for songs. Use when the user asks "
                "about specific songs, ISRCs, or wants to look something up."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string",
                              "description": "Title, artist, ISRC, or ISWC. Optional."},
                    "limit": {"type": "integer", "default": 10, "minimum": 1, "maximum": 25},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_song_health",
            "description": "Get a song's metadata health, gaps, and credit count.",
            "parameters": {
                "type": "object",
                "properties": {"song_id": {"type": "integer"}},
                "required": ["song_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_creators",
            "description": "Search creators (artists, songwriters, producers) in this org.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "limit": {"type": "integer", "default": 10, "minimum": 1, "maximum": 25},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_creator_summary",
            "description": "Counts of songs, contracts, and open action items for a creator.",
            "parameters": {
                "type": "object",
                "properties": {"creator_id": {"type": "integer"}},
                "required": ["creator_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_contracts",
            "description": "Search this org's contracts.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "status": {"type": "string",
                               "enum": ["DRAFT", "PENDING", "ACTIVE", "EXPIRED", "TERMINATED"]},
                    "limit": {"type": "integer", "default": 10, "minimum": 1, "maximum": 25},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_expiring_contracts",
            "description": "List contracts whose end_date falls within N days.",
            "parameters": {
                "type": "object",
                "properties": {
                    "days": {"type": "integer", "default": 90, "minimum": 1, "maximum": 365},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_royalty_summary_for_song",
            "description": (
                "Total streams + matched-statement net royalties for a song. "
                "Optionally pass a `period` shortcut (last_30d, last_90d, "
                "last_quarter, ytd, last_year) or explicit `period_start` / "
                "`period_end` ISO dates (YYYY-MM-DD) to scope earnings to a "
                "window. Omit period args for all-time."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "song_id": {"type": "integer"},
                    "period": {
                        "type": "string",
                        "enum": ["last_30d", "last_90d", "last_quarter",
                                 "ytd", "last_year", "all_time"],
                    },
                    "period_start": {
                        "type": "string",
                        "description": "ISO date YYYY-MM-DD (inclusive).",
                    },
                    "period_end": {
                        "type": "string",
                        "description": "ISO date YYYY-MM-DD (inclusive).",
                    },
                },
                "required": ["song_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_action_items_for_user",
            "description": "List open action items assigned to the calling user.",
            "parameters": {
                "type": "object",
                "properties": {
                    "status": {"type": "string", "default": "PENDING",
                               "description": "PENDING, OPEN (anything not COMPLETED), or any status string"},
                    "limit": {"type": "integer", "default": 10, "minimum": 1, "maximum": 25},
                },
            },
        },
    },
    # ---- WRITES (return proposed_action) ----
    {
        "type": "function",
        "function": {
            "name": "create_song",
            "description": (
                "Propose creating a new song. Returns a proposed_action — the user "
                "must confirm before anything is written."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "primary_artist": {"type": "string"},
                    "isrc": {"type": "string"},
                    "iswc": {"type": "string"},
                    "notes": {"type": "string"},
                },
                "required": ["title"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_placement",
            "description": "Propose creating a sync placement. Returns a proposed_action.",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "song_id": {"type": "integer"},
                    "placement_type": {"type": "string",
                                       "enum": ["SYNC", "ADVERTISING", "FILM", "TV",
                                                "GAMING", "TRAILER", "OTHER"],
                                       "default": "SYNC"},
                    "client_name": {"type": "string"},
                    "project_name": {"type": "string"},
                    "license_fee": {"type": "number"},
                    "notes": {"type": "string"},
                },
                "required": ["title"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "update_placement_status",
            "description": "Propose moving a placement to a new pipeline status.",
            "parameters": {
                "type": "object",
                "properties": {
                    "placement_id": {"type": "integer"},
                    "new_status": {"type": "string",
                                   "enum": ["PITCHED", "IN_REVIEW", "IN_NEGOTIATION",
                                            "SECURED", "DELIVERED", "AIRED", "PAID",
                                            "DECLINED", "CANCELLED"]},
                },
                "required": ["placement_id", "new_status"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_action_item",
            "description": "Propose creating an action item / task.",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "description": {"type": "string"},
                    "priority": {"type": "integer", "enum": [1, 2, 3], "default": 2,
                                 "description": "1=high, 2=normal, 3=low"},
                    "creator_id": {"type": "integer"},
                    "song_id": {"type": "integer"},
                    "deadline": {"type": "string",
                                 "description": "ISO-8601 date or datetime"},
                },
                "required": ["title"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "mark_song_released",
            "description": (
                "Propose flipping a song's release status to RELEASED. "
                "Optionally set the release date (defaults to leaving it as-is). "
                "Returns a proposed_action."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "song_id": {"type": "integer"},
                    "release_date": {
                        "type": "string",
                        "description": "ISO date YYYY-MM-DD (optional).",
                    },
                },
                "required": ["song_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "update_song_metadata",
            "description": (
                "Propose updating a song's title, ISRC, or ISWC. Pass only the "
                "fields you want to change — others are left alone. Releases, "
                "credits, and rights are NOT touched by this tool."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "song_id": {"type": "integer"},
                    "title": {"type": "string"},
                    "isrc": {"type": "string"},
                    "iswc": {"type": "string"},
                },
                "required": ["song_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "assign_action_item",
            "description": (
                "Propose assigning an action item to a user in this org, or "
                "unassigning it by passing assignee_user_id=null."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "action_item_id": {"type": "integer"},
                    "assignee_user_id": {
                        "type": ["integer", "null"],
                        "description": "User id of the assignee, or null to unassign.",
                    },
                },
                "required": ["action_item_id", "assignee_user_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "add_song_credit",
            "description": (
                "Propose adding a creator credit (writer / producer / featured / "
                "etc.) to a song with optional publishing % and master % shares."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "song_id": {"type": "integer"},
                    "creator_id": {"type": "integer"},
                    "role": {
                        "type": "string",
                        "description": "e.g. WRITER, PRODUCER, FEATURED, PERFORMER",
                    },
                    "pub_share": {
                        "type": "number",
                        "description": "Publishing share percentage 0–100.",
                    },
                    "master_share": {
                        "type": "number",
                        "description": "Master share percentage 0–100.",
                    },
                },
                "required": ["song_id", "creator_id", "role"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "record_payment",
            "description": (
                "Propose recording a cash disbursement (royalty payment) to a "
                "creator. Amount is in CENTS. Status is created as PENDING."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "payee_id": {"type": "integer",
                                 "description": "Creator id of the payee."},
                    "amount_cents": {"type": "integer", "minimum": 1},
                    "currency": {"type": "string", "default": "USD"},
                    "contract_id": {"type": "integer"},
                    "payment_method": {"type": "string"},
                    "payment_reference": {"type": "string"},
                    "notes": {"type": "string"},
                },
                "required": ["payee_id", "amount_cents"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_contract_stub",
            "description": (
                "Propose creating a DRAFT contract row. Parties, dates, and "
                "terms are filled in afterwards in the Contracts page."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "contract_type": {"type": "string",
                                      "enum": ["MASTER", "PUBLISHING", "SYNC_LICENSE",
                                               "DISTRIBUTION", "MANAGEMENT",
                                               "ADMINISTRATION", "CO_PUBLISHING",
                                               "SUB_PUBLISHING", "OTHER"],
                                      "default": "OTHER"},
                    "creator_id": {"type": "integer"},
                    "notes": {"type": "string"},
                },
                "required": ["title"],
            },
        },
    },
    # ---- Phase 3B writes (Task #196) ----
    {
        "type": "function",
        "function": {
            "name": "update_placement_status_v2",
            "description": (
                "Move a sync placement through the pipeline. Functionally "
                "identical to update_placement_status — kept as an explicit "
                "v2 entry so the assistant always sees the current full "
                "enum (PITCHED / IN_REVIEW / IN_NEGOTIATION / SECURED / "
                "DELIVERED / AIRED / PAID / DECLINED / CANCELLED)."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "placement_id": {"type": "integer"},
                    "new_status": {
                        "type": "string",
                        "enum": ["PITCHED", "IN_REVIEW", "IN_NEGOTIATION",
                                 "SECURED", "DELIVERED", "AIRED", "PAID",
                                 "DECLINED", "CANCELLED"],
                    },
                },
                "required": ["placement_id", "new_status"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "mark_song_registered",
            "description": (
                "Propose marking a song as registered (or any other "
                "registration status) with one of the seven supported "
                "registries: BMI, ASCAP, SESAC, GMR, MLC, SoundExchange, "
                "or HFA. Upserts the per-registry SongRegistration row."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "song_id": {"type": "integer"},
                    "registry": {
                        "type": "string",
                        "enum": ["BMI", "ASCAP", "SESAC", "GMR",
                                 "MLC", "SOUNDEXCHANGE", "HFA"],
                    },
                    "status": {
                        "type": "string",
                        "enum": ["NOT_STARTED", "PENDING", "REGISTERED",
                                 "REJECTED", "NOT_APPLICABLE"],
                        "default": "REGISTERED",
                    },
                    "registration_id": {
                        "type": "string",
                        "description": "Optional society-side id (BMI work id, MLC work id, etc.)",
                    },
                },
                "required": ["song_id", "registry"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "add_fee_to_song",
            "description": (
                "Propose logging a fee against a song, owed to / from a "
                "specific creator. `amount` is in DOLLARS. `fee_type` is "
                "one of MANAGEMENT_FEE / ADMIN_FEE / DISTRIBUTION_FEE / "
                "SYNC_FEE / LEGAL_FEE / OTHER."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "song_id": {"type": "integer"},
                    "creator_id": {"type": "integer"},
                    "fee_type": {
                        "type": "string",
                        "enum": ["MANAGEMENT_FEE", "ADMIN_FEE",
                                 "DISTRIBUTION_FEE", "SYNC_FEE",
                                 "LEGAL_FEE", "OTHER"],
                    },
                    "amount": {"type": "number", "minimum": 0.01,
                               "description": "Fee amount in dollars."},
                    "description": {"type": "string"},
                },
                "required": ["song_id", "creator_id", "fee_type", "amount"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "update_song_status",
            "description": (
                "Propose changing a song's lifecycle status. DRAFT = "
                "unreleased, RELEASED = live, ARCHIVED = retired. The "
                "song's `is_released` flag is kept in sync automatically."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "song_id": {"type": "integer"},
                    "new_status": {"type": "string",
                                   "enum": ["DRAFT", "RELEASED", "ARCHIVED"]},
                },
                "required": ["song_id", "new_status"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "update_creator_pro",
            "description": (
                "Propose changing a creator's PRO affiliation. Allowed: "
                "BMI / ASCAP / SESAC / GMR / SOCAN / PRS / PRO_OTHER / "
                "NONE. The literal `OTHER` is accepted as an alias of "
                "PRO_OTHER. Note: a US writer can only be affiliated with "
                "one PRO at a time."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "creator_id": {"type": "integer"},
                    "new_pro": {"type": "string",
                                "enum": ["BMI", "ASCAP", "SESAC", "GMR",
                                         "SOCAN", "PRS", "PRO_OTHER",
                                         "OTHER", "NONE"]},
                },
                "required": ["creator_id", "new_pro"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "update_release_status",
            "description": (
                "Propose moving a release between DRAFT / READY / "
                "SUBMITTED / RELEASED."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "release_id": {"type": "integer"},
                    "new_status": {"type": "string",
                                   "enum": ["DRAFT", "READY",
                                            "SUBMITTED", "RELEASED"]},
                },
                "required": ["release_id", "new_status"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "update_release_type",
            "description": (
                "Propose changing a release's product type "
                "(SINGLE / EP / ALBUM / COMPILATION / MIXTAPE / OTHER)."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "release_id": {"type": "integer"},
                    "new_type": {"type": "string",
                                 "enum": ["SINGLE", "EP", "ALBUM",
                                          "COMPILATION", "MIXTAPE", "OTHER"]},
                },
                "required": ["release_id", "new_type"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "update_contract_status",
            "description": (
                "Propose moving a contract through its lifecycle "
                "(DRAFT / PENDING / ACTIVE / EXPIRED / TERMINATED)."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "contract_id": {"type": "integer"},
                    "new_status": {"type": "string",
                                   "enum": ["DRAFT", "PENDING", "ACTIVE",
                                            "EXPIRED", "TERMINATED"]},
                },
                "required": ["contract_id", "new_status"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "update_action_item_status",
            "description": (
                "Propose changing an action item's status. Accepts the "
                "user-friendly OPEN / IN_PROGRESS / DONE / CANCELLED "
                "labels — OPEN maps to PENDING, DONE maps to COMPLETED."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "action_item_id": {"type": "integer"},
                    "new_status": {"type": "string",
                                   "enum": ["OPEN", "PENDING", "IN_PROGRESS",
                                            "DONE", "COMPLETED", "CANCELLED"]},
                },
                "required": ["action_item_id", "new_status"],
            },
        },
    },
]


_HANDLERS: dict[str, Callable[..., dict]] = {
    # reads
    "search_songs": _read_search_songs,
    "get_song_health": _read_get_song_health,
    "search_creators": _read_search_creators,
    "get_creator_summary": _read_get_creator_summary,
    "search_contracts": _read_search_contracts,
    "list_expiring_contracts": _read_list_expiring_contracts,
    "get_royalty_summary_for_song": _read_get_royalty_summary_for_song,
    "list_action_items_for_user": _read_list_action_items_for_user,
    # writes (return proposed_action)
    "create_song": _write_create_song,
    "create_placement": _write_create_placement,
    "update_placement_status": _write_update_placement_status,
    "create_action_item": _write_create_action_item,
    "create_contract_stub": _write_create_contract_stub,
    "mark_song_released": _write_mark_song_released,
    "update_song_metadata": _write_update_song_metadata,
    "assign_action_item": _write_assign_action_item,
    "add_song_credit": _write_add_song_credit,
    "record_payment": _write_record_payment,
    # Phase 3B additions
    "update_placement_status_v2": _write_update_placement_status,
    "mark_song_registered": _write_mark_song_registered,
    "add_fee_to_song": _write_add_fee_to_song,
    "update_song_status": _write_update_song_status,
    "update_creator_pro": _write_update_creator_pro,
    "update_release_status": _write_update_release_status,
    "update_release_type": _write_update_release_type,
    "update_contract_status": _write_update_contract_status,
    "update_action_item_status": _write_update_action_item_status,
}

WRITE_TOOL_NAMES = {
    "create_song", "create_placement", "update_placement_status",
    "create_action_item", "create_contract_stub",
    "mark_song_released", "update_song_metadata", "assign_action_item",
    "add_song_credit", "record_payment",
    # Phase 3B additions
    "update_placement_status_v2",
    "mark_song_registered", "add_fee_to_song",
    "update_song_status", "update_creator_pro",
    "update_release_status", "update_release_type",
    "update_contract_status", "update_action_item_status",
}

# Write tools that are still safe for CLIENT users — they're proposing
# self-tasks, not mutating other people's catalog data.
CLIENT_ALLOWED_WRITE_TOOLS = {"create_action_item"}


def _client_song_ids(db: Session, org_id: int,
                     linked_creator_id: int) -> set[int]:
    """Songs in this org that are credited to the client's linked creator."""
    rows = db.query(SongCredit.song_id).join(
        Song, Song.id == SongCredit.song_id
    ).filter(
        Song.organization_id == org_id,
        SongCredit.creator_id == linked_creator_id,
    ).distinct().all()
    return {sid for (sid,) in rows}


def _client_contract_ids(db: Session, org_id: int,
                         linked_creator_id: int) -> set[int]:
    """Contracts where the client's creator is a party or owns the contract."""
    direct = db.query(Contract.id).filter(
        Contract.organization_id == org_id,
        Contract.creator_id == linked_creator_id,
    ).all()
    party = db.query(ContractParty.contract_id).join(
        Contract, Contract.id == ContractParty.contract_id
    ).filter(
        Contract.organization_id == org_id,
        ContractParty.creator_id == linked_creator_id,
    ).all()
    return {cid for (cid,) in (direct + party)}


def _check_client_id_scope(name: str, args: dict, *, db: Session,
                           org_id: int, linked_creator_id: int | None) -> str | None:
    """For CLIENT users, validate that any explicit entity-id args refer
    to a resource the client is allowed to see/touch. Returns an error
    string when the request must be refused, or None when it's OK.
    """
    if not linked_creator_id:
        return ("This account is set up as a Client but isn't linked to a "
                "creator yet, so I can't pull data for you. Ask your admin "
                "to link your creator profile.")

    if name == "get_creator_summary":
        cid = args.get("creator_id")
        if cid and int(cid) != int(linked_creator_id):
            return "As a Client you can only view your own creator profile."

    if name in {"get_song_health", "get_royalty_summary_for_song"}:
        sid = args.get("song_id")
        if sid:
            allowed = _client_song_ids(db, org_id, linked_creator_id)
            if int(sid) not in allowed:
                return "That song isn't part of your catalog."

    if name == "create_action_item":
        cid = args.get("creator_id")
        if cid and int(cid) != int(linked_creator_id):
            return "Action items you create can only be tied to your own creator profile."
        sid = args.get("song_id")
        if sid:
            allowed = _client_song_ids(db, org_id, linked_creator_id)
            if int(sid) not in allowed:
                return "That song isn't part of your catalog."
    return None


def _client_filter_action_items(db: Session, rows: list[dict], *,
                                org_id: int,
                                linked_creator_id: int,
                                user_id: int) -> list[dict]:
    """Keep only items that are (a) explicitly assigned to the client user,
    (b) tied to the client's own creator profile, or (c) tied to a song in
    the client's catalog. Drops org-wide unassigned tasks that would leak
    other creators' work to a CLIENT account.
    """
    if not rows:
        return rows
    allowed_songs = _client_song_ids(db, org_id, linked_creator_id)
    filtered: list[dict] = []
    for r in rows:
        item_id = r.get("id")
        if item_id is None:
            continue
        item = db.query(ActionItem).filter(
            ActionItem.id == item_id,
            ActionItem.organization_id == org_id,
        ).first()
        if not item:
            continue
        is_self = item.assigned_to_user_id == user_id
        is_own_creator = item.creator_id == linked_creator_id
        is_own_song = item.song_id is not None and item.song_id in allowed_songs
        if is_self or is_own_creator or is_own_song:
            filtered.append(r)
    return filtered


def _client_post_filter(name: str, result: dict, *, db: Session,
                        org_id: int, linked_creator_id: int) -> dict:
    """Trim list-style read results to entities the CLIENT may see."""
    if not isinstance(result, dict) or "results" not in result:
        return result
    rows = result.get("results") or []
    if not rows:
        return result

    if name == "search_songs":
        allowed = _client_song_ids(db, org_id, linked_creator_id)
        rows = [r for r in rows if r.get("id") in allowed]
    elif name == "search_creators":
        rows = [r for r in rows if r.get("id") == linked_creator_id]
    elif name in {"search_contracts", "list_expiring_contracts"}:
        allowed = _client_contract_ids(db, org_id, linked_creator_id)
        rows = [r for r in rows if r.get("id") in allowed]
    # action items / royalty summary already user/song-scoped

    result = dict(result)
    result["results"] = rows
    result["count"] = len(rows)
    return result


def dispatch_tool(name: str, args: dict, *,
                  db: Session, org_id: int | None,
                  user_id: int,
                  user_role: str = "MEMBER",
                  linked_creator_id: int | None = None) -> dict:
    """Run a tool by name. Always returns a JSON-serialisable dict.

    Errors are returned as ``{"error": "..."}`` so the LLM sees them
    in the tool message and can react (rather than 500-ing the route).

    ``user_role`` and ``linked_creator_id`` are used to gate CLIENT
    accounts: writes are blocked (other than self-task creation) and
    reads are clamped to the client's own catalog / contracts.
    """
    if not org_id:
        return {"error": "You don't have an organization yet — assistant tools "
                         "need an org context to be safe."}
    fn = _HANDLERS.get(name)
    if fn is None:
        return {"error": f"Unknown tool: {name}"}
    args = args or {}

    role = (user_role or "MEMBER").upper()
    if role == "CLIENT":
        if name in WRITE_TOOL_NAMES and name not in CLIENT_ALLOWED_WRITE_TOOLS:
            return {"error": (
                "As a Client account you can't create or modify catalog data "
                "through chat. Ask your label / administrator to make this "
                "change for you."
            )}
        scope_err = _check_client_id_scope(
            name, args,
            db=db, org_id=org_id, linked_creator_id=linked_creator_id,
        )
        if scope_err:
            return {"error": scope_err}

    try:
        result = fn(db=db, org_id=org_id, user_id=user_id, **args)
    except TypeError as e:
        return {"error": f"Invalid arguments for {name}: {e}"}
    except Exception as e:  # pragma: no cover — last-resort guard
        logger.exception("assistant tool %s crashed", name)
        return {"error": f"{name} failed: {e}"}

    if role == "CLIENT" and linked_creator_id:
        result = _client_post_filter(
            name, result,
            db=db, org_id=org_id, linked_creator_id=linked_creator_id,
        )
        if name == "list_action_items_for_user" and isinstance(result, dict):
            rows = result.get("results") or []
            rows = _client_filter_action_items(
                db, rows,
                org_id=org_id,
                linked_creator_id=linked_creator_id,
                user_id=user_id,
            )
            result = dict(result)
            result["results"] = rows
            result["count"] = len(rows)
    return result
