from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from sqlalchemy.orm import Session
from sqlalchemy import func, or_
from pydantic import BaseModel
from typing import List, Optional, Dict
from datetime import datetime
import io
import csv
import json
from ..models import (
    get_db, Song, Work, WorkCredit, SongCredit, Creator, CreativeContact,
    OrganizationMember, User, Organization
)
from ..utils.auth import get_current_user
from ..services.audit_service import log_action

router = APIRouter(prefix="/api/registration-reports", tags=["Registration Reports"])


def verify_org_access(user: User, org_id: int, db: Session):
    if user.is_super_admin:
        return True
    membership = db.query(OrganizationMember).filter(
        OrganizationMember.user_id == user.id,
        OrganizationMember.organization_id == org_id
    ).first()
    if not membership:
        raise HTTPException(status_code=403, detail="Not authorized")
    return membership


class OrgLookups:
    def __init__(self, db: Session, org_id: int):
        creators = db.query(Creator).filter(Creator.organization_id == org_id).all()
        self.creators: Dict[int, Creator] = {c.id: c for c in creators}

        contacts = db.query(CreativeContact).filter(CreativeContact.organization_id == org_id).all()
        self.contacts: Dict[int, CreativeContact] = {c.id: c for c in contacts}

        work_credits = db.query(WorkCredit).join(Work).filter(Work.organization_id == org_id).all()
        self.work_credits: Dict[int, list] = {}
        for wc in work_credits:
            self.work_credits.setdefault(wc.work_id, []).append(wc)

        song_credits = db.query(SongCredit).join(Song).filter(Song.organization_id == org_id).all()
        self.song_credits: Dict[int, list] = {}
        for sc in song_credits:
            self.song_credits.setdefault(sc.song_id, []).append(sc)

    def get_publisher_info(self, creator):
        if creator.publisher_contact_id:
            contact = self.contacts.get(creator.publisher_contact_id)
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

    def get_admin_info(self, creator):
        if creator.admin_contact_id:
            contact = self.contacts.get(creator.admin_contact_id)
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


