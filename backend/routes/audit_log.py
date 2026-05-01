from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import Optional, List
from datetime import datetime

from ..models import get_db, User, OrganizationMember
from ..models.models import AuditLog
from ..utils.auth import get_current_user

router = APIRouter(prefix="/api/audit-log", tags=["Audit Log"])


def verify_org_access(user: User, org_id: int, db: Session):
    membership = db.query(OrganizationMember).filter(
        OrganizationMember.user_id == user.id,
        OrganizationMember.organization_id == org_id
    ).first()
    if not membership and not user.is_super_admin:
        raise HTTPException(status_code=403, detail="Access denied")
    return membership


@router.get("/org/{org_id}", summary="List org audit log entries", description="Returns the org's audit trail (provisioning, deletes, role changes, payments, etc.) with paging. Used by the org settings > audit log page.\n\n**Path parameter:** `org_id`.\n**Query:** `category` (`auth|catalog|royalties|admin|...`), `actor_user_id`, `start_date`, `end_date`, `limit` (default 50), `offset`.\n**Auth:** Bearer JWT — caller must be an admin of the org.\n**Response:** `{ total, entries: [{id, category, action, actor_user_id, actor_email, target_type, target_id, summary, metadata, created_at}] }`.")
def get_audit_logs(
    org_id: int,
    action: Optional[str] = None,
    entity_type: Optional[str] = None,
    user_id: Optional[int] = None,
    song_id: Optional[int] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    limit: int = Query(default=50, le=200),
    offset: int = 0,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    verify_org_access(current_user, org_id, db)

    query = db.query(AuditLog).filter(AuditLog.organization_id == org_id)

    if action:
        query = query.filter(AuditLog.action == action)
    if entity_type:
        query = query.filter(AuditLog.entity_type == entity_type)
    if user_id:
        query = query.filter(AuditLog.user_id == user_id)
    if song_id is not None:
        # Task #171 — Phase 4: server-side song scope for the SongDetailModal
        # Split History timeline. Split mutation rows store the affected
        # song under details.song_id; without this filter the frontend had
        # to fetch up to 200 org-wide rows and slice client-side, which
        # silently dropped events on busy orgs. We use the JSONB ->>
        # text-extract operator (Postgres) which still returns matches
        # even when other audit rows have a different details schema.
        from sqlalchemy import cast, String
        query = query.filter(
            cast(AuditLog.details["song_id"], String) == str(song_id)
        )
    if start_date:
        try:
            start = datetime.fromisoformat(start_date)
            query = query.filter(AuditLog.created_at >= start)
        except ValueError:
            pass
    if end_date:
        try:
            end = datetime.fromisoformat(end_date)
            query = query.filter(AuditLog.created_at <= end)
        except ValueError:
            pass

    total = query.count()
    logs = query.order_by(desc(AuditLog.created_at)).offset(offset).limit(limit).all()

    return {
        "total": total,
        "logs": [
            {
                "id": log.id,
                "action": log.action,
                "entity_type": log.entity_type,
                "entity_id": log.entity_id,
                "entity_name": log.entity_name,
                "details": log.details,
                "created_at": log.created_at.isoformat() if log.created_at else None,
                "user_name": log.user.username if log.user else "System",
            }
            for log in logs
        ],
    }


@router.get("/org/{org_id}/summary", summary="Audit log summary", description='Aggregated counts of audit events per category for the dashboard tile.\n\n**Path parameter:** `org_id`.\n**Query:** `start_date`, `end_date`.\n**Auth:** Bearer JWT — caller must be an admin of the org.\n**Response:** `{ totals: {by_category: {...}, by_actor: [...]}, period: {start, end} }`.')
def get_audit_summary(
    org_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    verify_org_access(current_user, org_id, db)

    from sqlalchemy import func

    action_counts = (
        db.query(AuditLog.action, func.count(AuditLog.id))
        .filter(AuditLog.organization_id == org_id)
        .group_by(AuditLog.action)
        .all()
    )

    entity_counts = (
        db.query(AuditLog.entity_type, func.count(AuditLog.id))
        .filter(AuditLog.organization_id == org_id)
        .group_by(AuditLog.entity_type)
        .all()
    )

    return {
        "by_action": {a: c for a, c in action_counts},
        "by_entity": {e: c for e, c in entity_counts},
    }
