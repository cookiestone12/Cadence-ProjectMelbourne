"""Internal developer-tools endpoints (Task #89).

Source viewer (read-only), deploy status, runtime config (feature
flags + knobs), enriched logs (search/filter/download), saved queries
+ query history. All require the internal-portal cookie auth via
`get_current_staff_or_admin`.

Source viewer is strictly read-only by design — no write surface
exists. Treat it like a browser-friendly `cat`."""
from __future__ import annotations

import csv
import io
import json
import logging
import os
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import desc, text
from sqlalchemy.orm import Session

from ..models import get_db, User, Organization, OrganizationMember
from ..models.models import (
    AuditLog, RuntimeConfig, DeployEvent, SavedQuery, QueryHistoryEntry,
)
from ..utils.auth import get_current_staff_from_cookie as get_current_staff_or_admin
from ..utils.logging_config import tail_logs
from ..services import deploy_info, runtime_config

logger = logging.getLogger("cadence")

router = APIRouter(prefix="/api/internal/portal", tags=["Internal Dev Tools"])


# ---------------------------------------------------------------------
# Audit helper (mirrors internal_portal._audit so writes here are
# recorded in the same trail).
# ---------------------------------------------------------------------

def _resolve_audit_org_id(db: Session, user: User) -> Optional[int]:
    membership = (
        db.query(OrganizationMember.organization_id)
        .filter(OrganizationMember.user_id == user.id)
        .order_by(OrganizationMember.organization_id.asc())
        .first()
    )
    if membership and membership[0]:
        return int(membership[0])
    fallback = db.query(Organization.id).order_by(Organization.id.asc()).first()
    return int(fallback[0]) if fallback else None


def _audit(db: Session, user: User, *, action: str, entity_type: str,
           entity_id: Optional[int] = None, entity_name: Optional[str] = None,
           details: Optional[dict] = None) -> None:
    org_id = _resolve_audit_org_id(db, user)
    if org_id is None:
        return
    try:
        db.add(AuditLog(
            organization_id=org_id, user_id=user.id, action=action,
            entity_type=entity_type, entity_id=entity_id,
            entity_name=entity_name, details=details or {},
        ))
        db.commit()
    except Exception:
        db.rollback()
        logger.warning("internal-dev audit insert failed", exc_info=True)


# ---------------------------------------------------------------------
# Source Viewer (read-only)
# ---------------------------------------------------------------------

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_ALLOWED_ROOTS = ("backend", "frontend/src")
_MAX_FILE_BYTES = 1_000_000  # 1 MB cap on individual file reads
_DENY_DIRS = {"__pycache__", "node_modules", ".git", "dist", "build", ".pytest_cache"}


def _is_allowed_path(p: Path) -> bool:
    """True iff `p` is inside one of the whitelisted roots and contains
    no symlinks anywhere along the chain. Resolved against the repo
    root so any `..` traversal resolves out before the prefix check."""
    try:
        resolved = (_REPO_ROOT / p).resolve(strict=False)
    except Exception:
        return False
    if not str(resolved).startswith(str(_REPO_ROOT) + os.sep) and resolved != _REPO_ROOT:
        return False
    rel = resolved.relative_to(_REPO_ROOT)
    rel_str = str(rel).replace(os.sep, "/")
    if not any(rel_str == r or rel_str.startswith(r + "/") for r in _ALLOWED_ROOTS):
        return False
    # Reject if any segment is a denied dir or hidden file/dir.
    for part in rel.parts:
        if part in _DENY_DIRS or part.startswith("."):
            return False
    # Reject symlinks anywhere on the chain.
    cur = _REPO_ROOT
    for part in rel.parts:
        cur = cur / part
        if cur.exists() and cur.is_symlink():
            return False
    return True


@router.get(
    "/source/tree",
    summary="List source files in a whitelisted directory",
    description="Returns the immediate children of `path` (default repo root view: "
                "the two whitelisted roots `backend/` and `frontend/src/`). Read-only.",
)
def source_tree(
    path: Optional[str] = Query(default=None, description="Repo-relative directory"),
    current_user: User = Depends(get_current_staff_or_admin),
):
    if not path:
        # Synthesise a top-level virtual listing showing the two roots.
        items: list[dict] = []
        for r in _ALLOWED_ROOTS:
            d = _REPO_ROOT / r
            if d.exists() and d.is_dir():
                items.append({"name": r, "path": r, "type": "dir", "size": None})
        return {"path": "", "items": items}

    rel = path.strip("/")
    if not _is_allowed_path(Path(rel)):
        raise HTTPException(status_code=404, detail="Not found")
    full = (_REPO_ROOT / rel).resolve()
    if not full.exists() or not full.is_dir():
        raise HTTPException(status_code=404, detail="Not a directory")

    items = []
    for entry in sorted(full.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower())):
        if entry.is_symlink():
            continue
        if entry.name in _DENY_DIRS or entry.name.startswith("."):
            continue
        try:
            items.append({
                "name": entry.name,
                "path": (Path(rel) / entry.name).as_posix(),
                "type": "dir" if entry.is_dir() else "file",
                "size": entry.stat().st_size if entry.is_file() else None,
            })
        except Exception:
            continue
    return {"path": rel, "items": items}


