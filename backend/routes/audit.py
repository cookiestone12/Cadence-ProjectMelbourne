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


@router.get("/{org_id}/audit/report/pdf")
def audit_report_pdf(
    org_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Render the open audit findings as a branded PDF report."""
    verify_org_access(current_user, org_id, db)

    from fastapi import Response
    from ..models import Organization, Song
    from ..services.branding import theme_from_org, safe_filename_segment
    from ..services.pdf_engine import BrandedPDF
    from ..services.excel_engine import pdf_response_headers

    org = db.query(Organization).filter(Organization.id == org_id).first()
    theme = theme_from_org(org)

    findings = db.query(RoyaltyAudit).filter(
        RoyaltyAudit.organization_id == org_id,
        RoyaltyAudit.resolved.is_(False),
    ).order_by(RoyaltyAudit.severity.desc(), RoyaltyAudit.id.desc()).all()

    by_severity: Dict[str, List[RoyaltyAudit]] = {"CRITICAL": [], "HIGH": [], "MEDIUM": [], "LOW": []}
    for f in findings:
        sev = (f.severity or "LOW").upper()
        by_severity.setdefault(sev, []).append(f)

    by_type: Dict[str, int] = {}
    for f in findings:
        by_type[f.audit_type] = by_type.get(f.audit_type, 0) + 1

    song_titles: Dict[int, str] = {}
    song_ids = {f.song_id for f in findings if f.song_id}
    if song_ids:
        for s in db.query(Song.id, Song.title).filter(Song.id.in_(song_ids)).all():
            song_titles[s.id] = s.title

    pdf = BrandedPDF(theme, title="Royalty Audit Report",
                     subtitle=org.name if org else f"Organization #{org_id}")
    pdf.cover()

    pdf.kpi_row([
        {"label": "Open Findings", "value": str(len(findings))},
        {"label": "Critical", "value": str(len(by_severity.get("CRITICAL", [])))},
        {"label": "High", "value": str(len(by_severity.get("HIGH", [])))},
        {"label": "Medium / Low",
         "value": str(len(by_severity.get("MEDIUM", [])) + len(by_severity.get("LOW", [])))},
    ])

    if by_type:
        pdf.section("Findings by Type")
        type_rows = [[k.replace("_", " ").title(), str(v)] for k, v in sorted(by_type.items())]
        pdf.table(headers=["Audit Type", "Count"], rows=type_rows,
                  col_widths=[3.5, 1.0], align=["LEFT", "RIGHT"])

    severity_order = ["CRITICAL", "HIGH", "MEDIUM", "LOW"]
    for sev in severity_order:
        items = by_severity.get(sev, [])
        if not items:
            continue
        pdf.section(f"{sev.title()} Findings ({len(items)})")
        rows = []
        for f in items[:120]:
            song = song_titles.get(f.song_id, "—") if f.song_id else "—"
            period = ""
            if f.period_start and f.period_end:
                period = f"{f.period_start.strftime('%Y-%m')} – {f.period_end.strftime('%Y-%m')}"
            elif f.period_start:
                period = f.period_start.strftime("%Y-%m")
            rows.append([
                f.audit_type.replace("_", " ").title() if f.audit_type else "—",
                song[:32],
                period or "—",
                f.message or "—",
            ])
        pdf.table(
            headers=["Type", "Song", "Period", "Detail"],
            rows=rows,
            col_widths=[1.2, 1.6, 1.0, 3.4],
            align=["LEFT", "LEFT", "LEFT", "LEFT"],
            wrap_cells=True,
        )

    if not findings:
        pdf.section("No Open Findings")
        pdf.text("All audit checks passed for this organization. Great work.")

    pdf.section("Methodology")
    pdf.small(
        "<b>CROSS_STATEMENT</b> — duplicate song-period payments across statements. "
        "<b>RATE_CHECK</b> — payment below the configured master rate floor. "
        "<b>MISSING_PERIOD</b> — gaps in the expected statement cadence. "
        "<b>DECAY_ANOMALY</b> — period revenue diverging from the song's fitted exponential decay."
    )

    safe_org = safe_filename_segment(org.name if org else f"org_{org_id}", "org")
    filename = f"cadence_audit_report_{safe_org}_{datetime.utcnow().strftime('%Y%m%d')}.pdf"
    return Response(content=pdf.build(), headers=pdf_response_headers(filename))


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
