from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from sqlalchemy.orm import Session
from sqlalchemy import func, or_
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
import io
import csv
import json
from ..models import (
    get_db, Song, Work, WorkCredit, SongCredit, Creator, CreativeContact,
    OrganizationMember, User, Organization
)
from ..utils.auth import get_current_user

router = APIRouter(prefix="/api/registration-reports", tags=["registration-reports"])


def verify_org_access(user: User, org_id: int, db: Session):
    membership = db.query(OrganizationMember).filter(
        OrganizationMember.user_id == user.id,
        OrganizationMember.organization_id == org_id
    ).first()
    if not membership:
        raise HTTPException(status_code=403, detail="Not authorized")
    return membership


def get_publisher_info(creator, db):
    if creator.publisher_contact_id:
        contact = db.query(CreativeContact).filter(CreativeContact.id == creator.publisher_contact_id).first()
        if contact:
            return {
                "name": contact.display_name,
                "company": contact.publisher_name,
                "pro": contact.publisher_pro or contact.pro,
                "ipi": contact.publisher_ipi or contact.ipi
            }
    if creator.publisher_name:
        return {"name": creator.publisher_name, "company": None, "pro": None, "ipi": None}
    return None


def get_admin_info(creator, db):
    if creator.admin_contact_id:
        contact = db.query(CreativeContact).filter(CreativeContact.id == creator.admin_contact_id).first()
        if contact:
            return {
                "id": contact.id,
                "name": contact.display_name,
                "email": contact.email,
                "company": contact.publisher_name,
                "pro": contact.pro,
                "ipi": contact.ipi
            }
    return None


def get_creators_for_work(work_id, db):
    credits = db.query(WorkCredit).filter(WorkCredit.work_id == work_id).all()
    creator_ids = set()
    for c in credits:
        if c.creator_id:
            creator_ids.add(c.creator_id)
    creators = []
    for cid in creator_ids:
        creator = db.query(Creator).filter(Creator.id == cid).first()
        if creator:
            creators.append({"id": creator.id, "name": creator.display_name})
    return creators


def get_creators_for_song(song_id, db):
    credits = db.query(SongCredit).filter(SongCredit.song_id == song_id).all()
    creator_ids = set()
    for c in credits:
        if c.creator_id:
            creator_ids.add(c.creator_id)
    creators = []
    for cid in creator_ids:
        creator = db.query(Creator).filter(Creator.id == cid).first()
        if creator:
            creators.append({"id": creator.id, "name": creator.display_name})
    return creators


def build_work_registration_data(work, db):
    credits = db.query(WorkCredit).filter(WorkCredit.work_id == work.id).all()
    writers = []
    validation_issues = []

    for credit in credits:
        creator = db.query(Creator).filter(Creator.id == credit.creator_id).first()
        if not creator:
            continue

        writer_data = {
            "name": creator.display_name,
            "legal_name": creator.legal_name,
            "role": credit.role,
            "share": credit.share_percentage,
            "pro": creator.primary_pro,
            "ipi": creator.primary_ipi,
            "publisher": get_publisher_info(creator, db),
            "administrator": get_admin_info(creator, db)
        }
        writers.append(writer_data)

        if not creator.primary_ipi:
            validation_issues.append(f"Missing IPI for {creator.display_name}")
        if not creator.primary_pro:
            validation_issues.append(f"Missing PRO for {creator.display_name}")
        if credit.share_percentage is None:
            validation_issues.append(f"Missing share % for {creator.display_name}")

    total_share = sum(w["share"] or 0 for w in writers)
    if total_share > 0 and abs(total_share - 100) > 0.01:
        validation_issues.append(f"Writer shares total {total_share}%, expected 100%")
    if not writers:
        validation_issues.append("No writers credited")
    if not work.iswc:
        validation_issues.append("Missing ISWC")

    creators_list = get_creators_for_work(work.id, db)

    return {
        "id": work.id,
        "work_id": work.id,
        "title": work.title,
        "iswc": work.iswc,
        "work_type": work.work_type,
        "alternate_titles": work.alternative_titles,
        "is_registered_with_pro": bool(getattr(work, 'is_registered_with_pro', False)),
        "creators": creators_list,
        "writers": writers,
        "total_share": total_share,
        "validation_issues": validation_issues,
        "is_valid": len(validation_issues) == 0
    }


