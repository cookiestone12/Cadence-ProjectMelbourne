"""Internal staff portal — read-only operational endpoints.

Backs the React app at `/internal`. Distinct from the org-scoped
TenantAdmin (/admin) and the master-admin AdminDashboard
(/super-admin). Every endpoint here requires
`is_cadence_staff=True` OR `is_super_admin=True` via
`get_current_staff_or_admin`.

All database access goes through SQLAlchemy + the request-scoped
`get_db` Session — no raw psycopg2, no engine.execute side
channel. The /database browser is strictly read-only and writes
an `INTERNAL_DB_VIEW` row to AuditLog on every load.
"""
from __future__ import annotations

import csv
import io
import logging
from datetime import datetime, timedelta
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import inspect, func, desc, text
from sqlalchemy.orm import Session

from ..models import get_db, User, Organization, OrganizationMember, UserSession
from ..models.models import AuditLog, Song, Creator
from ..utils.auth import (
    get_current_staff_from_cookie as get_current_staff_or_admin,
    decode_access_token,
    verify_password,
    create_access_token,
    get_password_hash,
    hash_token,
    ACCESS_TOKEN_EXPIRE_MINUTES,
)
import os
from ..utils.logging_config import tail_logs

logger = logging.getLogger("cadence")

router = APIRouter(prefix="/api/internal/portal", tags=["Internal Staff"])


# --- helpers ----------------------------------------------------------

# Tables we will never expose, even read-only, through the DB browser
# because they store credential material or one-time secrets.
# Only the migration table is hidden — staff need read access to the
# full operational schema, including users and user_sessions, per the
# task spec. Sensitive columns inside those tables (hashed_password,
# token_hash) remain visible because the browser is intentionally
# read-only and access is gated by the staff role + session check.
_BLOCKED_TABLES = {
    "alembic_version",
}


def _all_table_names(db: Session) -> list[str]:
    insp = inspect(db.get_bind())
    return sorted(
        t for t in insp.get_table_names()
        if not t.startswith("_") and t not in _BLOCKED_TABLES
    )


def _resolve_audit_org_id(db: Session, user: User) -> Optional[int]:
    """Internal portal actions span all orgs, but AuditLog.organization_id
    is a non-null FK. Pick the actor's first organization membership; fall
    back to the lowest-id real organization in the table. Returns None
    only when no organizations exist (fresh install), in which case the
    audit row is skipped instead of failing the request."""
    membership = (
        db.query(OrganizationMember.organization_id)
        .filter(OrganizationMember.user_id == user.id)
        .order_by(OrganizationMember.organization_id.asc())
        .first()
    )
    if membership and membership[0]:
        return int(membership[0])
    fallback = (
        db.query(Organization.id).order_by(Organization.id.asc()).first()
    )
    return int(fallback[0]) if fallback else None


def _audit(
    db: Session,
    user: User,
    action: str,
    entity_type: str,
    entity_id: Optional[int] = None,
    entity_name: Optional[str] = None,
    details: Optional[dict] = None,
    *,
    required: bool = False,
) -> None:
    """Write an AuditLog row for an internal-portal action. INTERNAL_*
    actions never belong to one specific tenant, so we stamp them against
    the actor's primary org (or the lowest org id) to satisfy the FK.
    When `required=True` (DB views/exports), insert failures bubble up
    as a 500 instead of being swallowed."""
    org_id = _resolve_audit_org_id(db, user)
    if org_id is None:
        if required:
            raise HTTPException(
                status_code=500,
                detail="Audit log unavailable: no organizations exist",
            )
        return
    try:
        db.add(AuditLog(
            organization_id=org_id,
            user_id=user.id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            entity_name=entity_name,
            details=details or {},
        ))
        db.commit()
    except Exception:
        db.rollback()
        if required:
            logger.exception("required audit insert failed action=%s", action)
            raise HTTPException(status_code=500, detail="Failed to record audit log")
        logger.warning("audit insert failed", exc_info=True)