@router.get(
    "/source/file",
    summary="Read a single source file",
    description="Returns the text contents of a whitelisted file. Files larger than 1MB "
                "are rejected. Read-only.",
)
def source_file(
    path: str = Query(..., description="Repo-relative file path"),
    current_user: User = Depends(get_current_staff_or_admin),
):
    rel = path.strip("/")
    if not _is_allowed_path(Path(rel)):
        raise HTTPException(status_code=404, detail="Not found")
    full = (_REPO_ROOT / rel).resolve()
    if not full.exists() or not full.is_file():
        raise HTTPException(status_code=404, detail="Not a file")
    size = full.stat().st_size
    if size > _MAX_FILE_BYTES:
        raise HTTPException(status_code=413, detail=f"File too large ({size} bytes)")
    try:
        content = full.read_text(encoding="utf-8")
        is_binary = False
    except UnicodeDecodeError:
        content = ""
        is_binary = True
    return {
        "path": rel,
        "size": size,
        "is_binary": is_binary,
        "content": content,
        "language": full.suffix.lstrip(".") or "text",
    }


# ---------------------------------------------------------------------
# Deploy Status
# ---------------------------------------------------------------------

@router.get(
    "/deploy/status",
    summary="Current deploy fingerprint + recent boot history",
    description="Returns the running git SHA, boot timestamp, environment, runtime "
                "versions, plus the last ~20 boots from deploy_event.",
)
def deploy_status(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_staff_or_admin),
):
    info = deploy_info.current() or deploy_info.capture()
    history_rows = (
        db.query(DeployEvent)
        .order_by(desc(DeployEvent.id))
        .limit(20)
        .all()
    )
    history = [
        {
            "id": r.id,
            "booted_at": r.booted_at.isoformat() if r.booted_at else None,
            "git_short": r.git_short,
            "git_message": r.git_message,
            "git_author": r.git_author,
            "app_env": r.app_env,
            "build_version": r.build_version,
            "python_version": r.python_version,
            "node_version": r.node_version,
        }
        for r in history_rows
    ]
    return {"current": info.to_dict(), "history": history}


# ---------------------------------------------------------------------
# Runtime Config (feature flags + knobs)
# ---------------------------------------------------------------------

class ConfigUpdate(BaseModel):
    value: Any


@router.get(
    "/config",
    summary="List all runtime config keys",
    description="Returns every runtime_config row, grouped by category in the response.",
)
def list_config(current_user: User = Depends(get_current_staff_or_admin)):
    items = runtime_config.all_items()
    grouped: dict[str, list[dict]] = {}
    for it in items:
        grouped.setdefault(it["category"], []).append(it)
    return {"items": items, "grouped": grouped}


