"""Royalty Audit endpoints — Task #173 (A+ Phase 6).

Exposes the four-check royalty audit engine to the frontend Audit page.

Endpoints
---------
- ``GET  /api/organizations/{org_id}/audit/findings`` — list findings
  with severity / type / resolved filters and pagination.
- ``GET  /api/organizations/{org_id}/audit/summary`` — counts by
  severity and type for the dashboard cards.
- ``POST /api/organizations/{org_id}/audit/scan`` — run the full
  audit-engine scan and return per-check counts.
- ``POST /api/organizations/{org_id}/audit/findings/{audit_id}/resolve``
  — mark a finding resolved with optional notes.
"""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from pydantic import BaseModel
from sqlalchemy import desc, func
from sqlalchemy.orm import Session

from ..models import RoyaltyAudit, User, get_db
from ..services import audit_engine
from ..services.luminate_service import LuminateService
from ..utils.auth import get_current_user
from .audit_log import verify_org_access

router = APIRouter(prefix="/api/organizations", tags=["Royalty Audit"])


def _serialize(a: RoyaltyAudit) -> dict:
    return {
        "id": a.id,
        "organization_id": a.organization_id,
        "song_id": a.song_id,
        "statement_id": a.statement_id,
        "audit_type": a.audit_type,
        "severity": a.severity,
        "expected_cents": a.expected_cents,
        "actual_cents": a.actual_cents,
        "discrepancy_cents": a.discrepancy_cents,
        "period_start": a.period_start.isoformat() if a.period_start else None,
        "period_end": a.period_end.isoformat() if a.period_end else None,
        "description": a.description,
        "details": a.details or {},
        "resolved": a.resolved,
        "resolved_at": a.resolved_at.isoformat() if a.resolved_at else None,
        "resolved_by_user_id": a.resolved_by_user_id,
        "resolution_notes": a.resolution_notes,
        "created_at": a.created_at.isoformat() if a.created_at else None,
        "updated_at": a.updated_at.isoformat() if a.updated_at else None,
    }


@router.get("/{org_id}/audit/findings")
def list_findings(
    org_id: int,
    audit_type: Optional[str] = None,
    severity: Optional[str] = None,
    resolved: Optional[bool] = None,
    song_id: Optional[int] = None,
    limit: int = Query(default=100, le=500),
    offset: int = 0,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    verify_org_access(current_user, org_id, db)
    q = db.query(RoyaltyAudit).filter(RoyaltyAudit.organization_id == org_id)
    if audit_type:
        q = q.filter(RoyaltyAudit.audit_type == audit_type)
    if severity:
        q = q.filter(RoyaltyAudit.severity == severity)
    if resolved is not None:
        q = q.filter(RoyaltyAudit.resolved == resolved)
    if song_id is not None:
        q = q.filter(RoyaltyAudit.song_id == song_id)
    total = q.count()
    rows = (
        q.order_by(desc(RoyaltyAudit.created_at))
        .offset(offset)
        .limit(limit)
        .all()
    )
    return {
        "total": total,
        "findings": [_serialize(r) for r in rows],
    }


@router.get("/{org_id}/audit/summary")
def audit_summary(
    org_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    verify_org_access(current_user, org_id, db)
    base = db.query(RoyaltyAudit).filter(
        RoyaltyAudit.organization_id == org_id,
        RoyaltyAudit.resolved.is_(False),
    )
    by_severity_rows = (
        db.query(RoyaltyAudit.severity, func.count(RoyaltyAudit.id))
        .filter(
            RoyaltyAudit.organization_id == org_id,
            RoyaltyAudit.resolved.is_(False),
        )
        .group_by(RoyaltyAudit.severity)
        .all()
    )
    by_type_rows = (
        db.query(RoyaltyAudit.audit_type, func.count(RoyaltyAudit.id))
        .filter(
            RoyaltyAudit.organization_id == org_id,
            RoyaltyAudit.resolved.is_(False),
        )
        .group_by(RoyaltyAudit.audit_type)
        .all()
    )
    return {
        "open_total": base.count(),
        "by_severity": {sev: cnt for sev, cnt in by_severity_rows},
        "by_type": {t: cnt for t, cnt in by_type_rows},
    }


@router.post("/{org_id}/audit/scan")
def run_scan(
    org_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    verify_org_access(current_user, org_id, db)
    counts = audit_engine.run_full_scan(db, org_id)
    return {
        "scanned_at": datetime.utcnow().isoformat(),
        "counts": counts,
        "total": sum(counts.values()),
    }


class ResolveBody(BaseModel):
    resolution_notes: Optional[str] = None


@router.post("/{org_id}/audit/findings/{audit_id}/resolve")
def resolve_finding(
    org_id: int,
    audit_id: int,
    body: ResolveBody,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    verify_org_access(current_user, org_id, db)
    finding = (
        db.query(RoyaltyAudit)
        .filter(
            RoyaltyAudit.id == audit_id,
            RoyaltyAudit.organization_id == org_id,
        )
        .first()
    )
    if not finding:
        raise HTTPException(status_code=404, detail="Finding not found")
    finding.resolved = True
    finding.resolved_at = datetime.utcnow()
    finding.resolved_by_user_id = current_user.id
    finding.resolution_notes = body.resolution_notes
    db.commit()
    db.refresh(finding)
    return _serialize(finding)


@router.post("/{org_id}/audit/luminate/import")
async def import_luminate_csv(
    org_id: int,
    file: UploadFile = File(...),
    rescan: bool = Query(default=True),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Upload a Luminate CSV export. Upserts SongStreamingMetrics rows
    tagged ``data_source='luminate'`` and (by default) re-runs the
    audit engine afterwards so cross-source discrepancies surface
    immediately."""
    verify_org_access(current_user, org_id, db)
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="CSV file required")
    svc = LuminateService()
    result = svc.import_csv(file.file, org_id, db)
    rescan_counts = None
    if rescan:
        rescan_counts = audit_engine.run_full_scan(db, org_id)
    return {
        "import": result,
        "rescan": rescan_counts,
    }


@router.post("/{org_id}/audit/findings/{audit_id}/reopen")
def reopen_finding(
    org_id: int,
    audit_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    verify_org_access(current_user, org_id, db)
    finding = (
        db.query(RoyaltyAudit)
        .filter(
            RoyaltyAudit.id == audit_id,
            RoyaltyAudit.organization_id == org_id,
        )
        .first()
    )
    if not finding:
        raise HTTPException(status_code=404, detail="Finding not found")
    finding.resolved = False
    finding.resolved_at = None
    finding.resolved_by_user_id = None
    finding.resolution_notes = None
    db.commit()
    db.refresh(finding)
    return _serialize(finding)