# --- dashboard --------------------------------------------------------

class DashboardStats(BaseModel):
    org_count: int
    user_count: int
    song_count: int
    statements_30d: int
    db_status: str
    health_status: str
    scheduler_jobs: list[dict]
    recent_audit: list[dict]


@router.get(
    "/dashboard",
    response_model=DashboardStats,
    summary="Internal portal dashboard",
    description="Aggregated platform health: org/user/song counts, last 30 days of "
                "statement ingests, DB and /health probe, last APScheduler runs and the "
                "50 most recent audit-log entries across all orgs.",
)
def dashboard(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_staff_or_admin),
):
    org_count = db.query(func.count(Organization.id)).scalar() or 0
    user_count = db.query(func.count(User.id)).scalar() or 0
    song_count = db.query(func.count(Song.id)).scalar() or 0

    # 30-day statements — best-effort, table may be empty in dev.
    statements_30d = 0
    try:
        from ..models.models import RoyaltyStatement
        cutoff = datetime.utcnow() - timedelta(days=30)
        statements_30d = (
            db.query(func.count(RoyaltyStatement.id))
            .filter(RoyaltyStatement.created_at >= cutoff)
            .scalar() or 0
        )
    except Exception:
        statements_30d = 0

    # DB probe.
    try:
        db.execute(text("SELECT 1")).scalar()
        db_status = "ok"
    except Exception:
        db_status = "down"

    # Scheduler introspection — never crash the dashboard if the
    # scheduler module isn't importable in this process.
    scheduler_jobs: list[dict] = []
    try:
        from ..services.email_scheduler import scheduler  # type: ignore
        # last-run timestamps are not stored on the Job object itself by
        # APScheduler; we keep our own per-job timestamp dict in the
        # scheduler module (see services/email_scheduler.py).
        last_runs = getattr(scheduler, "_last_runs", None) or {} if scheduler else {}
        if scheduler is not None and getattr(scheduler, "running", False):
            for job in scheduler.get_jobs():
                next_run = job.next_run_time.isoformat() \
                    if getattr(job, "next_run_time", None) else None
                last_run = last_runs.get(job.id)
                scheduler_jobs.append({
                    "id": job.id,
                    "name": getattr(job, "name", job.id),
                    "next_run_time": next_run,
                    "last_run_time": (
                        last_run.isoformat() if hasattr(last_run, "isoformat") else last_run
                    ),
                })
    except Exception:
        scheduler_jobs = []

    recent = (
        db.query(AuditLog)
        .order_by(desc(AuditLog.created_at))
        .limit(50)
        .all()
    )
    recent_audit = [
        {
            "id": r.id,
            "organization_id": r.organization_id,
            "user_id": r.user_id,
            "user_name": r.user.username if r.user else None,
            "action": r.action,
            "entity_type": r.entity_type,
            "entity_id": r.entity_id,
            "entity_name": r.entity_name,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in recent
    ]

    return DashboardStats(
        org_count=org_count,
        user_count=user_count,
        song_count=song_count,
        statements_30d=statements_30d,
        db_status=db_status,
        health_status="ok" if db_status == "ok" else "degraded",
        scheduler_jobs=scheduler_jobs,
        recent_audit=recent_audit,
    )


# --- organizations ----------------------------------------------------

@router.get(
    "/organizations",
    summary="List all organizations",
    description="Cross-org list with member / song / creator counts. Staff and master "
                "admin only. Read-only.",
)
def list_organizations(
    q: Optional[str] = Query(default=None, description="Case-insensitive name match"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_staff_or_admin),
):
    query = db.query(Organization)
    if q:
        like = f"%{q.lower()}%"
        query = query.filter(func.lower(Organization.name).like(like))
    orgs = query.order_by(Organization.id.desc()).all()
    rows: list[dict] = []
    for o in orgs:
        member_count = db.query(func.count(OrganizationMember.id)).filter(
            OrganizationMember.organization_id == o.id
        ).scalar() or 0
        song_count = db.query(func.count(Song.id)).filter(
            Song.organization_id == o.id
        ).scalar() or 0
        creator_count = db.query(func.count(Creator.id)).filter(
            Creator.organization_id == o.id
        ).scalar() or 0
        rows.append({
            "id": o.id,
            "name": o.name,
            "type": (o.type or "").upper(),
            "account_type": getattr(o, "account_type", None),
            "display_name": getattr(o, "display_name", None),
            "created_at": o.created_at.isoformat() if o.created_at else None,
            "member_count": member_count,
            "song_count": song_count,
            "creator_count": creator_count,
        })
    return {"total": len(rows), "rows": rows}


@router.get(
    "/organizations/{org_id}",
    summary="Get organization detail",
    description='Returns members, recent audit log, and aggregate counts for a single org. Read-only support view.\n\n**Path parameter:** `org_id`.\n**Auth:** Bearer JWT — Cadence staff or master admin.\n**Response:** `{ org: {id, name, plan, created_at}, members: [...], recent_audit: [...], counts: {users, creators, songs, releases, contracts} }`.',
)
def organization_detail(
    org_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_staff_or_admin),
):
    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    members = (
        db.query(OrganizationMember, User)
        .join(User, OrganizationMember.user_id == User.id)
        .filter(OrganizationMember.organization_id == org_id)
        .all()
    )
    recent = (
        db.query(AuditLog)
        .filter(AuditLog.organization_id == org_id)
        .order_by(desc(AuditLog.created_at))
        .limit(25)
        .all()
    )
    return {
        "id": org.id,
        "name": org.name,
        "type": (org.type or "").upper(),
        "account_type": getattr(org, "account_type", None),
        "display_name": getattr(org, "display_name", None),
        "created_at": org.created_at.isoformat() if org.created_at else None,
        "members": [
            {
                "user_id": u.id,
                "username": u.username,
                "email": u.email,
                "role": m.role,
                "last_login_at": u.last_login_at.isoformat()
                    if getattr(u, "last_login_at", None) else None,
            }
            for m, u in members
        ],
        "song_count": db.query(func.count(Song.id)).filter(
            Song.organization_id == org_id
        ).scalar() or 0,
        "creator_count": db.query(func.count(Creator.id)).filter(
            Creator.organization_id == org_id
        ).scalar() or 0,
        "recent_audit": [
            {
                "id": r.id,
                "action": r.action,
                "entity_type": r.entity_type,
                "entity_name": r.entity_name,
                "user_name": r.user.username if r.user else None,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in recent
        ],
    }


# --- users ------------------------------------------------------------

@router.get(
    "/users",
    summary="List all users",
    description="Cross-org user directory with role flags, last login and org "
                "memberships. Filter by username or email substring with `q`.",
)
def list_users(
    q: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_staff_or_admin),
):
    query = db.query(User)
    if q:
        like = f"%{q.lower()}%"
        query = query.filter(
            (func.lower(User.username).like(like))
            | (func.lower(User.email).like(like))
        )
    users = query.order_by(User.id.desc()).limit(500).all()
    return {
        "total": len(users),
        "rows": [
            {
                "id": u.id,
                "username": u.username,
                "email": u.email,
                "is_admin": u.is_admin,
                "is_super_admin": getattr(u, "is_super_admin", False),
                "is_cadence_staff": getattr(u, "is_cadence_staff", False),
                "is_active": getattr(u, "is_active", True),
                "last_login_at": u.last_login_at.isoformat()
                    if getattr(u, "last_login_at", None) else None,
                "created_at": u.created_at.isoformat() if u.created_at else None,
                "organizations": [
                    {
                        "id": m.organization_id,
                        "role": m.role,
                        "name": m.organization.name if m.organization else None,
                    }
                    for m in u.organization_memberships
                ],
            }
            for u in users
        ],
    }