@router.put(
    "/config/{key}",
    summary="Update a runtime config value",
    description="Updates the value for a single runtime_config key. Coerces to the "
                "configured value_type. Writes an INTERNAL_CONFIG_SET audit row.",
)
def update_config(
    key: str,
    payload: ConfigUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_staff_or_admin),
):
    try:
        result = runtime_config.set_value(db, key, payload.value, current_user.id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Unknown config key")
    except (ValueError, TypeError) as e:
        raise HTTPException(status_code=400, detail=f"Invalid value: {e}")
    _audit(
        db, current_user,
        action="INTERNAL_CONFIG_SET",
        entity_type="runtime_config",
        entity_name=key,
        details={"value": result["value"]},
    )
    return result


# ---------------------------------------------------------------------
# Logs (server-side filters + JSONL download)
# ---------------------------------------------------------------------

def _filter_logs(entries: list[dict], q: Optional[str], request_id: Optional[str]) -> list[dict]:
    if q:
        ql = q.lower()
        entries = [
            e for e in entries
            if ql in (e.get("message") or "").lower()
            or ql in (e.get("logger") or "").lower()
            or ql in (e.get("exception") or "").lower()
        ]
    if request_id:
        entries = [e for e in entries if (e.get("request_id") or "") == request_id]
    return entries


@router.get(
    "/logs/search",
    summary="Search the in-process log ring buffer",
    description="Like /logs but with text search (`q`), `request_id` exact-match, and "
                "the existing `level` + `since` filters.",
)
def logs_search(
    q: Optional[str] = Query(default=None),
    level: Optional[str] = Query(default=None),
    since: Optional[str] = Query(default=None),
    request_id: Optional[str] = Query(default=None),
    limit: int = Query(default=500, ge=1, le=5000),
    current_user: User = Depends(get_current_staff_or_admin),
):
    parsed_since: Optional[datetime] = None
    if since:
        try:
            parsed_since = datetime.fromisoformat(since)
        except ValueError:
            raise HTTPException(status_code=400, detail="since must be ISO-8601")
    entries = tail_logs(level=level, since=parsed_since, limit=10_000)
    entries = _filter_logs(entries, q, request_id)
    if len(entries) > limit:
        entries = entries[-limit:]
    return {"entries": entries, "count": len(entries)}


@router.get(
    "/logs/download",
    summary="Download filtered logs as JSONL",
    description="Streams the same filtered entries as /logs/search but as one JSON "
                "object per line for easy grep/jq.",
)
def logs_download(
    q: Optional[str] = Query(default=None),
    level: Optional[str] = Query(default=None),
    since: Optional[str] = Query(default=None),
    request_id: Optional[str] = Query(default=None),
    limit: int = Query(default=10_000, ge=1, le=10_000),
    current_user: User = Depends(get_current_staff_or_admin),
):
    parsed_since: Optional[datetime] = None
    if since:
        try:
            parsed_since = datetime.fromisoformat(since)
        except ValueError:
            raise HTTPException(status_code=400, detail="since must be ISO-8601")
    entries = tail_logs(level=level, since=parsed_since, limit=10_000)
    entries = _filter_logs(entries, q, request_id)
    if len(entries) > limit:
        entries = entries[-limit:]

    def stream():
        for e in entries:
            yield json.dumps(e, default=str) + "\n"

    fname = f"cadence-logs-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}.jsonl"
    return StreamingResponse(
        stream(),
        media_type="application/x-ndjson",
        headers={"Content-Disposition": f'attachment; filename="{fname}"'},
    )


# ---------------------------------------------------------------------
# Saved Queries + History
# ---------------------------------------------------------------------

class SavedQueryCreate(BaseModel):
    name: str
    sql: str


_SQL_FORBIDDEN = re.compile(
    r"\b(insert|update|delete|drop|truncate|alter|create|grant|revoke|"
    r"vacuum|reindex|copy|comment|cluster|do|call|merge|"
    r"set_config|pg_terminate_backend|pg_cancel_backend|pg_reload_conf|"
    r"pg_advisory_lock|pg_read_file|pg_ls_dir|lo_import|lo_export)\b",
    re.IGNORECASE,
)
# Block SQL comments — they're a classic guard-bypass surface.
_SQL_COMMENT = re.compile(r"(--|/\*|\*/)")


def _ensure_read_only(sql: str) -> None:
    stripped = sql.strip().rstrip(";").strip()
    if not stripped:
        raise HTTPException(status_code=400, detail="Empty SQL")
    if not re.match(r"^(select|with)\b", stripped, re.IGNORECASE):
        raise HTTPException(status_code=400, detail="Only SELECT/WITH queries are allowed")
    if _SQL_FORBIDDEN.search(stripped):
        raise HTTPException(status_code=400, detail="Mutating SQL keywords are not allowed")
    if _SQL_COMMENT.search(stripped):
        raise HTTPException(status_code=400, detail="SQL comments are not allowed")
    if ";" in stripped:
        raise HTTPException(status_code=400, detail="Multiple statements are not allowed")


@router.get(
    "/queries/saved",
    summary="List the staff user's saved queries",
)
def list_saved_queries(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_staff_or_admin),
):
    rows = (
        db.query(SavedQuery)
        .filter(SavedQuery.owner_id == current_user.id)
        .order_by(SavedQuery.created_at.desc())
        .all()
    )
    return {
        "rows": [
            {"id": r.id, "name": r.name, "sql": r.sql,
             "created_at": r.created_at.isoformat() if r.created_at else None}
            for r in rows
        ]
    }


@router.post(
    "/queries/saved",
    summary="Save a SELECT query for re-running later",
)
def create_saved_query(
    payload: SavedQueryCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_staff_or_admin),
):
    name = (payload.name or "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="Name required")
    _ensure_read_only(payload.sql)
    row = SavedQuery(name=name, sql=payload.sql.strip(), owner_id=current_user.id)
    db.add(row); db.commit(); db.refresh(row)
    _audit(
        db, current_user,
        action="INTERNAL_QUERY_SAVED",
        entity_type="saved_query",
        entity_id=row.id, entity_name=name,
    )
    return {"id": row.id, "name": row.name}


@router.delete(
    "/queries/saved/{query_id}",
    summary="Delete one of your saved queries",
)
def delete_saved_query(
    query_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_staff_or_admin),
):
    row = db.query(SavedQuery).filter(
        SavedQuery.id == query_id,
        SavedQuery.owner_id == current_user.id,
    ).first()
    if not row:
        raise HTTPException(status_code=404, detail="Not found")
    db.delete(row); db.commit()
    _audit(
        db, current_user,
        action="INTERNAL_QUERY_DELETED",
        entity_type="saved_query",
        entity_id=query_id, entity_name=row.name,
    )
    return {"ok": True}


