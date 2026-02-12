from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import Optional, List
from datetime import datetime

from ..models import get_db, User, OrganizationMember
from ..models.models import AuditLog
from ..utils.auth import get_current_user

router = APIRouter(prefix="/api/audit-log", tags=["audit_log"])


def verify_org_access(user: User, org_id: int, db: Session):
    membership = db.query(OrganizationMember).filter(
        OrganizationMember.user_id == user.id,
        OrganizationMember.organization_id == org_id
    ).first()
    if not membership and not user.is_super_admin:
        raise HTTPException(status_code=403, detail="Access denied")
    return membership


@router.get("/org/{org_id}")
def get_audit_logs(
    org_id: int,
    action: Optional[str] = None,
    entity_type: Optional[str] = None,
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


@router.get("/org/{org_id}/summary")
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
