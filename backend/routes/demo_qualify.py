"""Demo-qualification form endpoints.

Public:
  POST /api/qualify          — save submission, send notification email

Admin (super-admin only):
  GET  /api/admin/qualifications         — list newest first
  GET  /api/admin/qualifications/{id}    — full record
  GET  /api/admin/qualifications/export  — CSV download
"""
from __future__ import annotations

import csv
import io
import logging
import re
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, EmailStr, field_validator
from sqlalchemy.orm import Session

from ..models import get_db
from ..models.misc import DemoQualification
from ..services.email_provider import get_email_provider
from ..utils.auth import get_current_super_admin

logger = logging.getLogger("cadence")

router = APIRouter(tags=["Demo Qualification"])
admin_router = APIRouter(prefix="/api/admin", tags=["Demo Qualification Admin"])

NOTIFY_EMAIL = "communication@cadence-ci.com"

ROLE_OPTIONS = [
    "Label", "Publisher", "Artist/Songwriter", "Manager",
    "Distributor", "Catalog investor/fund", "Rights administrator", "Other",
]
CATALOG_COVERAGE_OPTIONS = ["Masters", "Publishing", "Both", "Still exploring"]
CATALOG_SIZE_OPTIONS = [
    "Under 100", "100-1,000", "1,000-10,000", "10,000-100,000", "100,000+",
]
CURRENT_MANAGEMENT_OPTIONS = [
    "Spreadsheets", "Distributor/admin dashboard", "Dedicated platform",
    "Outsourced", "No system yet",
]
GOALS_OPTIONS = [
    "Royalty processing", "Rights tracking", "Catalog valuation",
    "Statement parsing", "Stakeholder reporting",
    "Acquisition due diligence", "Other",
]
TIMELINE_OPTIONS = ["Immediately", "1-3 months", "3-6 months", "Just researching"]

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class QualifyRequest(BaseModel):
    full_name: str
    work_email: str
    company: str
    role: str
    catalog_coverage: Optional[List[str]] = None
    catalog_size: Optional[str] = None
    current_management: Optional[str] = None
    goals: Optional[List[str]] = None
    reason_now: Optional[str] = None
    timeline: Optional[str] = None
    demo_notes: Optional[str] = None
    honeypot: Optional[str] = None

    @field_validator("full_name", "company")
    @classmethod
    def not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("This field is required.")
        return v.strip()

    @field_validator("work_email")
    @classmethod
    def valid_email(cls, v: str) -> str:
        v = (v or "").strip()
        if not v or not _EMAIL_RE.match(v):
            raise ValueError("A valid work email is required.")
        return v

    @field_validator("role")
    @classmethod
    def valid_role(cls, v: str) -> str:
        if v not in ROLE_OPTIONS:
            raise ValueError(f"Invalid role.")
        return v


def _notification_html(q: DemoQualification) -> str:
    coverage = ", ".join(q.catalog_coverage or []) or "—"
    goals = ", ".join(q.goals or []) or "—"
    rows = [
        ("Name", q.full_name),
        ("Email", q.work_email),
        ("Company", q.company),
        ("Role", q.role),
        ("Catalog coverage", coverage),
        ("Catalog size", q.catalog_size or "—"),
        ("Current management", q.current_management or "—"),
        ("Goals", goals),
        ("Timeline", q.timeline or "—"),
        ("Reason now", q.reason_now or "—"),
        ("Demo notes", q.demo_notes or "—"),
        ("Submitted", q.created_at.strftime("%Y-%m-%d %H:%M UTC") if q.created_at else "—"),
    ]
    row_html = "".join(
        f"""<tr>
          <td style="padding:8px 12px;font-weight:600;color:#3D4A44;white-space:nowrap;
                     border-bottom:1px solid #eef1ec;vertical-align:top;">{label}</td>
          <td style="padding:8px 12px;color:#1D1D1F;border-bottom:1px solid #eef1ec;">{value}</td>
        </tr>"""
        for label, value in rows
    )
    return f"""<!DOCTYPE html><html><body style="margin:0;padding:0;background:#F8F9F7;
      font-family:-apple-system,Inter,sans-serif;">
      <div style="max-width:600px;margin:32px auto;background:#fff;border-radius:8px;
                  border:1px solid #d4ddd8;overflow:hidden;">
        <div style="background:linear-gradient(135deg,#5B8A72 0%,#7BA594 100%);
                    padding:24px 32px;">
          <img src="https://cadence-ci.com/assets/email/cadence-logo-white.png"
               alt="Cadence" height="32" style="display:block;" />
        </div>
        <div style="padding:28px 32px;">
          <h2 style="margin:0 0 4px;color:#1D1D1F;font-size:18px;font-weight:700;">
            New demo qualification submission</h2>
          <p style="margin:0 0 20px;color:#7A8580;font-size:14px;">
            Review in the admin panel or reply directly to the submitter.</p>
          <table style="width:100%;border-collapse:collapse;font-size:14px;">
            {row_html}
          </table>
        </div>
      </div>
    </body></html>"""


