from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Response
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import and_
from openpyxl import load_workbook
import csv
import io
import logging
from datetime import datetime, date
from typing import Optional
from ..models import (
    get_db, Song, Creator, SongCredit, OrganizationMember, User, Organization,
    RightsSplit, ContractAsset, Contract,
)
from ..utils.auth import get_current_user
from .client_sharing import has_shared_access

logger = logging.getLogger("cadence")

router = APIRouter(prefix="/api/schedule-a", tags=["Schedule A"])


@router.post("/upload/{org_id}", summary="Upload a Schedule A document", description='Stages a Schedule A PDF/DOCX, runs AI extraction, and returns a parsed preview for review.\n\n**Path parameter:** `org_id`.\n**Body (multipart/form-data):** `file`; `creator_id?`; `notes?`.\n**Auth:** Bearer JWT — caller must be a member of the org.\n**Response:** `{ import_id, parsed_rows, creator_id, warnings: [...], preview: [{title, isrc?, splits: [...]}] }`.')
async def upload_schedule_a(
    org_id: int,
    file: UploadFile = File(...),
    creator_name: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Upload a Schedule A / Placement Status Sheet file (CSV or Excel).
    
    The creator name can be provided via query param, or extracted from filename.
    Expected filename format: "CREATOR NAME - Placement Sheet.xlsx"
    """
    from backend.services.schedule_a_ingestion import ingest_schedule_a, ScheduleAIngestionResult
    
    membership = db.query(OrganizationMember).filter(
        OrganizationMember.user_id == current_user.id,
        OrganizationMember.organization_id == org_id
    ).first()
    
    if not membership:
        raise HTTPException(status_code=403, detail="Not a member of this organization")
    
    organization = db.query(Organization).filter(Organization.id == org_id).first()
    if not organization:
        raise HTTPException(status_code=404, detail="Organization not found")
    
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")
    
    allowed_extensions = ['.csv', '.xlsx', '.xls']
    file_ext = file.filename.lower()
    if not any(file_ext.endswith(ext) for ext in allowed_extensions):
        raise HTTPException(
            status_code=400, 
            detail=f"Invalid file type. Allowed types: {', '.join(allowed_extensions)}"
        )
    
    if file.size and file.size > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File too large. Maximum size is 10MB.")
    
    try:
        file_content = await file.read()
        
        result = ingest_schedule_a(
            db=db,
            organization=organization,
            file_content=file_content,
            filename=file.filename,
            creator_name_override=creator_name,
            user_id=current_user.id,
        )
        
        if result.errors:
            raise HTTPException(status_code=400, detail=result.errors[0])
        
        return result.to_dict()
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Schedule A upload failed for org {org_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to process file: {str(e)}")


def parse_yes_no_na(value):
    """Parse Yes/No/N/A values from Excel"""
    if value is None:
        return 'N/A'
    str_val = str(value).strip().upper()
    if str_val in ['YES', 'Y', '1', 'TRUE']:
        return 'Yes'
    elif str_val in ['NO', 'N', '0', 'FALSE']:
        return 'No'
    return 'N/A'

def parse_percentage(value):
    """Parse percentage values, cap at 100%"""
    if value is None:
        return None
    try:
        if isinstance(value, str):
            value = value.replace('%', '').strip()
        pct = float(value)
        # Cap at 100% and round to 2 decimal places
        return min(round(pct, 2), 100.0)
    except:
        return None

def parse_amount(value):
    """Parse currency amounts (stored in cents)"""
    if value is None:
        return None
    try:
        if isinstance(value, str):
            value = value.replace('$', '').replace(',', '').strip()
        amount = float(value)
        return int(amount * 100)  # Convert to cents
    except:
        return None

def parse_date(value):
    """Parse date values"""
    if value is None:
        return None
    try:
        if isinstance(value, str):
            for fmt in ['%Y-%m-%d', '%m/%d/%Y', '%m-%d-%Y', '%Y/%m/%d']:
                try:
                    return datetime.strptime(value, fmt).date()
                except:
                    continue
        elif hasattr(value, 'date'):
            return value.date()
        return None
    except:
        return None

def get_placement_status(song):
    """Derive placement status from song fields for Schedule A"""
    if str(song.is_paid).upper() in ("YES", "TRUE"):
        return "Paid"
    elif song.has_contract_executed:
        if str(song.is_invoiced).upper() in ("YES", "TRUE"):
            return "Invoiced"
        else:
            return "Contracted"
    elif song.has_contract_sent:
        return "Contract Sent"
    elif song.is_released:
        return "Released - Awaiting Contract"
    else:
        return "In Pipeline"

def format_date(d):
    """Format date for export"""
    if d is None:
        return ""
    if isinstance(d, (datetime, date)):
        return d.strftime("%Y-%m-%d")
    return str(d)

def format_currency(cents):
    """Format cents to dollars"""
    if cents is None:
        return ""
    return f"${cents / 100:,.2f}"

def format_percentage(pct):
    """Format percentage"""
    if pct is None:
        return ""
    return f"{pct:.2f}%"

def format_bool(val):
    """Format boolean or string flag to Yes/No/N/A"""
    if val is True or str(val).strip().upper() in ("YES", "TRUE", "1"):
        return "Yes"
    elif val is False or str(val).strip().upper() in ("NO", "FALSE", "0"):
        return "No"
    return "N/A"


@router.get("/creator/{creator_id}/data", summary="Get a creator's Schedule A data", description="Returns the structured Schedule A rows (titles, splits, contracts) for a creator.\n\n**Path parameter:** `creator_id`.\n**Auth:** Bearer JWT — caller must be a member of the creator's org.\n**Response:** `{ creator: {...}, rows: [{title, isrc, iswc, writer_splits: [...], contracts: [...]}] }`.")
def get_schedule_a_data(
    creator_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get Schedule A data for a creator, organized by Released and Pipeline"""
    creator = db.query(Creator).filter(Creator.id == creator_id).first()
    if not creator:
        raise HTTPException(status_code=404, detail="Creator not found")
    
    membership = db.query(OrganizationMember).filter(
        OrganizationMember.user_id == current_user.id,
        OrganizationMember.organization_id == creator.organization_id
    ).first()
    
    # Task #171 — Phase 4: a client-portal caller (a Cadence user with shared
    # access to one creator but no org membership) must NEVER see another
    # creator's RightsSplit rows. We track that boundary here and use it below
    # to scope writer_splits per song to just this creator's rows. Org
    # members see the full split set so they can verify totals add to 100%.
    is_client_portal_caller = False
    if not membership:
        if not has_shared_access(db, current_user.id, creator_id, required_module="contracts"):
            raise HTTPException(status_code=403, detail="Not authorized")
        is_client_portal_caller = True

    org = db.query(Organization).filter(Organization.id == creator.organization_id).first()
    
    # Get all songs for this creator
    songs = db.query(Song).join(SongCredit).filter(
        SongCredit.creator_id == creator_id
    ).order_by(Song.release_date.desc().nullslast(), Song.title).all()
    
    released = []
    pipeline = []
    
    for song in songs:
        # Get credits for this song
        credits = db.query(SongCredit).filter(SongCredit.song_id == song.id).all()
        credit_info = []
        for c in credits:
            cr = db.query(Creator).filter(Creator.id == c.creator_id).first()
            if cr:
                credit_info.append({
                    "name": cr.display_name,
                    "role": c.role,
                    "share": c.share_percentage
                })
        
        # Task #171 — Phase 4: gather RightsSplit rows attached to this song
        # via any of its ContractAssets. Client-portal callers see only their
        # own creator's splits; org members see every holder so they can audit
        # 100% totals. Org callers ALSO get `writer_splits_by_holder` — a
        # dict keyed by holder display_name with the holder's split rows
        # underneath — so the UI can render the org Schedule A view as
        # "split totals grouped by client" without re-bucketing the flat
        # list on the frontend. Client-portal callers receive an empty
        # `writer_splits_by_holder` because by definition they only see
        # one holder.
        writer_splits = []
        writer_splits_by_holder = {}
        asset_ids = [
            ca.id for ca in db.query(ContractAsset).filter(
                ContractAsset.asset_type == "SONG",
                ContractAsset.asset_id == song.id,
            ).all()
        ]
        if asset_ids:
            split_q = db.query(RightsSplit).filter(
                RightsSplit.contract_asset_id.in_(asset_ids)
            )
            if is_client_portal_caller:
                split_q = split_q.filter(RightsSplit.rights_holder_id == creator_id)
            for s in split_q.all():
                holder_name = s.rights_holder_name
                if s.rights_holder_id and not holder_name:
                    h = db.query(Creator).filter(Creator.id == s.rights_holder_id).first()
                    holder_name = h.display_name if h else None
                row = {
                    "id": s.id,
                    "rights_holder_id": s.rights_holder_id,
                    "rights_holder_name": holder_name or "Unknown",
                    "rights_type": s.rights_type,
                    "share_percentage": s.share_percentage,
                    "role": s.role,
                }
                writer_splits.append(row)
                if not is_client_portal_caller:
                    writer_splits_by_holder.setdefault(
                        row["rights_holder_name"], []
                    ).append(row)

        song_data = {
            "id": song.id,
            "title": song.title,
            "primary_artist": song.primary_artist,
            "isrc": song.isrc or "",
            "iswc": song.iswc or "",
            "release_date": format_date(song.release_date),
            "label": song.label or "",
            "publishing_percentage": song.publishing_percentage,
            "master_percentage": song.master_percentage,
            "advance_amount": song.advance_amount,
            "advance_display": format_currency(song.advance_amount),
            "is_registered_with_pro": song.is_registered_with_pro,
            "is_registered_with_dsp": song.is_registered_with_dsp,
            "soundexchange_registered": song.soundexchange_registered or "N/A",
            "has_contract_executed": song.has_contract_executed,
            "has_contract_sent": song.has_contract_sent,
            "is_invoiced": song.is_invoiced,
            "is_paid": song.is_paid,
            "status": get_placement_status(song),
            "notes": song.notes or "",
            "credits": credit_info,
            "writer_splits": writer_splits,
            "writer_splits_by_holder": writer_splits_by_holder,
        }
        
        if song.is_released or song.release_date:
            released.append(song_data)
        else:
            pipeline.append(song_data)
    
    # Calculate summary stats
    total_advance = sum(s.advance_amount or 0 for s in songs)
    paid_count = sum(1 for s in songs if str(s.is_paid).upper() in ("YES", "TRUE"))
    contracted_count = sum(1 for s in songs if s.has_contract_executed)
    pro_registered = sum(1 for s in songs if s.is_registered_with_pro)
    dsp_registered = sum(1 for s in songs if str(s.is_registered_with_dsp).upper() in ("YES", "TRUE"))
    
    return {
        "creator": {
            "id": creator.id,
            "display_name": creator.display_name,
            "legal_name": creator.legal_name,
            "roles": creator.roles,
            "primary_pro": creator.primary_pro,
            "primary_ipi": creator.primary_ipi
        },
        "organization": {
            "id": org.id,
            "name": org.name,
            "type": org.type
        },
        "summary": {
            "total_songs": len(songs),
            "released_count": len(released),
            "pipeline_count": len(pipeline),
            "paid_count": paid_count,
            "contracted_count": contracted_count,
            "pro_registered": pro_registered,
            "dsp_registered": dsp_registered,
            "total_advance": total_advance,
            "total_advance_display": format_currency(total_advance)
        },
        "released": released,
        "pipeline": pipeline,
        "generated_at": datetime.utcnow().isoformat()
    }


@router.get("/creator/{creator_id}/csv", summary="Export Schedule A as CSV", description="Streams the creator's Schedule A as a CSV download.\n\n**Path parameter:** `creator_id`.\n**Auth:** Bearer JWT — caller must be a member of the creator's org.\n**Response:** `text/csv` download.")
def export_schedule_a_csv(
    creator_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Export Schedule A as properly formatted CSV with metadata in comment rows"""
    data = get_schedule_a_data(creator_id, db, current_user)
    
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Column headers - first row for proper CSV import
    headers = [
        "Section", "Song Title", "Artist", "Release Date", "Label",
        "ISRC", "ISWC", "Publishing %", "Master %", "Advance",
        "Status", "PRO Registered", "DSP Registered", "SoundExchange",
        "Contract Executed", "Invoiced", "Paid", "Notes"
    ]
    writer.writerow(headers)
    
    # Released catalog songs
    for song in data['released']:
        writer.writerow([
            "Released",
            song['title'],
            song['primary_artist'],
            song['release_date'],
            song['label'],
            song['isrc'],
            song['iswc'],
            format_percentage(song['publishing_percentage']),
            format_percentage(song['master_percentage']),
            song['advance_display'],
            song['status'],
            format_bool(song['is_registered_with_pro']),
            format_bool(song['is_registered_with_dsp']),
            song['soundexchange_registered'],
            format_bool(song['has_contract_executed']),
            format_bool(song['is_invoiced']),
            format_bool(song['is_paid']),
            song['notes']
        ])
    
    # Pipeline songs
    for song in data['pipeline']:
        writer.writerow([
            "Pipeline",
            song['title'],
            song['primary_artist'],
            song['release_date'],
            song['label'],
            song['isrc'],
            song['iswc'],
            format_percentage(song['publishing_percentage']),
            format_percentage(song['master_percentage']),
            song['advance_display'],
            song['status'],
            format_bool(song['is_registered_with_pro']),
            format_bool(song['is_registered_with_dsp']),
            song['soundexchange_registered'],
            format_bool(song['has_contract_executed']),
            format_bool(song['is_invoiced']),
            format_bool(song['is_paid']),
            song['notes']
        ])
    
    # Add metadata as comment rows at the end (prefixed with # for CSV compatibility)
    writer.writerow([])
    writer.writerow(["# CADENCE CATALOG INTELLIGENCE - SCHEDULE A"])
    writer.writerow([f"# Creator: {data['creator']['display_name']}"])
    writer.writerow([f"# Legal Name: {data['creator'].get('legal_name') or 'N/A'}"])
    writer.writerow([f"# Organization: {data['organization']['name']}"])
    writer.writerow([f"# Total Compositions: {data['summary']['total_songs']}"])
    writer.writerow([f"# Released: {data['summary']['released_count']} | Pipeline: {data['summary']['pipeline_count']}"])
    writer.writerow([f"# Paid: {data['summary']['paid_count']} | Contracted: {data['summary']['contracted_count']}"])
    writer.writerow([f"# Total Advances: {data['summary']['total_advance_display']}"])
    writer.writerow([f"# Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}"])
    
    content = output.getvalue()
    output.close()
    
    filename = f"Schedule_A_{data['creator']['display_name'].replace(' ', '_')}_{datetime.utcnow().strftime('%Y-%m-%d')}.csv"
    
    return Response(
        content=content,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@router.get("/creator/{creator_id}/pdf", summary="Export Schedule A as PDF", description="Renders a branded PDF Schedule A for the creator with the org logo.\n\n**Path parameter:** `creator_id`.\n**Auth:** Bearer JWT — caller must be a member of the creator's org.\n**Response:** `application/pdf` download.")
def export_schedule_a_pdf(
    creator_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Export Schedule A as branded PDF"""
    from ..services.branding import theme_from_org, safe_filename_segment
    from ..services.pdf_engine import BrandedPDF
    from ..models import Organization

    data = get_schedule_a_data(creator_id, db, current_user)
    org = db.query(Organization).filter(Organization.id == data['organization']['id']).first()
    theme = theme_from_org(org)

    pdf = BrandedPDF(
        theme,
        title="Schedule A",
        subtitle="Catalog of Compositions",
        landscape_orientation=True,
    )
    pdf.cover()

    pdf.text(
        f"<b>Creator:</b> {data['creator']['display_name']} · "
        f"<b>Legal Name:</b> {data['creator'].get('legal_name') or 'N/A'} · "
        f"<b>PRO:</b> {data['creator'].get('primary_pro') or 'N/A'} · "
        f"<b>IPI:</b> {data['creator'].get('primary_ipi') or 'N/A'}"
    )

    pdf.section("Summary")
    pdf.kpi_row([
        {"label": "Total Compositions", "value": str(data['summary']['total_songs'])},
        {"label": "Released", "value": str(data['summary']['released_count'])},
        {"label": "Pipeline", "value": str(data['summary']['pipeline_count'])},
        {"label": "Paid Placements", "value": str(data['summary']['paid_count'])},
        {"label": "Contracted", "value": str(data['summary']['contracted_count'])},
        {"label": "Total Advances", "value": data['summary']['total_advance_display']},
        {"label": "PRO Registered", "value": str(data['summary']['pro_registered'])},
        {"label": "DSP Registered", "value": str(data['summary']['dsp_registered'])},
    ])

    table_headers = [
        "Title", "Artist", "Release", "Label", "Pub %",
        "Advance", "Status", "PRO", "DSP", "Contract", "Paid"
    ]
    col_widths = [1.4, 1.2, 0.7, 0.9, 0.6, 0.8, 0.9, 0.4, 0.4, 0.5, 0.4]

    def _yn(song, field):
        v = str(song.get(field, "")).upper()
        if v == "YES":
            return "Y"
        if v == "N/A":
            return "N/A"
        return "N"

    def _build_rows(songs, default_date):
        rows = []
        for song in songs:
            rows.append([
                (song['title'] or "")[:40],
                (song['primary_artist'] or "")[:25],
                song['release_date'][:10] if song['release_date'] else default_date,
                (song['label'] or "")[:18],
                format_percentage(song['publishing_percentage'])[:8] if song['publishing_percentage'] else "-",
                song['advance_display'],
                song['status'],
                "Y" if song['is_registered_with_pro'] else "N",
                _yn(song, 'is_registered_with_dsp'),
                "Y" if song['has_contract_executed'] else "N",
                _yn(song, 'is_paid'),
            ])
        return rows

    if data['released']:
        pdf.section("Released Catalog")
        pdf.table(
            headers=table_headers,
            rows=_build_rows(data['released'], ""),
            col_widths=col_widths,
            wrap_cells=True,
        )

    if data['pipeline']:
        pdf.section("Pipeline (Unreleased)")
        pdf.table(
            headers=table_headers,
            rows=_build_rows(data['pipeline'], "TBD"),
            col_widths=col_widths,
            wrap_cells=True,
        )

    pdf_bytes = pdf.build()
    safe_name = safe_filename_segment(data['creator']['display_name'], "Creator")
    filename = f"Catalog_Doc_{safe_name}_{datetime.utcnow().strftime('%Y-%m-%d')}.pdf"

    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@router.get("/creator/{creator_id}/schedule-a-pdf", summary="Export simplified Schedule A PDF for external sharing", description="Renders a simplified, share-friendly Schedule A PDF (less internal detail) suitable for sending to a sub-publisher or counterparty.\n\n**Path parameter:** `creator_id`.\n**Auth:** Bearer JWT — caller must be a member of the creator's org.\n**Response:** `application/pdf` download.")
def export_simplified_schedule_a_pdf(
    creator_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Export simplified Schedule A PDF for external sharing"""
    from ..services.branding import theme_from_org, safe_filename_segment
    from ..services.pdf_engine import BrandedPDF
    from ..models import Organization

    data = get_schedule_a_data(creator_id, db, current_user)
    org = db.query(Organization).filter(Organization.id == data['organization']['id']).first()
    theme = theme_from_org(org)

    all_songs = sorted(
        data['released'] + data['pipeline'],
        key=lambda s: (s['title'] or '').lower()
    )

    pdf = BrandedPDF(theme, title="Schedule A", subtitle="Summary catalog of compositions")
    pdf.cover()

    creator_name = data['creator']['display_name']
    pdf.text(
        f"<b>Creator:</b> {creator_name}<br/>"
        f"<b>Legal Name:</b> {data['creator'].get('legal_name') or 'N/A'}<br/>"
        f"<b>PRO:</b> {data['creator'].get('primary_pro') or 'N/A'}"
    )
    pdf.spacer(8)

    rows = []
    released_ids = {s['id'] for s in data['released']}
    for song in all_songs:
        is_released = "Yes" if song['id'] in released_ids or song.get('release_date') else "No"
        pub_pct = format_percentage(song['publishing_percentage'])[:8] if song['publishing_percentage'] else "-"
        rows.append([
            (song['title'] or "")[:50],
            (song['primary_artist'] or "")[:30],
            is_released,
            (song['label'] or "-")[:25],
            pub_pct,
            song['status'],
        ])
    pdf.table(
        headers=["Title", "Artist", "Released", "Label", "Pub %", "Status"],
        rows=rows,
        col_widths=[2.0, 1.4, 0.7, 1.2, 0.6, 1.2],
        wrap_cells=True,
        align=["LEFT", "LEFT", "CENTER", "LEFT", "CENTER", "LEFT"],
    )

    pdf_bytes = pdf.build()
    safe_name = safe_filename_segment(creator_name, "Creator")
    filename = f"Schedule_A_{safe_name}_{datetime.utcnow().strftime('%Y-%m-%d')}.pdf"

    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


# Keep backward compatibility with old endpoint
@router.get("/creator/{creator_id}", summary="Legacy CSV export - redirects to new CSV endpoint", description="Legacy CSV export endpoint that 308-redirects to `/creator/{creator_id}/csv`. Kept for backward compatibility with older integrations.\n\n**Path parameter:** `creator_id`.\n**Auth:** Bearer JWT — caller must be a member of the creator's org.\n**Response:** 308 redirect to the new CSV endpoint.")
def export_schedule_a_legacy(
    creator_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Legacy CSV export - redirects to new CSV endpoint"""
    return export_schedule_a_csv(creator_id, db, current_user)
