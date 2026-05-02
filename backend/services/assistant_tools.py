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
"""

from __future__ import annotations

import logging
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
)

logger = logging.getLogger("cadence")

PROPOSED_ACTION_TTL_SECONDS = 600  # 10 minutes
PLACEMENT_STATUSES = {
    "PITCHED", "IN_REVIEW", "IN_NEGOTIATION", "SECURED",
    "DELIVERED", "AIRED", "PAID", "DECLINED", "CANCELLED",
}


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

def _read_search_songs(db: Session, org_id: int, user_id: int,
                       query: str | None = None, limit: int = 10) -> dict:
    limit = max(1, min(int(limit or 10), 25))
    q = db.query(Song).filter(Song.organization_id == org_id)
    if query:
        like = f"%{query.strip()}%"
        q = q.filter(or_(
            Song.title.ilike(like),
            Song.primary_artist.ilike(like),
            Song.isrc.ilike(like),
            Song.iswc.ilike(like),
        ))
    rows = q.order_by(desc(Song.updated_at)).limit(limit).all()
    return {"count": len(rows), "results": [_song_brief(s) for s in rows]}


def _read_get_song_health(db: Session, org_id: int, user_id: int,
                          song_id: int) -> dict:
    song = db.query(Song).filter(
        Song.id == song_id, Song.organization_id == org_id
    ).first()
    if not song:
        return {"error": "Song not found in your organization."}

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


def _read_get_royalty_summary_for_song(db: Session, org_id: int, user_id: int,
                                       song_id: int) -> dict:
    song = db.query(Song).filter(
        Song.id == song_id, Song.organization_id == org_id
    ).first()
    if not song:
        return {"error": "Song not found in your organization."}

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
            RoyaltyStatementLine.song_id == song.id,
        )
    )
    net_amount, line_count = line_q.first() or (0.0, 0)

    return {
        "song_id": song.id,
        "song_title": song.title,
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


_EXECUTORS: dict[str, Callable[[ProposedAction, Session, User], dict]] = {
    "create_song": _exec_create_song,
    "create_placement": _exec_create_placement,
    "update_placement_status": _exec_update_placement_status,
    "create_action_item": _exec_create_action_item,
    "create_contract_stub": _exec_create_contract_stub,
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
            "description": "Total streams + matched-statement net royalties for a song.",
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
}

WRITE_TOOL_NAMES = {
    "create_song", "create_placement", "update_placement_status",
    "create_action_item", "create_contract_stub",
}


def dispatch_tool(name: str, args: dict, *,
                  db: Session, org_id: int | None,
                  user_id: int) -> dict:
    """Run a tool by name. Always returns a JSON-serialisable dict.

    Errors are returned as ``{"error": "..."}`` so the LLM sees them
    in the tool message and can react (rather than 500-ing the route).
    """
    if not org_id:
        return {"error": "You don't have an organization yet — assistant tools "
                         "need an org context to be safe."}
    fn = _HANDLERS.get(name)
    if fn is None:
        return {"error": f"Unknown tool: {name}"}
    args = args or {}
    try:
        return fn(db=db, org_id=org_id, user_id=user_id, **args)
    except TypeError as e:
        return {"error": f"Invalid arguments for {name}: {e}"}
    except Exception as e:  # pragma: no cover — last-resort guard
        logger.exception("assistant tool %s crashed", name)
        return {"error": f"{name} failed: {e}"}