def build_song_registration_data(song, db):
    credits = db.query(SongCredit).filter(SongCredit.song_id == song.id).all()
    writers = []
    validation_issues = []

    for credit in credits:
        creator = db.query(Creator).filter(Creator.id == credit.creator_id).first()
        if not creator:
            continue

        writer_data = {
            "name": creator.display_name,
            "legal_name": creator.legal_name,
            "role": credit.role,
            "share": credit.share_percentage,
            "pro": creator.primary_pro,
            "ipi": creator.primary_ipi,
            "publisher": get_publisher_info(creator, db),
            "administrator": get_admin_info(creator, db)
        }
        writers.append(writer_data)

        if not creator.primary_ipi:
            validation_issues.append(f"Missing IPI for {creator.display_name}")
        if not creator.primary_pro:
            validation_issues.append(f"Missing PRO for {creator.display_name}")
        if credit.share_percentage is None:
            validation_issues.append(f"Missing share % for {creator.display_name}")

    total_share = sum(w["share"] or 0 for w in writers)
    if total_share > 0 and abs(total_share - 100) > 0.01:
        validation_issues.append(f"Writer shares total {total_share}%, expected 100%")
    if not writers:
        validation_issues.append("No writers credited")
    if not song.isrc:
        validation_issues.append("Missing ISRC")

    creators_list = get_creators_for_song(song.id, db)

    return {
        "id": song.id,
        "song_id": song.id,
        "title": song.title,
        "primary_artist": song.primary_artist,
        "isrc": song.isrc,
        "iswc": song.iswc,
        "release_date": str(song.release_date) if song.release_date else None,
        "is_registered_with_pro": bool(getattr(song, 'is_registered_with_pro', False)),
        "creators": creators_list,
        "writers": writers,
        "total_share": total_share,
        "validation_issues": validation_issues,
        "is_valid": len(validation_issues) == 0
    }