@router.post("/api/qualify", summary="Submit demo qualification form")
def submit_qualification(payload: QualifyRequest, db: Session = Depends(get_db)):
    if payload.honeypot:
        return {"ok": True}

    record = DemoQualification(
        full_name=payload.full_name,
        work_email=payload.work_email,
        company=payload.company,
        role=payload.role,
        catalog_coverage=payload.catalog_coverage or [],
        catalog_size=payload.catalog_size,
        current_management=payload.current_management,
        goals=payload.goals or [],
        reason_now=payload.reason_now,
        timeline=payload.timeline,
        demo_notes=payload.demo_notes,
        created_at=datetime.utcnow(),
    )
    db.add(record)
    db.commit()
    db.refresh(record)

    try:
        provider = get_email_provider()
        provider.send_email(
            to=NOTIFY_EMAIL,
            subject=f"Demo request: {record.full_name} — {record.company}",
            html_body=_notification_html(record),
            reply_to=record.work_email,
        )
    except Exception as e:
        logger.warning(f"Demo qualification notification email failed: {e}")

    return {"ok": True, "id": record.id}


@admin_router.get("/qualifications/export", summary="Export demo qualifications CSV")
def export_qualifications_csv(
    db: Session = Depends(get_db),
    _: object = Depends(get_current_super_admin),
):
    records = (
        db.query(DemoQualification)
        .order_by(DemoQualification.created_at.desc())
        .all()
    )
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow([
        "ID", "Full Name", "Work Email", "Company", "Role",
        "Catalog Coverage", "Catalog Size", "Current Management",
        "Goals", "Reason Now", "Timeline", "Demo Notes", "Submitted At",
    ])
    for r in records:
        writer.writerow([
            r.id, r.full_name, r.work_email, r.company, r.role,
            "; ".join(r.catalog_coverage or []),
            r.catalog_size or "",
            r.current_management or "",
            "; ".join(r.goals or []),
            r.reason_now or "",
            r.timeline or "",
            r.demo_notes or "",
            r.created_at.strftime("%Y-%m-%d %H:%M") if r.created_at else "",
        ])
    buf.seek(0)
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=demo-qualifications.csv"},
    )


@admin_router.get("/qualifications", summary="List demo qualification submissions")
def list_qualifications(
    db: Session = Depends(get_db),
    _: object = Depends(get_current_super_admin),
):
    records = (
        db.query(DemoQualification)
        .order_by(DemoQualification.created_at.desc())
        .all()
    )
    return [
        {
            "id": r.id,
            "full_name": r.full_name,
            "work_email": r.work_email,
            "company": r.company,
            "role": r.role,
            "catalog_coverage": r.catalog_coverage,
            "catalog_size": r.catalog_size,
            "current_management": r.current_management,
            "goals": r.goals,
            "reason_now": r.reason_now,
            "timeline": r.timeline,
            "demo_notes": r.demo_notes,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in records
    ]


@admin_router.get("/qualifications/{qualification_id}", summary="Get a single qualification")
def get_qualification(
    qualification_id: int,
    db: Session = Depends(get_db),
    _: object = Depends(get_current_super_admin),
):
    record = db.query(DemoQualification).filter(DemoQualification.id == qualification_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Not found")
    return {
        "id": record.id,
        "full_name": record.full_name,
        "work_email": record.work_email,
        "company": record.company,
        "role": record.role,
        "catalog_coverage": record.catalog_coverage,
        "catalog_size": record.catalog_size,
        "current_management": record.current_management,
        "goals": record.goals,
        "reason_now": record.reason_now,
        "timeline": record.timeline,
        "demo_notes": record.demo_notes,
        "created_at": record.created_at.isoformat() if record.created_at else None,
    }