@router.get(
    "/users/{user_id}/sessions",
    summary="Active sessions for a user",
    description='Returns non-revoked, unexpired UserSession rows for a single user — used by support to see active devices before revoking them.\n\n**Path parameter:** `user_id`.\n**Auth:** Bearer JWT — Cadence staff or master admin.\n**Response:** `{ sessions: [{id, created_at, last_seen_at, expires_at, user_agent, ip_address}] }`.',
)
def user_sessions(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_staff_or_admin),
):
    now = datetime.utcnow()
    q = (
        db.query(UserSession)
        .filter(UserSession.user_id == user_id)
        .filter(UserSession.revoked_at.is_(None))
        .filter(UserSession.expires_at > now)
        .order_by(desc(UserSession.created_at))
    )
    rows = q.limit(50).all()
    return {
        "total": len(rows),
        "rows": [
            {
                "id": s.id,
                "ip_address": s.ip_address,
                "user_agent": s.user_agent,
                "created_at": s.created_at.isoformat() if s.created_at else None,
                "expires_at": s.expires_at.isoformat() if s.expires_at else None,
            }
            for s in rows
        ],
    }


# --- database browser -------------------------------------------------

@router.get(
    "/database/tables",
    summary="List database tables",
    description="Sorted list of every table the staff DB browser is permitted to view. "
                "Only the alembic_version table is excluded; the staff portal exposes "
                "the full operational schema (users, user_sessions, etc.) read-only "
                "and gated by staff/master role + non-revoked UserSession.",
)
def database_tables(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_staff_or_admin),
):
    return {"tables": _all_table_names(db)}