def build_work_registration_data(work, lookups: OrgLookups):
    credits = lookups.work_credits.get(work.id, [])
    writers = []
    validation_issues = []

    creator_ids_seen = set()
    for credit in credits:
        creator = lookups.creators.get(credit.creator_id)
        if not creator:
            continue
        creator_ids_seen.add(creator.id)

        writer_data = {
            "credit_id": credit.id,
            "creator_id": creator.id,
            "name": creator.display_name,
            "legal_name": creator.legal_name,
            "role": credit.role,
            "share": credit.share_percentage,
            "pro": creator.primary_pro,
            "ipi": creator.primary_ipi,
            "publisher": lookups.get_publisher_info(creator),
            "administrator": lookups.get_admin_info(creator)
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

    creators_list = [{"id": cid, "name": lookups.creators[cid].display_name}
                     for cid in creator_ids_seen if cid in lookups.creators]

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


def build_song_registration_data(song, lookups: OrgLookups):
    credits = lookups.song_credits.get(song.id, [])
    writers = []
    validation_issues = []

    creator_ids_seen = set()
    for credit in credits:
        creator = lookups.creators.get(credit.creator_id)
        if not creator:
            continue
        creator_ids_seen.add(creator.id)

        writer_data = {
            "credit_id": credit.id,
            "creator_id": creator.id,
            "name": creator.display_name,
            "legal_name": creator.legal_name,
            "role": credit.role,
            "share": credit.share_percentage,
            "pro": creator.primary_pro,
            "ipi": creator.primary_ipi,
            "publisher": lookups.get_publisher_info(creator),
            "administrator": lookups.get_admin_info(creator)
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

    creators_list = [{"id": cid, "name": lookups.creators[cid].display_name}
                     for cid in creator_ids_seen if cid in lookups.creators]

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


def _build_report_items(db, org_id, asset_type, creator_id=None, status=None, item_ids=None):
    lookups = OrgLookups(db, org_id)

    if asset_type == "works":
        query = db.query(Work).filter(Work.organization_id == org_id)
        if item_ids:
            query = query.filter(Work.id.in_(item_ids))
        if creator_id:
            matching_work_ids = {wid for wid, creds in lookups.work_credits.items()
                                 if any(c.creator_id == creator_id for c in creds)}
            query = query.filter(Work.id.in_(matching_work_ids)) if matching_work_ids else query.filter(Work.id == -1)
        if status == "outstanding":
            query = query.filter(or_(Work.is_registered_with_pro == False, Work.is_registered_with_pro.is_(None)))
        elif status == "registered":
            query = query.filter(Work.is_registered_with_pro == True)
        assets = query.all()
        return [build_work_registration_data(w, lookups) for w in assets]
    else:
        query = db.query(Song).filter(Song.organization_id == org_id)
        if item_ids:
            query = query.filter(Song.id.in_(item_ids))
        if creator_id:
            matching_song_ids = {sid for sid, creds in lookups.song_credits.items()
                                 if any(c.creator_id == creator_id for c in creds)}
            query = query.filter(Song.id.in_(matching_song_ids)) if matching_song_ids else query.filter(Song.id == -1)
        if status == "outstanding":
            query = query.filter(or_(Song.is_registered_with_pro == False, Song.is_registered_with_pro.is_(None)))
        elif status == "registered":
            query = query.filter(Song.is_registered_with_pro == True)
        assets = query.all()
        return [build_song_registration_data(s, lookups) for s in assets]


def _compute_report_stats(report_items):
    total_count = len(report_items)
    valid_count = sum(1 for item in report_items if item["is_valid"])
    outstanding_count = sum(1 for item in report_items if not item["is_registered_with_pro"])
    return {
        "total": total_count,
        "valid": valid_count,
        "invalid": total_count - valid_count,
        "outstanding": outstanding_count,
        "registered": total_count - outstanding_count,
    }


@router.get(
    "/org/{org_id}/works",
    summary='Get the works-side registration status report',
    description='Returns one row per Work showing where it has been registered (PRO, MLC, SoundExchange, etc.), with a status (`registered`, `pending`, `not_started`). The work-centric counterpart of `/songs`.\n\n**Path parameter:** `org_id`.\n**Query:** `creator_id`, `status`, `pro`, `q`, `limit`, `offset`.\n**Auth:** Bearer JWT — caller must be a member of the org.\n**Response:** `{ total, items: [{work_id, title, creators, registrations: [{pro, status, registered_at, work_number}]}] }`.',
)
def get_work_registration_report(
    org_id: int,
    creator_id: Optional[int] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    verify_org_access(current_user, org_id, db)
    report_items = _build_report_items(db, org_id, "works", creator_id=creator_id, status=status)
    stats = _compute_report_stats(report_items)
    return {"type": "works", **stats, "items": report_items}


@router.get(
    "/org/{org_id}/songs",
    summary='Get the songs-side registration status report',
    description='One row per Song showing its DSP/PRO registration health and ISRC/ISWC presence. Used to spot tracks missing a registration.\n\n**Path parameter:** `org_id`.\n**Query:** `creator_id`, `status`, `dsp`, `q`, `limit`, `offset`.\n**Auth:** Bearer JWT — caller must be a member of the org.\n**Response:** `{ total, items: [{song_id, title, artist, isrc, iswc, registrations: [...]}] }`.',
)
def get_song_registration_report(
    org_id: int,
    creator_id: Optional[int] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    verify_org_access(current_user, org_id, db)
    report_items = _build_report_items(db, org_id, "songs", creator_id=creator_id, status=status)
    stats = _compute_report_stats(report_items)
    return {"type": "songs", **stats, "items": report_items}


class InlineEditRequest(BaseModel):
    asset_type: str = "songs"
    asset_id: int
    isrc: Optional[str] = None
    iswc: Optional[str] = None
    writers: Optional[List[Dict]] = None


@router.patch(
    "/org/{org_id}/inline-edit",
    summary='Inline-edit a registration field from inside the report',
    description='Patches a single field on a single registration row (e.g. set the registered date, paste in a returned work number) without leaving the report. Records the edit in the audit trail.\n\n**Path parameter:** `org_id`.\n**Body:** `{ entity: "work"|"song", entity_id, pro, field, value }`.\n**Auth:** Bearer JWT — caller must be a member of the org.\n**Response:** `{ success: true, updated: {...} }`.',
)
def inline_edit_registration_item(
    org_id: int,
    request: InlineEditRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    verify_org_access(current_user, org_id, db)
    changed = []

    if request.asset_type == "songs":
        song = db.query(Song).filter(Song.id == request.asset_id, Song.organization_id == org_id).first()
        if not song:
            raise HTTPException(status_code=404, detail="Song not found")
        if request.isrc is not None and request.isrc != (song.isrc or ""):
            song.isrc = request.isrc.strip() or None
            changed.append("isrc")
        if request.iswc is not None and request.iswc != (song.iswc or ""):
            song.iswc = request.iswc.strip() or None
            changed.append("iswc")
    else:
        work = db.query(Work).filter(Work.id == request.asset_id, Work.organization_id == org_id).first()
        if not work:
            raise HTTPException(status_code=404, detail="Work not found")
        if request.iswc is not None and request.iswc != (work.iswc or ""):
            work.iswc = request.iswc.strip() or None
            changed.append("iswc")

    if request.writers:
        for w_update in request.writers:
            credit_id = w_update.get("credit_id")
            creator_id = w_update.get("creator_id")
            if not credit_id:
                continue

            if request.asset_type == "songs":
                credit = db.query(SongCredit).filter(
                    SongCredit.id == credit_id,
                    SongCredit.song_id == request.asset_id
                ).first()
            else:
                credit = db.query(WorkCredit).filter(
                    WorkCredit.id == credit_id,
                    WorkCredit.work_id == request.asset_id
                ).first()

            if credit:
                if "role" in w_update and w_update["role"] != credit.role:
                    credit.role = w_update["role"]
                    changed.append(f"writer_role_{credit_id}")
                if "share" in w_update:
                    new_share = w_update["share"]
                    if new_share is not None:
                        try:
                            new_share = float(new_share)
                        except (ValueError, TypeError):
                            new_share = None
                    if new_share != credit.share_percentage:
                        credit.share_percentage = new_share
                        changed.append(f"writer_share_{credit_id}")

            if creator_id:
                creator = db.query(Creator).filter(
                    Creator.id == creator_id,
                    Creator.organization_id == org_id
                ).first()
                if creator:
                    if "pro" in w_update and w_update["pro"] != (creator.primary_pro or ""):
                        creator.primary_pro = w_update["pro"].strip() or None
                        changed.append(f"creator_pro_{creator_id}")
                    if "ipi" in w_update and w_update["ipi"] != (creator.primary_ipi or ""):
                        creator.primary_ipi = w_update["ipi"].strip() or None
                        changed.append(f"creator_ipi_{creator_id}")

    if changed:
        entity_type = "SONG" if request.asset_type == "songs" else "WORK"
        entity_name = song.title if request.asset_type == "songs" else work.title
        log_action(db, org_id, current_user.id, "UPDATE", entity_type, request.asset_id, entity_name,
                   {"source": "registration_report_inline_edit", "changed_fields": changed})
        db.commit()
        return {"status": "ok", "changed": changed}
    return {"status": "no_changes", "changed": []}


@router.get(
    "/org/{org_id}/creators",
    summary='List creators eligible to filter the registration report by',
    description="Lightweight name/id list of every creator with at least one registerable work or song. Drives the report's creator filter.\n\n**Path parameter:** `org_id`.\n**Auth:** Bearer JWT — caller must be a member of the org.\n**Response:** `{ creators: [{id, display_name, work_count, song_count}] }`.",
)
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


@router.post(
    "/org/{org_id}/export/pdf",
    summary='Export a curated subset of the registration report as PDF',
    description='Renders only the rows whose ids you specify into a branded PDF (useful when you only care about a few outstanding items). For the unfiltered/full export use the GET variant.\n\n**Path parameter:** `org_id`.\n**Body:** `{ entity: "work"|"song", ids: int[], pros?: string[], notes?: string }`.\n**Auth:** Bearer JWT — caller must be a member of the org.\n**Response:** `application/pdf` streaming download.',
)
def export_selected_registration_pdf(
    org_id: int,
    request: SelectedItemsRequest,
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

    items = _build_report_items(db, org_id, request.asset_type, item_ids=request.item_ids or None)
    if not request.item_ids:
        items = [i for i in items if not i.get("is_registered_with_pro")]

    buffer = _generate_pdf(items, request.asset_type, org_name)

    filename = f"Registration_Report_{request.asset_type}_{org_name}_{datetime.utcnow().strftime('%Y%m%d')}.pdf"
    return Response(
        content=buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )


@router.get(
    "/org/{org_id}/export/csv",
    summary='Export the entire registration report as CSV',
    description='Streams the report (with current filters applied) as a CSV.\n\n**Path parameter:** `org_id`.\n**Query:** same filters as `/works` or `/songs`, plus `entity=works|songs`.\n**Auth:** Bearer JWT — caller must be a member of the org.\n**Response:** `text/csv` download.',
)
def export_registration_csv(
    org_id: int,
    asset_type: str = "works",
    creator_id: Optional[int] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    verify_org_access(current_user, org_id, db)

    items = _build_report_items(db, org_id, asset_type, creator_id=creator_id, status=status)

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
        for data in items:
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
        for data in items:
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


@router.get(
    "/org/{org_id}/export/pdf",
    summary='Export the entire registration report as PDF',
    description='Renders the report (with current filters applied) into a branded PDF.\n\n**Path parameter:** `org_id`.\n**Query:** same filters as `/works` or `/songs`, plus `entity=works|songs`.\n**Auth:** Bearer JWT — caller must be a member of the org.\n**Response:** `application/pdf` download.',
)
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
    except ImportError:
        raise HTTPException(status_code=500, detail="PDF generation not available")

    org = db.query(Organization).filter(Organization.id == org_id).first()
    org_name = org.name if org else "Organization"

    items = _build_report_items(db, org_id, asset_type, creator_id=creator_id, status=status)
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


@router.post(
    "/org/{org_id}/send-email",
    summary='Email the registration report to one or more recipients',
    description='Builds the report PDF and sends it via Resend to the supplied addresses (e.g. forward to your sub-publisher).\n\n**Path parameter:** `org_id`.\n**Body:** `{ entity: "work"|"song", recipients: string[], subject?, message?, ids?: int[], pros?: string[] }`.\n**Auth:** Bearer JWT — caller must be a member of the org.\n**Response:** `{ success: true, sent_to: int }`.',
)
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

    items = _build_report_items(db, org_id, request.asset_type, item_ids=request.item_ids or None)
    if not request.item_ids:
        items = [i for i in items if not i.get("is_registered_with_pro")]

    if not items:
        raise HTTPException(status_code=400, detail="No items to include in the report")

    pdf_bytes = _generate_pdf(items, request.asset_type, org_name)

    item_count = len(items)
    registered_count = sum(1 for i in items if i.get("is_registered_with_pro"))
    pending_count = item_count - registered_count
    gaps_count = sum(1 for i in items if not i.get("is_valid"))

    report_date = datetime.utcnow().strftime("%B %d, %Y")
    works_summary = [{"title": i.get("title", "Untitled"), "status": "registered" if i.get("is_registered_with_pro") else "pending"} for i in items[:20]]

    from ..templates.email_templates import registration_report as reg_report_template
    html_body = reg_report_template(
        recipient_name=to_name,
        org_name=org_name,
        report_date=report_date,
        total_works=item_count,
        registered=registered_count,
        pending=pending_count,
        gaps=gaps_count,
        works_summary=works_summary,
    )

    import base64
    try:
        from ..services.email_provider import get_email_provider
        provider = get_email_provider()

        filename = f"Registration_Report_{request.asset_type}_{org_name}_{datetime.utcnow().strftime('%Y%m%d')}.pdf"
        pdf_b64 = base64.b64encode(pdf_bytes).decode('utf-8')

        success = provider.send_email(
            to=to_email,
            subject=f"PRO Bulk Registration Report — {org_name} ({item_count} {request.asset_type})",
            html_body=html_body,
            attachments=[{"filename": filename, "content": pdf_b64}],
        )

        if not success:
            raise HTTPException(status_code=500, detail="Failed to send email")

        from ..models import RegistrationReport
        now = datetime.utcnow()
        stats = _compute_report_stats(items)
        sent_report = RegistrationReport(
            organization_id=org_id,
            report_type=request.asset_type.upper(),
            title=f"Sent to {to_name} — {request.asset_type.title()} ({now.strftime('%b %d, %Y')})",
            status="SENT",
            item_count=stats["total"],
            outstanding_count=stats["outstanding"],
            ready_count=stats["valid"],
            needs_attention_count=stats["invalid"],
            report_data=json.dumps(items),
            pdf_data=pdf_bytes,
            pdf_mime="application/pdf",
            generated_at=now,
            sent_at=now,
            sent_to=to_email,
            created_by_user_id=current_user.id,
        )
        db.add(sent_report)

        from ..services.audit_service import log_action
        db.flush()
        log_action(
            db, org_id, current_user.id,
            "SEND_REGISTRATION_REPORT", "REGISTRATION_REPORT", sent_report.id,
            sent_report.title,
            {"recipient_email": to_email, "recipient_name": to_name, "item_count": item_count, "asset_type": request.asset_type}
        )

        db.commit()

        return {"success": True, "message": f"Report sent to {to_email}", "report_id": sent_report.id}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to send email: {str(e)}")


class SaveReportRequest(BaseModel):
    title: Optional[str] = None
    asset_type: str = "songs"
    creator_id: Optional[int] = None
    filter_status: Optional[str] = None


@router.get(
    "/org/{org_id}/saved",
    summary='List saved registration reports for the org',
    description='Returns each named SavedRegistrationReport snapshot (filter set + frozen results) the org has saved.\n\n**Path parameter:** `org_id`.\n**Auth:** Bearer JWT — caller must be a member of the org.\n**Response:** `{ reports: [{id, name, entity, created_at, row_count, last_refreshed_at}] }`.',
)
def list_saved_reports(
    org_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    from ..models import RegistrationReport
    verify_org_access(current_user, org_id, db)

    reports = db.query(RegistrationReport).filter(
        RegistrationReport.organization_id == org_id
    ).order_by(RegistrationReport.created_at.desc()).all()

    return [{
        "id": r.id,
        "title": r.title,
        "report_type": r.report_type,
        "status": r.status,
        "filter_creator_id": r.filter_creator_id,
        "filter_status": r.filter_status,
        "item_count": r.item_count,
        "outstanding_count": r.outstanding_count,
        "ready_count": r.ready_count,
        "needs_attention_count": r.needs_attention_count,
        "generated_at": r.generated_at.isoformat() if r.generated_at else None,
        "sent_at": r.sent_at.isoformat() if r.sent_at else None,
        "sent_to": r.sent_to,
        "created_at": r.created_at.isoformat() if r.created_at else None,
        "created_by_user_id": r.created_by_user_id,
    } for r in reports]


@router.post(
    "/org/{org_id}/save",
    summary='Save the current registration report as a named snapshot',
    description='Persists the supplied filter set + result snapshot so it can be re-opened or refreshed later.\n\n**Path parameter:** `org_id`.\n**Body:** `{ name, entity, filters: {...} }`.\n**Auth:** Bearer JWT — caller must be a member of the org.\n**Response:** the saved report header.',
)
def save_report(
    org_id: int,
    request: SaveReportRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    from ..models import RegistrationReport
    verify_org_access(current_user, org_id, db)

    report_items = _build_report_items(
        db, org_id, request.asset_type,
        creator_id=request.creator_id,
        status=request.filter_status,
    )
    stats = _compute_report_stats(report_items)

    now = datetime.utcnow()
    title = request.title or f"Bulk Registration — {request.asset_type.title()} ({now.strftime('%b %d, %Y')})"

    report = RegistrationReport(
        organization_id=org_id,
        report_type=request.asset_type.upper(),
        title=title,
        status="GENERATED",
        filter_creator_id=request.creator_id,
        filter_status=request.filter_status,
        item_count=stats["total"],
        outstanding_count=stats["outstanding"],
        ready_count=stats["valid"],
        needs_attention_count=stats["invalid"],
        report_data=json.dumps(report_items),
        generated_at=now,
        created_by_user_id=current_user.id,
    )
    db.add(report)
    db.commit()
    db.refresh(report)

    return {
        "id": report.id,
        "title": report.title,
        "report_type": report.report_type,
        "status": report.status,
        "item_count": report.item_count,
        "outstanding_count": report.outstanding_count,
        "ready_count": report.ready_count,
        "needs_attention_count": report.needs_attention_count,
        "generated_at": report.generated_at.isoformat() if report.generated_at else None,
        "created_at": report.created_at.isoformat() if report.created_at else None,
    }


@router.get(
    "/org/{org_id}/saved/{report_id}",
    summary='Open a previously saved registration report',
    description='Returns the frozen rows captured the last time the snapshot was refreshed plus its filter set.\n\n**Path parameters:** `org_id`, `report_id`.\n**Auth:** Bearer JWT — caller must be a member of the org.\n**Response:** `{ id, name, entity, filters, last_refreshed_at, rows: [...] }`.',
)
def get_saved_report(
    org_id: int,
    report_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    from ..models import RegistrationReport
    verify_org_access(current_user, org_id, db)

    report = db.query(RegistrationReport).filter(
        RegistrationReport.id == report_id,
        RegistrationReport.organization_id == org_id,
    ).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    report_items = json.loads(report.report_data) if report.report_data else []

    return {
        "id": report.id,
        "title": report.title,
        "report_type": report.report_type,
        "status": report.status,
        "filter_creator_id": report.filter_creator_id,
        "filter_status": report.filter_status,
        "item_count": report.item_count,
        "outstanding_count": report.outstanding_count,
        "ready_count": report.ready_count,
        "needs_attention_count": report.needs_attention_count,
        "generated_at": report.generated_at.isoformat() if report.generated_at else None,
        "sent_at": report.sent_at.isoformat() if report.sent_at else None,
        "sent_to": report.sent_to,
        "created_at": report.created_at.isoformat() if report.created_at else None,
        "items": report_items,
    }


@router.put(
    "/org/{org_id}/saved/{report_id}/refresh",
    summary='Re-run a saved report against the current data',
    description='Re-applies the saved filter set to live data and updates the stored snapshot rows + `last_refreshed_at`.\n\n**Path parameters:** `org_id`, `report_id`.\n**Auth:** Bearer JWT — caller must be a member of the org.\n**Response:** `{ id, last_refreshed_at, row_count }`.',
)
def refresh_saved_report(
    org_id: int,
    report_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    from ..models import RegistrationReport
    verify_org_access(current_user, org_id, db)

    report = db.query(RegistrationReport).filter(
        RegistrationReport.id == report_id,
        RegistrationReport.organization_id == org_id,
    ).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    asset_type = report.report_type.lower() if report.report_type else "songs"
    report_items = _build_report_items(
        db, org_id, asset_type,
        creator_id=report.filter_creator_id,
        status=report.filter_status,
    )
    stats = _compute_report_stats(report_items)

    report.report_data = json.dumps(report_items)
    report.item_count = stats["total"]
    report.outstanding_count = stats["outstanding"]
    report.ready_count = stats["valid"]
    report.needs_attention_count = stats["invalid"]
    report.generated_at = datetime.utcnow()
    if report.status != "SENT":
        report.status = "GENERATED"
    db.commit()

    return {
        "id": report.id,
        "title": report.title,
        "status": report.status,
        "item_count": report.item_count,
        "outstanding_count": report.outstanding_count,
        "ready_count": report.ready_count,
        "needs_attention_count": report.needs_attention_count,
        "generated_at": report.generated_at.isoformat() if report.generated_at else None,
        "sent_at": report.sent_at.isoformat() if report.sent_at else None,
        "sent_to": report.sent_to,
        "items": json.loads(report.report_data) if report.report_data else [],
    }


@router.delete(
    "/org/{org_id}/saved/{report_id}",
    summary='Delete a saved registration report',
    description='Hard-deletes the snapshot.\n\n**Path parameters:** `org_id`, `report_id`.\n**Auth:** Bearer JWT — caller must be a member of the org.\n**Response:** `{ success: true }`.',
)
def delete_saved_report(
    org_id: int,
    report_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    from ..models import RegistrationReport
    verify_org_access(current_user, org_id, db)

    report = db.query(RegistrationReport).filter(
        RegistrationReport.id == report_id,
        RegistrationReport.organization_id == org_id,
    ).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    db.delete(report)
    db.commit()
    return {"detail": "Report deleted"}


@router.get(
    "/org/{org_id}/saved/{report_id}/pdf",
    summary='Download a saved registration report as PDF',
    description='Renders the snapshot (NOT live data) into a branded PDF — useful for distributing a frozen point-in-time view.\n\n**Path parameters:** `org_id`, `report_id`.\n**Auth:** Bearer JWT — caller must be a member of the org.\n**Response:** `application/pdf` download.',
)
def download_saved_report_pdf(
    org_id: int,
    report_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    from ..models import RegistrationReport
    verify_org_access(current_user, org_id, db)

    report = db.query(RegistrationReport).filter(
        RegistrationReport.id == report_id,
        RegistrationReport.organization_id == org_id,
    ).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    report_items = json.loads(report.report_data) if report.report_data else []
    if not report_items:
        raise HTTPException(status_code=400, detail="Report has no data")

    org = db.query(Organization).filter(Organization.id == org_id).first()
    org_name = org.name if org else "Organization"
    asset_type = report.report_type.lower() if report.report_type else "songs"

    buffer = _generate_pdf(report_items, asset_type, org_name)
    import re
    safe_title = re.sub(r'[^\w\s-]', '', report.title or 'Report').replace(' ', '_')[:80]
    filename = f"Registration_Report_{safe_title}_{datetime.utcnow().strftime('%Y%m%d')}.pdf"
    return Response(
        content=buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )


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
    elements.append(Paragraph(f"Bulk Registration — {asset_type.title()}", title_style))
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
    elements.append(Paragraph("Cadence — Catalog Intelligence | Confidential", footer_style))

    doc.build(elements)
    buffer.seek(0)
    return buffer.getvalue()