@router.get(
    "/queries/history",
    summary="Recent queries you've run",
)
def list_query_history(
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_staff_or_admin),
):
    rows = (
        db.query(QueryHistoryEntry)
        .filter(QueryHistoryEntry.owner_id == current_user.id)
        .order_by(QueryHistoryEntry.ran_at.desc())
        .limit(limit)
        .all()
    )
    return {
        "rows": [
            {
                "id": r.id, "sql": r.sql,
                "ran_at": r.ran_at.isoformat() if r.ran_at else None,
                "row_count": r.row_count,
                "success": r.success,
                "error": r.error,
            }
            for r in rows
        ]
    }


class QueryRunRequest(BaseModel):
    sql: str
    limit: Optional[int] = 100


@router.post(
    "/queries/run",
    summary="Run a read-only SELECT and capture history",
    description="Executes a SELECT/WITH query (max 1000 rows). Records the query in "
                "query_history regardless of success.",
)
def run_query(
    payload: QueryRunRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_staff_or_admin),
):
    sql = (payload.sql or "").strip()
    _ensure_read_only(sql)
    cap = max(1, min(payload.limit or 100, 1000))
    # Wrap user query in a subselect so we can apply our own limit
    # without mutating their text. This works for both SELECT and
    # CTEs because PostgreSQL accepts subselects on either.
    wrapped = f"SELECT * FROM ({sql.rstrip(';')}) AS _staff_q LIMIT {cap}"

    columns: list[str] = []
    rows: list[list[Any]] = []
    success = True
    err: Optional[str] = None
    try:
        result = db.execute(text(wrapped))
        columns = list(result.keys())
        for r in result.fetchall():
            rows.append([_jsonify(v) for v in r])
    except Exception as e:
        success = False
        err = str(e)
        # Clear the failed transaction so the history insert below can
        # commit on the same session.
        db.rollback()

    try:
        db.add(QueryHistoryEntry(
            owner_id=current_user.id, sql=sql,
            row_count=(len(rows) if success else None),
            success=success, error=err,
        ))
        db.commit()
        # Trim per-user history to last 50 — older rows are fine to drop.
        keep_ids = [
            row[0] for row in db.query(QueryHistoryEntry.id)
            .filter(QueryHistoryEntry.owner_id == current_user.id)
            .order_by(QueryHistoryEntry.ran_at.desc())
            .limit(50).all()
        ]
        if keep_ids:
            db.query(QueryHistoryEntry).filter(
                QueryHistoryEntry.owner_id == current_user.id,
                ~QueryHistoryEntry.id.in_(keep_ids),
            ).delete(synchronize_session=False)
            db.commit()
    except Exception:
        db.rollback()
        logger.warning("Failed to record query history", exc_info=True)

    if not success:
        raise HTTPException(status_code=400, detail=err or "Query failed")

    return {"columns": columns, "rows": rows, "row_count": len(rows)}


@router.post(
    "/queries/run.csv",
    summary="Run a read-only SELECT and stream results as CSV",
)
def run_query_csv(
    payload: QueryRunRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_staff_or_admin),
):
    sql = (payload.sql or "").strip()
    _ensure_read_only(sql)
    cap = max(1, min(payload.limit or 1000, 10_000))
    wrapped = f"SELECT * FROM ({sql.rstrip(';')}) AS _staff_q LIMIT {cap}"
    try:
        result = db.execute(text(wrapped))
        columns = list(result.keys())
        rows = result.fetchall()
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    def stream():
        buf = io.StringIO(); w = csv.writer(buf)
        w.writerow(columns); yield buf.getvalue(); buf.seek(0); buf.truncate(0)
        for r in rows:
            w.writerow([_jsonify(v) for v in r])
            yield buf.getvalue(); buf.seek(0); buf.truncate(0)

    fname = f"query-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}.csv"
    return StreamingResponse(
        stream(), media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{fname}"'},
    )


def _jsonify(v: Any) -> Any:
    if isinstance(v, datetime):
        return v.isoformat()
    if isinstance(v, (bytes, bytearray)):
        return f"<{len(v)} bytes>"
    return v