def _read_table_page(
    db: Session, table: str, limit: int, offset: int,
) -> tuple[list[str], list[list[Any]], int]:
    insp = inspect(db.get_bind())
    if table not in _all_table_names(db):
        raise HTTPException(status_code=404, detail="Table not viewable")
    cols = [c["name"] for c in insp.get_columns(table)]
    # Column / table names come from SQLAlchemy reflection (not user
    # input) so it's safe to interpolate them into the SQL string.
    quoted_cols = ", ".join(f'"{c}"' for c in cols)
    total = db.execute(
        text(f'SELECT COUNT(*) FROM "{table}"')
    ).scalar() or 0
    result = db.execute(text(
        f'SELECT {quoted_cols} FROM "{table}" '
        f'ORDER BY 1 DESC LIMIT :lim OFFSET :off'
    ), {"lim": limit, "off": offset})
    rows = [list(r) for r in result.fetchall()]
    return cols, rows, int(total)


@router.get(
    "/database/{table}",
    summary="Read a table page",
    description="Read-only paginated view of a single table. Default 50 rows, max 200. "
                "Every load writes an INTERNAL_DB_VIEW audit entry.",
)
def database_table_page(
    table: str,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_staff_or_admin),
):
    cols, rows, total = _read_table_page(db, table, limit, offset)
    _audit(
        db, current_user,
        action="INTERNAL_DB_VIEW",
        entity_type="table",
        entity_name=table,
        details={"limit": limit, "offset": offset, "row_count": len(rows)},
        required=True,
    )
    return {
        "table": table,
        "columns": cols,
        "rows": [[_jsonify(v) for v in r] for r in rows],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


def _jsonify(v: Any) -> Any:
    if isinstance(v, datetime):
        return v.isoformat()
    if isinstance(v, (bytes, bytearray)):
        return f"<{len(v)} bytes>"
    return v


@router.get(
    "/database/{table}/export.csv",
    summary="Export table as CSV",
    description="Streams up to 10,000 rows of a table as CSV for offline review. "
                "Audited as INTERNAL_DB_EXPORT.",
)
def database_table_export(
    table: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_staff_or_admin),
):
    cols, rows, _ = _read_table_page(db, table, limit=10_000, offset=0)
    _audit(
        db, current_user,
        action="INTERNAL_DB_EXPORT",
        entity_type="table",
        entity_name=table,
        details={"row_count": len(rows)},
        required=True,
    )

    def stream():
        buf = io.StringIO()
        w = csv.writer(buf)
        w.writerow(cols)
        yield buf.getvalue()
        buf.seek(0); buf.truncate(0)
        for r in rows:
            w.writerow([_jsonify(v) for v in r])
            yield buf.getvalue()
            buf.seek(0); buf.truncate(0)

    return StreamingResponse(
        stream(),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{table}.csv"'},
    )