@router.get("/org/{org_id}/works")
def get_work_registration_report(
    org_id: int,
    creator_id: Optional[int] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    verify_org_access(current_user, org_id, db)

    query = db.query(Work).filter(Work.organization_id == org_id)
    if creator_id:
        work_ids = db.query(WorkCredit.work_id).filter(WorkCredit.creator_id == creator_id).subquery()
        query = query.filter(Work.id.in_(work_ids))
    if status == "outstanding":
        query = query.filter(or_(Work.is_registered_with_pro == False, Work.is_registered_with_pro.is_(None)))
    elif status == "registered":
        query = query.filter(Work.is_registered_with_pro == True)

    works = query.all()
    report_items = [build_work_registration_data(w, db) for w in works]

    valid_count = sum(1 for item in report_items if item["is_valid"])
    total_count = len(report_items)
    outstanding_count = sum(1 for item in report_items if not item["is_registered_with_pro"])

    return {
        "type": "works",
        "total": total_count,
        "valid": valid_count,
        "invalid": total_count - valid_count,
        "outstanding": outstanding_count,
        "registered": total_count - outstanding_count,
        "items": report_items
    }


@router.get("/org/{org_id}/songs")
def get_song_registration_report(
    org_id: int,
    creator_id: Optional[int] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    verify_org_access(current_user, org_id, db)

    query = db.query(Song).filter(Song.organization_id == org_id)
    if creator_id:
        song_ids = db.query(SongCredit.song_id).filter(SongCredit.creator_id == creator_id).subquery()
        query = query.filter(Song.id.in_(song_ids))
    if status == "outstanding":
        query = query.filter(or_(Song.is_registered_with_pro == False, Song.is_registered_with_pro.is_(None)))
    elif status == "registered":
        query = query.filter(Song.is_registered_with_pro == True)

    songs = query.all()
    report_items = [build_song_registration_data(s, db) for s in songs]

    valid_count = sum(1 for item in report_items if item["is_valid"])
    total_count = len(report_items)
    outstanding_count = sum(1 for item in report_items if not item["is_registered_with_pro"])

    return {
        "type": "songs",
        "total": total_count,
        "valid": valid_count,
        "invalid": total_count - valid_count,
        "outstanding": outstanding_count,
        "registered": total_count - outstanding_count,
        "items": report_items
    }


@router.get("/org/{org_id}/creators")
def get_creators_list(
    org_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    verify_org_access(current_user, org_id, db)
    creators = db.query(Creator).filter(Creator.organization_id == org_id).order_by(Creator.display_name).all()
    return [{"id": c.id, "name": c.display_name, "admin_contact_id": c.admin_contact_id} for c in creators]


class SelectedItemsRequest(BaseModel):
    asset_type: str = "works"
    item_ids: List[int] = []


@router.post("/org/{org_id}/export/pdf")
def export_selected_registration_pdf(
    org_id: int,
    request: SelectedItemsRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    verify_org_access(current_user, org_id, db)

    try:
        from reportlab.lib.pagesizes import letter, landscape
        from reportlab.lib import colors
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, HRFlowable
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import inch
    except ImportError:
        raise HTTPException(status_code=500, detail="PDF generation not available")

    org = db.query(Organization).filter(Organization.id == org_id).first()
    org_name = org.name if org else "Organization"

    items = []
    if request.asset_type == "works":
        if request.item_ids:
            works = db.query(Work).filter(Work.id.in_(request.item_ids), Work.organization_id == org_id).all()
        else:
            works = db.query(Work).filter(Work.organization_id == org_id, or_(Work.is_registered_with_pro == False, Work.is_registered_with_pro.is_(None))).all()
        items = [build_work_registration_data(w, db) for w in works]
    else:
        if request.item_ids:
            songs = db.query(Song).filter(Song.id.in_(request.item_ids), Song.organization_id == org_id).all()
        else:
            songs = db.query(Song).filter(Song.organization_id == org_id, or_(Song.is_registered_with_pro == False, Song.is_registered_with_pro.is_(None))).all()
        items = [build_song_registration_data(s, db) for s in songs]

    buffer = _generate_pdf(items, request.asset_type, org_name)

    filename = f"Registration_Report_{request.asset_type}_{org_name}_{datetime.utcnow().strftime('%Y%m%d')}.pdf"
    return Response(
        content=buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )


@router.get("/org/{org_id}/export/csv")
def export_registration_csv(
    org_id: int,
    asset_type: str = "works",
    creator_id: Optional[int] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    verify_org_access(current_user, org_id, db)

    output = io.StringIO()
    writer = csv.writer(output)

    if asset_type == "works":
        writer.writerow([
            "Work Title", "ISWC", "Work Type", "PRO Registered", "Alternate Titles",
            "Writer Name", "Writer Legal Name", "Writer Role", "Share %",
            "Writer PRO", "Writer IPI",
            "Publisher Name", "Publisher PRO", "Publisher IPI",
            "Administrator Name", "Admin PRO", "Admin IPI",
            "Validation Status"
        ])
        query = db.query(Work).filter(Work.organization_id == org_id)
        if creator_id:
            work_ids = db.query(WorkCredit.work_id).filter(WorkCredit.creator_id == creator_id).subquery()
            query = query.filter(Work.id.in_(work_ids))
        if status == "outstanding":
            query = query.filter(or_(Work.is_registered_with_pro == False, Work.is_registered_with_pro.is_(None)))
        elif status == "registered":
            query = query.filter(Work.is_registered_with_pro == True)
        works = query.all()
        for work in works:
            data = build_work_registration_data(work, db)
            if not data["writers"]:
                writer.writerow([
                    data["title"], data["iswc"] or "", data["work_type"] or "",
                    "Yes" if data["is_registered_with_pro"] else "No",
                    ", ".join(data["alternate_titles"] or []),
                    "", "", "", "", "", "", "", "", "", "", "", "", "",
                    "INVALID: " + "; ".join(data["validation_issues"])
                ])
            for w in data["writers"]:
                pub = w.get("publisher") or {}
                admin = w.get("administrator") or {}
                writer.writerow([
                    data["title"], data["iswc"] or "", data["work_type"] or "",
                    "Yes" if data["is_registered_with_pro"] else "No",
                    ", ".join(data["alternate_titles"] or []),
                    w["name"], w.get("legal_name") or "", w["role"], w.get("share") or "",
                    w.get("pro") or "", w.get("ipi") or "",
                    pub.get("name") or "", pub.get("pro") or "", pub.get("ipi") or "",
                    admin.get("name") or "", admin.get("pro") or "", admin.get("ipi") or "",
                    "Valid" if data["is_valid"] else "Issues: " + "; ".join(data["validation_issues"])
                ])
    else:
        writer.writerow([
            "Song Title", "Primary Artist", "ISRC", "ISWC", "PRO Registered", "Release Date",
            "Writer Name", "Writer Legal Name", "Writer Role", "Share %",
            "Writer PRO", "Writer IPI",
            "Publisher Name", "Publisher PRO", "Publisher IPI",
            "Administrator Name", "Admin PRO", "Admin IPI",
            "Validation Status"
        ])
        query = db.query(Song).filter(Song.organization_id == org_id)
        if creator_id:
            song_ids = db.query(SongCredit.song_id).filter(SongCredit.creator_id == creator_id).subquery()
            query = query.filter(Song.id.in_(song_ids))
        if status == "outstanding":
            query = query.filter(or_(Song.is_registered_with_pro == False, Song.is_registered_with_pro.is_(None)))
        elif status == "registered":
            query = query.filter(Song.is_registered_with_pro == True)
        songs = query.all()
        for song in songs:
            data = build_song_registration_data(song, db)
            if not data["writers"]:
                writer.writerow([
                    data["title"], data.get("primary_artist") or "", data["isrc"] or "",
                    data["iswc"] or "",
                    "Yes" if data["is_registered_with_pro"] else "No",
                    data.get("release_date") or "",
                    "", "", "", "", "", "", "", "", "", "", "", "", "",
                    "INVALID: " + "; ".join(data["validation_issues"])
                ])
            for w in data["writers"]:
                pub = w.get("publisher") or {}
                admin = w.get("administrator") or {}
                writer.writerow([
                    data["title"], data.get("primary_artist") or "", data["isrc"] or "",
                    data["iswc"] or "",
                    "Yes" if data["is_registered_with_pro"] else "No",
                    data.get("release_date") or "",
                    w["name"], w.get("legal_name") or "", w["role"], w.get("share") or "",
                    w.get("pro") or "", w.get("ipi") or "",
                    pub.get("name") or "", pub.get("pro") or "", pub.get("ipi") or "",
                    admin.get("name") or "", admin.get("pro") or "", admin.get("ipi") or "",
                    "Valid" if data["is_valid"] else "Issues: " + "; ".join(data["validation_issues"])
                ])

    org = db.query(Organization).filter(Organization.id == org_id).first()
    org_name = org.name if org else "Organization"
    filename = f"Registration_Report_{asset_type}_{org_name}_{datetime.utcnow().strftime('%Y%m%d')}.csv"

    output.seek(0)
    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )


@router.get("/org/{org_id}/export/pdf")
def export_registration_pdf_get(
    org_id: int,
    asset_type: str = "works",
    creator_id: Optional[int] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    verify_org_access(current_user, org_id, db)

    try:
        from reportlab.lib.pagesizes import letter, landscape
        from reportlab.lib import colors
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, HRFlowable
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import inch
    except ImportError:
        raise HTTPException(status_code=500, detail="PDF generation not available")

    org = db.query(Organization).filter(Organization.id == org_id).first()
    org_name = org.name if org else "Organization"

    if asset_type == "works":
        query = db.query(Work).filter(Work.organization_id == org_id)
        if creator_id:
            work_ids = db.query(WorkCredit.work_id).filter(WorkCredit.creator_id == creator_id).subquery()
            query = query.filter(Work.id.in_(work_ids))
        if status == "outstanding":
            query = query.filter(or_(Work.is_registered_with_pro == False, Work.is_registered_with_pro.is_(None)))
        elif status == "registered":
            query = query.filter(Work.is_registered_with_pro == True)
        items = [build_work_registration_data(w, db) for w in query.all()]
    else:
        query = db.query(Song).filter(Song.organization_id == org_id)
        if creator_id:
            song_ids = db.query(SongCredit.song_id).filter(SongCredit.creator_id == creator_id).subquery()
            query = query.filter(Song.id.in_(song_ids))
        if status == "outstanding":
            query = query.filter(or_(Song.is_registered_with_pro == False, Song.is_registered_with_pro.is_(None)))
        elif status == "registered":
            query = query.filter(Song.is_registered_with_pro == True)
        items = [build_song_registration_data(s, db) for s in query.all()]

    buffer = _generate_pdf(items, asset_type, org_name)
    filename = f"Registration_Report_{asset_type}_{org_name}_{datetime.utcnow().strftime('%Y%m%d')}.pdf"
    return Response(
        content=buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )


class EmailReportRequest(BaseModel):
    asset_type: str = "works"
    item_ids: List[int] = []
    recipient_email: Optional[str] = None
    recipient_name: Optional[str] = None
    admin_contact_id: Optional[int] = None
    message: Optional[str] = None


@router.post("/org/{org_id}/send-email")
def send_registration_report_email(
    org_id: int,
    request: EmailReportRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    verify_org_access(current_user, org_id, db)

    try:
        from reportlab.lib.pagesizes import letter, landscape
    except ImportError:
        raise HTTPException(status_code=500, detail="PDF generation not available")

    org = db.query(Organization).filter(Organization.id == org_id).first()
    org_name = org.name if org else "Organization"

    to_email = request.recipient_email
    to_name = request.recipient_name or "Admin"

    if request.admin_contact_id and not to_email:
        contact = db.query(CreativeContact).filter(
            CreativeContact.id == request.admin_contact_id,
            CreativeContact.organization_id == org_id
        ).first()
        if contact and contact.email:
            to_email = contact.email
            to_name = contact.display_name or to_name
        else:
            raise HTTPException(status_code=400, detail="Admin contact has no email address")

    if not to_email:
        raise HTTPException(status_code=400, detail="No recipient email provided")

    items = []
    if request.asset_type == "works":
        if request.item_ids:
            works = db.query(Work).filter(Work.id.in_(request.item_ids), Work.organization_id == org_id).all()
        else:
            works = db.query(Work).filter(Work.organization_id == org_id, or_(Work.is_registered_with_pro == False, Work.is_registered_with_pro.is_(None))).all()
        items = [build_work_registration_data(w, db) for w in works]
    else:
        if request.item_ids:
            songs = db.query(Song).filter(Song.id.in_(request.item_ids), Song.organization_id == org_id).all()
        else:
            songs = db.query(Song).filter(Song.organization_id == org_id, or_(Song.is_registered_with_pro == False, Song.is_registered_with_pro.is_(None))).all()
        items = [build_song_registration_data(s, db) for s in songs]

    if not items:
        raise HTTPException(status_code=400, detail="No items to include in the report")

    pdf_bytes = _generate_pdf(items, request.asset_type, org_name)

    user_name = current_user.full_name or current_user.username
    custom_msg = request.message or ""
    item_count = len(items)

    html_body = f"""
    <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 600px; margin: 0 auto;">
        <div style="background: linear-gradient(135deg, #5B8A72, #7A8580); padding: 24px 32px; border-radius: 12px 12px 0 0;">
            <h1 style="color: white; margin: 0; font-size: 22px; font-weight: 600;">Registration Report</h1>
            <p style="color: rgba(255,255,255,0.8); margin: 8px 0 0; font-size: 14px;">PRO Registration — {org_name}</p>
        </div>
        <div style="background: #F5F7F4; padding: 24px 32px; border: 1px solid #EEF1EC; border-top: none; border-radius: 0 0 12px 12px;">
            <p style="color: #3D4A44; font-size: 15px; line-height: 1.6;">
                Hi {to_name},
            </p>
            <p style="color: #3D4A44; font-size: 15px; line-height: 1.6;">
                {user_name} has sent you a PRO registration report containing <strong>{item_count} {request.asset_type}</strong> that need to be registered.
            </p>
            {"<p style='color: #3D4A44; font-size: 15px; line-height: 1.6; background: white; padding: 16px; border-radius: 8px; border-left: 3px solid #5B8A72;'>" + custom_msg + "</p>" if custom_msg else ""}
            <p style="color: #3D4A44; font-size: 15px; line-height: 1.6;">
                Please find the attached branded PDF report with all details needed for registration.
            </p>
            <div style="margin-top: 20px; padding-top: 16px; border-top: 1px solid #E5E7EB;">
                <p style="color: #7A8580; font-size: 12px; margin: 0;">
                    Sent via Rythm — Catalog Intelligence
                </p>
            </div>
        </div>
    </div>
    """

    import base64
    try:
        from ..services.email_provider import get_email_provider
        provider = get_email_provider()

        import resend
        from ..services.email_provider import _get_resend_credentials
        credentials = _get_resend_credentials()
        resend.api_key = credentials["api_key"]
        connector_from = credentials.get("from_email") or "onboarding@resend.dev"

        filename = f"Registration_Report_{request.asset_type}_{org_name}_{datetime.utcnow().strftime('%Y%m%d')}.pdf"
        pdf_b64 = base64.b64encode(pdf_bytes).decode('utf-8')

        result = resend.Emails.send({
            "from": connector_from,
            "to": [to_email],
            "subject": f"PRO Registration Report — {org_name} ({item_count} {request.asset_type})",
            "html": html_body,
            "attachments": [
                {
                    "filename": filename,
                    "content": pdf_b64,
                }
            ]
        })

        return {"success": True, "message": f"Report sent to {to_email}", "email_id": str(result)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to send email: {str(e)}")


def _generate_pdf(items, asset_type, org_name):
    from reportlab.lib.pagesizes import letter, landscape
    from reportlab.lib import colors
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, HRFlowable
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=landscape(letter), topMargin=0.5*inch, bottomMargin=0.5*inch)
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle('CustomTitle', parent=styles['Title'], fontSize=18, textColor=colors.HexColor('#3D4A44'))
    subtitle_style = ParagraphStyle('Subtitle', parent=styles['Normal'], fontSize=10, textColor=colors.HexColor('#7A8580'))
    section_style = ParagraphStyle('Section', parent=styles['Heading2'], fontSize=13, textColor=colors.HexColor('#5B8A72'), spaceAfter=6)
    cell_style = ParagraphStyle('Cell', parent=styles['Normal'], fontSize=7, leading=9)
    header_cell_style = ParagraphStyle('HeaderCell', parent=styles['Normal'], fontSize=7, leading=9, textColor=colors.white)

    elements = []
    elements.append(Paragraph(f"Registration Report — {asset_type.title()}", title_style))
    elements.append(Paragraph(f"{org_name} | Generated {datetime.utcnow().strftime('%B %d, %Y')}", subtitle_style))

    valid_count = sum(1 for item in items if item["is_valid"])
    outstanding_count = sum(1 for item in items if not item.get("is_registered_with_pro", False))
    elements.append(Spacer(1, 8))
    elements.append(Paragraph(f"Total: {len(items)} | Ready: {valid_count} | Outstanding: {outstanding_count} | Needs Attention: {len(items) - valid_count}", subtitle_style))
    elements.append(Spacer(1, 12))

    sage = colors.HexColor('#5B8A72')
    light_sage = colors.HexColor('#EEF1EC')

    for item in items:
        title = item.get("title", "Untitled")
        identifier = item.get("iswc") or item.get("isrc") or "—"
        reg_status = "Registered" if item.get("is_registered_with_pro") else "Outstanding"
        reg_color = sage if item.get("is_registered_with_pro") else colors.HexColor('#DC2626')
        status = "Ready" if item["is_valid"] else "Needs Attention"
        status_color = sage if item["is_valid"] else colors.HexColor('#D97706')

        elements.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor('#E5E7EB')))
        elements.append(Spacer(1, 4))
        elements.append(Paragraph(
            f'<b>{title}</b> <font color="#7A8580">({identifier})</font> — '
            f'<font color="{reg_color}">{reg_status}</font> | '
            f'<font color="{status_color}">{status}</font>',
            section_style
        ))

        if item.get("writers"):
            header = [
                Paragraph("<b>Writer</b>", header_cell_style),
                Paragraph("<b>Legal Name</b>", header_cell_style),
                Paragraph("<b>Role</b>", header_cell_style),
                Paragraph("<b>Share %</b>", header_cell_style),
                Paragraph("<b>PRO</b>", header_cell_style),
                Paragraph("<b>IPI</b>", header_cell_style),
                Paragraph("<b>Publisher</b>", header_cell_style),
                Paragraph("<b>Pub PRO</b>", header_cell_style),
                Paragraph("<b>Pub IPI</b>", header_cell_style),
            ]
            data = [header]
            for w in item["writers"]:
                pub = w.get("publisher") or {}
                row = [
                    Paragraph(w.get("name") or "", cell_style),
                    Paragraph(w.get("legal_name") or "", cell_style),
                    Paragraph(w.get("role") or "", cell_style),
                    Paragraph(str(w.get("share") or ""), cell_style),
                    Paragraph(w.get("pro") or "", cell_style),
                    Paragraph(w.get("ipi") or "", cell_style),
                    Paragraph(pub.get("name") or "", cell_style),
                    Paragraph(pub.get("pro") or "", cell_style),
                    Paragraph(pub.get("ipi") or "", cell_style),
                ]
                data.append(row)

            col_widths = [1.3*inch, 1.3*inch, 0.8*inch, 0.6*inch, 0.7*inch, 1.0*inch, 1.3*inch, 0.7*inch, 1.0*inch]
            table = Table(data, colWidths=col_widths)
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), sage),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('FONTSIZE', (0, 0), (-1, -1), 7),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, light_sage]),
                ('GRID', (0, 0), (-1, -1), 0.3, colors.HexColor('#D1D5DB')),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('TOPPADDING', (0, 0), (-1, -1), 3),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
            ]))
            elements.append(table)

        if item.get("validation_issues"):
            issues_text = " | ".join(item["validation_issues"])
            elements.append(Spacer(1, 2))
            elements.append(Paragraph(f'<font color="#D97706" size="7">Issues: {issues_text}</font>', styles['Normal']))

        elements.append(Spacer(1, 8))

    if not items:
        elements.append(Paragraph("No items found for this report.", subtitle_style))

    elements.append(Spacer(1, 20))
    elements.append(HRFlowable(width="100%", thickness=1, color=sage))
    elements.append(Spacer(1, 6))
    footer_style = ParagraphStyle('Footer', parent=styles['Normal'], fontSize=8, textColor=colors.HexColor('#7A8580'), alignment=1)
    elements.append(Paragraph("Rythm — Catalog Intelligence | Confidential", footer_style))

    doc.build(elements)
    buffer.seek(0)
    return buffer.getvalue()
