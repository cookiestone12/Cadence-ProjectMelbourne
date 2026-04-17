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
    get_db, Song, Creator, SongCredit, OrganizationMember, User, Organization
)
from ..utils.auth import get_current_user
from .client_sharing import has_shared_access

logger = logging.getLogger("cadence")

router = APIRouter(prefix="/api/schedule-a", tags=["Schedule A"])


@router.post("/upload/{org_id}", summary="Upload a Schedule A document", description="Stages a Schedule A PDF/DOCX, runs AI extraction, and returns a parsed preview for review.")
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
            creator_name_override=creator_name
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


@router.get("/creator/{creator_id}/data", summary="Get a creator's Schedule A data", description="Returns the structured Schedule A rows (titles, splits, contracts) for a creator.")
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
    
    if not membership:
        if not has_shared_access(db, current_user.id, creator_id, required_module="contracts"):
            raise HTTPException(status_code=403, detail="Not authorized")
    
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
            "credits": credit_info
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


@router.get("/creator/{creator_id}/csv", summary="Export Schedule A as CSV", description="Streams the creator's Schedule A as a CSV download.")
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


@router.get("/creator/{creator_id}/pdf", summary="Export Schedule A as PDF", description="Renders a branded PDF Schedule A for the creator.")
def export_schedule_a_pdf(
    creator_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Export Schedule A as branded PDF"""
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter, landscape
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
    import os
    
    data = get_schedule_a_data(creator_id, db, current_user)
    
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, 
        pagesize=landscape(letter),
        rightMargin=0.5*inch,
        leftMargin=0.5*inch,
        topMargin=0.5*inch,
        bottomMargin=0.5*inch
    )
    
    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=colors.HexColor('#9333EA'),
        alignment=TA_CENTER,
        spaceAfter=6
    )
    
    subtitle_style = ParagraphStyle(
        'CustomSubtitle',
        parent=styles['Normal'],
        fontSize=14,
        textColor=colors.HexColor('#EC4899'),
        alignment=TA_CENTER,
        spaceAfter=12
    )
    
    section_style = ParagraphStyle(
        'SectionHeader',
        parent=styles['Heading2'],
        fontSize=14,
        textColor=colors.HexColor('#9333EA'),
        spaceBefore=20,
        spaceAfter=10
    )
    
    normal_style = ParagraphStyle(
        'CustomNormal',
        parent=styles['Normal'],
        fontSize=10
    )
    
    small_style = ParagraphStyle(
        'Small',
        parent=styles['Normal'],
        fontSize=8,
        textColor=colors.grey
    )
    
    elements = []
    
    # Header with logo
    logo_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'assets', 'cadence-logo.png')
    if os.path.exists(logo_path):
        logo = Image(logo_path, width=2.0*inch, height=1.125*inch)
        logo.hAlign = 'CENTER'
        elements.append(logo)
        elements.append(Spacer(1, 6))
    
    elements.append(Paragraph("CADENCE CATALOG INTELLIGENCE", title_style))
    elements.append(Paragraph("Schedule A - Catalog of Compositions", subtitle_style))
    elements.append(Spacer(1, 12))
    
    # Creator info
    creator_info = f"""
    <b>Creator:</b> {data['creator']['display_name']}<br/>
    <b>Legal Name:</b> {data['creator'].get('legal_name') or 'N/A'}<br/>
    <b>Organization:</b> {data['organization']['name']}<br/>
    <b>PRO:</b> {data['creator'].get('primary_pro') or 'N/A'} | <b>IPI:</b> {data['creator'].get('primary_ipi') or 'N/A'}<br/>
    <b>Generated:</b> {datetime.utcnow().strftime('%B %d, %Y')}
    """
    elements.append(Paragraph(creator_info, normal_style))
    elements.append(Spacer(1, 12))
    
    # Summary table
    elements.append(Paragraph("SUMMARY", section_style))
    
    summary_data = [
        ["Total Compositions", str(data['summary']['total_songs']),
         "Released", str(data['summary']['released_count']),
         "Pipeline", str(data['summary']['pipeline_count'])],
        ["Paid Placements", str(data['summary']['paid_count']),
         "Contracted", str(data['summary']['contracted_count']),
         "Total Advances", data['summary']['total_advance_display']],
        ["PRO Registered", str(data['summary']['pro_registered']),
         "DSP Registered", str(data['summary']['dsp_registered']),
         "", ""]
    ]
    
    summary_table = Table(summary_data, colWidths=[1.5*inch, 0.8*inch, 1.2*inch, 0.8*inch, 1.2*inch, 1.2*inch])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#F3E8FF')),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor('#581C87')),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#C084FC'))
    ]))
    elements.append(summary_table)
    elements.append(Spacer(1, 20))
    
    # Table headers for songs
    table_headers = [
        "Title", "Artist", "Release", "Label", "Pub %", 
        "Advance", "Status", "PRO", "DSP", "Contract", "Paid"
    ]
    
    # Released catalog
    if data['released']:
        elements.append(Paragraph("RELEASED CATALOG", section_style))
        
        table_data = [table_headers]
        for song in data['released']:
            table_data.append([
                Paragraph(song['title'][:30], small_style),
                Paragraph(song['primary_artist'][:20], small_style),
                song['release_date'][:10] if song['release_date'] else "",
                Paragraph((song['label'] or "")[:15], small_style),
                format_percentage(song['publishing_percentage'])[:8],
                song['advance_display'],
                song['status'],
                "Y" if song['is_registered_with_pro'] else "N",
                "Y" if str(song.get('is_registered_with_dsp', '')).upper() == 'YES' else ("N/A" if str(song.get('is_registered_with_dsp', '')).upper() == 'N/A' else "N"),
                "Y" if song['has_contract_executed'] else "N",
                "Y" if str(song.get('is_paid', '')).upper() == 'YES' else ("N/A" if str(song.get('is_paid', '')).upper() == 'N/A' else "N")
            ])
        
        released_table = Table(table_data, colWidths=[
            1.4*inch, 1.2*inch, 0.7*inch, 0.9*inch, 0.6*inch,
            0.8*inch, 0.9*inch, 0.4*inch, 0.4*inch, 0.5*inch, 0.4*inch
        ])
        released_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#9333EA')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 8),
            ('FONTSIZE', (0, 1), (-1, -1), 7),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E9D5FF')),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#FAF5FF')])
        ]))
        elements.append(released_table)
        elements.append(Spacer(1, 20))
    
    # Pipeline
    if data['pipeline']:
        elements.append(Paragraph("PIPELINE (UNRELEASED)", section_style))
        
        table_data = [table_headers]
        for song in data['pipeline']:
            table_data.append([
                Paragraph(song['title'][:30], small_style),
                Paragraph(song['primary_artist'][:20], small_style),
                song['release_date'][:10] if song['release_date'] else "TBD",
                Paragraph((song['label'] or "")[:15], small_style),
                format_percentage(song['publishing_percentage'])[:8],
                song['advance_display'],
                song['status'],
                "Y" if song['is_registered_with_pro'] else "N",
                "Y" if str(song.get('is_registered_with_dsp', '')).upper() == 'YES' else ("N/A" if str(song.get('is_registered_with_dsp', '')).upper() == 'N/A' else "N"),
                "Y" if song['has_contract_executed'] else "N",
                "Y" if str(song.get('is_paid', '')).upper() == 'YES' else ("N/A" if str(song.get('is_paid', '')).upper() == 'N/A' else "N")
            ])
        
        pipeline_table = Table(table_data, colWidths=[
            1.4*inch, 1.2*inch, 0.7*inch, 0.9*inch, 0.6*inch,
            0.8*inch, 0.9*inch, 0.4*inch, 0.4*inch, 0.5*inch, 0.4*inch
        ])
        pipeline_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#EC4899')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 8),
            ('FONTSIZE', (0, 1), (-1, -1), 7),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#FBCFE8')),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#FDF2F8')])
        ]))
        elements.append(pipeline_table)
    
    # Footer
    elements.append(Spacer(1, 30))
    footer_text = f"""
    <i>This Schedule A was generated by Cadence Catalog Intelligence</i><br/>
    <i>Report Date: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}</i>
    """
    elements.append(Paragraph(footer_text, small_style))
    
    doc.build(elements)
    
    buffer.seek(0)
    
    filename = f"Catalog_Doc_{data['creator']['display_name'].replace(' ', '_')}_{datetime.utcnow().strftime('%Y-%m-%d')}.pdf"
    
    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@router.get("/creator/{creator_id}/schedule-a-pdf")
def export_simplified_schedule_a_pdf(
    creator_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Export simplified Schedule A PDF for external sharing"""
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
    from reportlab.lib.enums import TA_CENTER, TA_LEFT
    import os

    sage_primary = colors.HexColor('#5B8A72')
    sage_dark = colors.HexColor('#3D4A44')
    sage_light = colors.HexColor('#E8F0EC')
    sage_border = colors.HexColor('#A3C4B5')

    data = get_schedule_a_data(creator_id, db, current_user)

    all_songs = sorted(
        data['released'] + data['pipeline'],
        key=lambda s: (s['title'] or '').lower()
    )

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=0.6*inch,
        leftMargin=0.6*inch,
        topMargin=0.5*inch,
        bottomMargin=0.6*inch
    )

    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        'SATitle',
        parent=styles['Heading1'],
        fontSize=22,
        textColor=sage_primary,
        alignment=TA_CENTER,
        spaceAfter=4
    )

    subtitle_style = ParagraphStyle(
        'SASubtitle',
        parent=styles['Normal'],
        fontSize=13,
        textColor=sage_dark,
        alignment=TA_CENTER,
        spaceAfter=16
    )

    info_style = ParagraphStyle(
        'SAInfo',
        parent=styles['Normal'],
        fontSize=10,
        textColor=sage_dark,
        leading=16
    )

    cell_style = ParagraphStyle(
        'SACell',
        parent=styles['Normal'],
        fontSize=8,
        textColor=sage_dark
    )

    footer_style = ParagraphStyle(
        'SAFooter',
        parent=styles['Normal'],
        fontSize=8,
        textColor=colors.HexColor('#7A8580'),
        alignment=TA_CENTER
    )

    elements = []

    logo_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'assets', 'cadence-logo.png')
    if os.path.exists(logo_path):
        logo = Image(logo_path, width=2.0*inch, height=1.125*inch)
        logo.hAlign = 'CENTER'
        elements.append(logo)
        elements.append(Spacer(1, 4))

    elements.append(Paragraph("CADENCE CATALOG INTELLIGENCE", title_style))
    elements.append(Paragraph("Schedule A", subtitle_style))

    creator_name = data['creator']['display_name']
    legal_name = data['creator'].get('legal_name') or 'N/A'
    pro = data['creator'].get('primary_pro') or 'N/A'
    gen_date = datetime.utcnow().strftime('%B %d, %Y')

    info_text = f"""
    <b>Creator:</b> {creator_name}<br/>
    <b>Legal Name:</b> {legal_name}<br/>
    <b>PRO:</b> {pro}<br/>
    <b>Generated:</b> {gen_date}
    """
    elements.append(Paragraph(info_text, info_style))
    elements.append(Spacer(1, 16))

    table_headers = ["Title", "Artist", "Released", "Label", "Pub %", "Status"]

    table_data = [table_headers]
    for song in all_songs:
        is_released = "Yes" if (song.get('release_date') or song.get('is_released_flag', False)) else "No"
        for s_data in data['released']:
            if s_data['id'] == song['id']:
                is_released = "Yes"
                break

        pub_pct = format_percentage(song['publishing_percentage'])[:8] if song['publishing_percentage'] else "-"

        table_data.append([
            Paragraph(song['title'][:40], cell_style),
            Paragraph((song['primary_artist'] or '')[:25], cell_style),
            is_released,
            Paragraph((song['label'] or '-')[:20], cell_style),
            pub_pct,
            song['status']
        ])

    col_widths = [2.0*inch, 1.4*inch, 0.7*inch, 1.2*inch, 0.6*inch, 1.2*inch]

    song_table = Table(table_data, colWidths=col_widths, repeatRows=1)
    song_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), sage_primary),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 9),
        ('FONTSIZE', (0, 1), (-1, -1), 8),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('ALIGN', (2, 0), (2, -1), 'CENTER'),
        ('ALIGN', (4, 0), (4, -1), 'CENTER'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
        ('TOPPADDING', (0, 0), (-1, 0), 8),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 5),
        ('TOPPADDING', (0, 1), (-1, -1), 5),
        ('GRID', (0, 0), (-1, -1), 0.5, sage_border),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, sage_light]),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    elements.append(song_table)

    elements.append(Spacer(1, 30))
    footer_text = f"""
    <i>Generated by Cadence on {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}</i>
    """
    elements.append(Paragraph(footer_text, footer_style))

    doc.build(elements)

    buffer.seek(0)

    filename = f"Schedule_A_{data['creator']['display_name'].replace(' ', '_')}_{datetime.utcnow().strftime('%Y-%m-%d')}.pdf"

    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


# Keep backward compatibility with old endpoint
@router.get("/creator/{creator_id}")
def export_schedule_a_legacy(
    creator_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Legacy CSV export - redirects to new CSV endpoint"""
    return export_schedule_a_csv(creator_id, db, current_user)