# --- logs -------------------------------------------------------------

@router.get(
    "/logs",
    summary="Tail in-process log ring buffer",
    description="Returns the most recent log entries from the in-process ring buffer. "
                "Filter by minimum `level` (DEBUG/INFO/WARNING/ERROR/CRITICAL) and "
                "ISO-8601 `since` timestamp. `limit` capped at 1000.",
)
def logs(
    level: Optional[str] = Query(default=None),
    since: Optional[str] = Query(default=None),
    limit: int = Query(default=200, ge=1, le=1000),
    current_user: User = Depends(get_current_staff_or_admin),
):
    parsed_since: Optional[datetime] = None
    if since:
        try:
            parsed_since = datetime.fromisoformat(since)
        except ValueError:
            raise HTTPException(status_code=400, detail="since must be ISO-8601")
    return {"entries": tail_logs(level=level, since=parsed_since, limit=limit)}


# --- cookie login -----------------------------------------------------

class CookieLoginRequest(BaseModel):
    # /api/auth/login -> /cookie-login handoff: pass the JWT in
    # access_token. Direct username+password login is still accepted
    # so curl-based smoke tests don't need two round-trips.
    username: Optional[str] = None
    password: Optional[str] = None
    access_token: Optional[str] = None


@router.post(
    "/cookie-login",
    summary="Internal portal cookie login",
    description="Issues the same JWT as /api/auth/login but additionally sets it as an "
                "httpOnly cookie scoped to /internal so the staff portal never has the "
                "token in localStorage. Caller must be staff or master admin.",
)
def cookie_login(
    payload: CookieLoginRequest,
    response: Response,
    request: Request,
    db: Session = Depends(get_db),
):
    user: Optional[User] = None
    token: Optional[str] = None

    if payload.access_token:
        # Handoff path: caller already authenticated via /api/auth/login
        # and a UserSession row already exists. Just verify the token,
        # confirm staff role, and re-cookie it.
        decoded = decode_access_token(payload.access_token)
        if not decoded or "sub" not in decoded:
            raise HTTPException(status_code=401, detail="Invalid token")
        user = db.query(User).filter(
            func.lower(User.username) == str(decoded["sub"]).lower()
        ).first()
        if not user:
            raise HTTPException(status_code=401, detail="Invalid token")
        existing = db.query(UserSession).filter(
            UserSession.token_hash == hash_token(payload.access_token)
        ).first()
        if existing is None or existing.is_revoked:
            raise HTTPException(status_code=401, detail="Session revoked")
        token = payload.access_token
    else:
        if not (payload.username and payload.password):
            raise HTTPException(status_code=400, detail="Missing credentials")
        user = db.query(User).filter(
            func.lower(User.username) == payload.username.lower()
        ).first()
        if not user or not verify_password(payload.password, user.hashed_password):
            raise HTTPException(status_code=401, detail="Invalid credentials")

    assert user is not None
    if not (user.is_super_admin or getattr(user, "is_cadence_staff", False)):
        raise HTTPException(status_code=403, detail="Cadence staff access required")
    if hasattr(user, "is_active") and not user.is_active:
        raise HTTPException(status_code=403, detail="Account disabled")

    if token is None:
        token = create_access_token(data={"sub": user.username})
        expires_at = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        user.last_login_at = datetime.utcnow()
        db.add(UserSession(
            user_id=user.id,
            token_hash=hash_token(token),
            ip_address=getattr(getattr(request, "client", None), "host", None),
            user_agent=(request.headers.get("user-agent") or "")[:512],
            expires_at=expires_at,
        ))
        db.commit()

    # Cookie is scoped strictly to /api/internal — the only API
    # surface the staff portal speaks to. Tenant endpoints reused by
    # the portal (org create, access-code) are exposed as portal
    # proxies under /api/internal/portal/* that delegate to the
    # underlying handlers in routes/organizations.py.
    response.set_cookie(
        key="cadence_internal_token",
        value=token,
        max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        httponly=True,
        secure=os.getenv("APP_ENV", "development").lower() == "production",
        samesite="lax",
        path="/api/internal",
    )
    return {
        "token_type": "cookie",
        "user": {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "is_super_admin": user.is_super_admin,
            "is_cadence_staff": getattr(user, "is_cadence_staff", False),
        },
    }


@router.post(
    "/cookie-logout",
    summary="Internal portal cookie logout",
    description="Clears the cadence_internal_token cookie and revokes the matching "
                "UserSession row so the JWT can't be reused.",
)
def cookie_logout(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
):
    token = request.cookies.get("cadence_internal_token")
    if token:
        sess = db.query(UserSession).filter(
            UserSession.token_hash == hash_token(token)
        ).first()
        if sess and not sess.is_revoked:
            sess.is_revoked = True
            sess.revoked_at = datetime.utcnow()
            db.commit()
    response.delete_cookie(key="cadence_internal_token", path="/api/internal")
    return {"ok": True}


# --- organization access code ----------------------------------------

# --- staff onboarding (staff OR master admin) ------------------------

class OnboardOrgRequest(BaseModel):
    name: str
    type: str = "MANAGER"  # MANAGER | LABEL | PUBLISHER


@router.post(
    "/onboarding/organization",
    summary="Create a new organization (staff or master admin)",
    description="Staff-capable wrapper around the master-admin org create flow. Audited "
                "as INTERNAL_ORG_CREATED.",
)
def onboarding_create_org(
    payload: OnboardOrgRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_staff_or_admin),
):
    name = (payload.name or "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="Name required")
    org_type = (payload.type or "MANAGER").upper()
    if org_type not in {"MANAGER", "LABEL", "PUBLISHER"}:
        raise HTTPException(status_code=400, detail="Invalid org type")
    if db.query(Organization).filter(Organization.name == name).first():
        raise HTTPException(status_code=409, detail="Organization name already exists")
    # Org type is stored lowercase to match the legacy seed data, but
    # the API contract for the internal portal returns uppercase so the
    # UI filter ("MANAGER"/"LABEL"/"PUBLISHER") matches both legacy and
    # newly created rows. See organizations() below for the read path
    # which upper-cases on the way out.
    org = Organization(name=name, type=org_type.lower())
    db.add(org); db.commit(); db.refresh(org)
    _audit(
        db, current_user,
        action="INTERNAL_ORG_CREATED",
        entity_type="organization",
        entity_id=org.id,
        entity_name=org.name,
        details={"type": org_type},
    )
    return {"id": org.id, "name": org.name, "type": (org.type or "").upper()}


class OnboardOwnerRequest(BaseModel):
    organization_id: int
    username: str
    email: str
    password: str
    role: str = "OWNER"  # OWNER | ADMIN | MEMBER | VIEWER


@router.post(
    "/onboarding/owner-user",
    summary="Create a user and add them to an organization (staff or master admin)",
    description="Staff-capable wrapper that creates a User and an OrganizationMember "
                "row. Audited as INTERNAL_USER_CREATED.",
)
def onboarding_create_owner(
    payload: OnboardOwnerRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_staff_or_admin),
):
    role = (payload.role or "OWNER").upper()
    if role not in {"OWNER", "ADMIN", "MEMBER", "VIEWER"}:
        raise HTTPException(status_code=400, detail="Invalid role")
    org = db.query(Organization).filter(Organization.id == payload.organization_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    if db.query(User).filter(func.lower(User.username) == payload.username.lower()).first():
        raise HTTPException(status_code=409, detail="Username already exists")
    if db.query(User).filter(func.lower(User.email) == payload.email.lower()).first():
        raise HTTPException(status_code=409, detail="Email already exists")
    user = User(
        username=payload.username,
        email=payload.email,
        hashed_password=get_password_hash(payload.password),
        is_admin=False,
        is_super_admin=False,
        is_active=True,
    )
    db.add(user); db.commit(); db.refresh(user)
    db.add(OrganizationMember(
        organization_id=org.id,
        user_id=user.id,
        role=role,
    ))
    db.commit()
    _audit(
        db, current_user,
        action="INTERNAL_USER_CREATED",
        entity_type="user",
        entity_id=user.id,
        entity_name=user.username,
        details={"organization_id": org.id, "role": role},
    )
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "organization_id": org.id,
        "role": role,
    }


class SetAccessCodeRequest(BaseModel):
    access_code: Optional[str] = None  # if None -> rotate to a fresh random one


@router.post(
    "/organizations/{org_id}/access-code",
    summary="Set or rotate an organization's join access code",
    description="Either rotates the org's access code to a fresh random 8-char value "
                "(if access_code is omitted) or sets it to the value provided. Audited "
                "as INTERNAL_ACCESS_CODE_SET.",
)
def set_org_access_code(
    org_id: int,
    payload: SetAccessCodeRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_staff_or_admin),
):
    import string, random
    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    if payload.access_code:
        code = payload.access_code.strip().upper()
        if len(code) < 4 or len(code) > 32 or not code.isalnum():
            raise HTTPException(
                status_code=400,
                detail="Access code must be 4-32 alphanumeric chars",
            )
        clash = (
            db.query(Organization)
            .filter(Organization.access_code == code, Organization.id != org_id)
            .first()
        )
        if clash:
            raise HTTPException(status_code=409, detail="Access code already in use")
        action = "INTERNAL_ACCESS_CODE_SET"
    else:
        chars = string.ascii_uppercase + string.digits
        code = "".join(random.choices(chars, k=8))
        while db.query(Organization).filter(Organization.access_code == code).first():
            code = "".join(random.choices(chars, k=8))
        action = "INTERNAL_ACCESS_CODE_ROTATED"

    org.access_code = code
    db.commit()
    _audit(
        db, current_user,
        action=action,
        entity_type="organization",
        entity_id=org.id,
        entity_name=org.name,
    )
    return {"organization_id": org.id, "access_code": org.access_code}


@router.get(
    "/organizations/{org_id}/access-code",
    summary="Get an organization's join access code",
    description="Read-only fetch of the org's current join code; auto-generates one if "
                "the org has never had it set. Mirrors the owner-only endpoint at "
                "/api/organizations/{id}/access-code so staff don't need to log in as "
                "the owner just to read the code during onboarding.",
)
def get_org_access_code(
    org_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_staff_or_admin),
):
    import string, random
    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    if not getattr(org, "access_code", None):
        chars = string.ascii_uppercase + string.digits
        new_code = "".join(random.choices(chars, k=8))
        while db.query(Organization).filter(Organization.access_code == new_code).first():
            new_code = "".join(random.choices(chars, k=8))
        org.access_code = new_code
        db.commit()
        _audit(
            db, current_user,
            action="INTERNAL_ACCESS_CODE_GENERATED",
            entity_type="organization",
            entity_id=org.id,
            entity_name=org.name,
        )
    return {"organization_id": org.id, "access_code": org.access_code}
