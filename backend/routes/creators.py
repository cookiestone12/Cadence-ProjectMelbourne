from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import Response
from sqlalchemy.orm import Session
from sqlalchemy import func
from pydantic import BaseModel
from typing import List, Optional
from ..models import get_db, Creator, CreativeContact, Organization, OrganizationMember, User, Song, SongCredit, WorkCredit
from ..utils.auth import get_current_user
import os
import uuid
from datetime import datetime
from pathlib import Path

router = APIRouter(prefix="/api/creators", tags=["creators"])

class CreatorResponse(BaseModel):
    id: int
    display_name: str
    legal_name: Optional[str]
    email: Optional[str]
    roles: List[str]
    primary_territory: Optional[str]
    primary_pro: Optional[str]
    primary_ipi: Optional[str]
    hero_image_url: Optional[str]
    linked_user_id: Optional[int]
    song_count: Optional[int] = 0
    avg_health_score: Optional[float] = 0.0
    bio: Optional[str] = None
    spotify_url: Optional[str] = None
    apple_music_url: Optional[str] = None
    youtube_url: Optional[str] = None
    instagram_url: Optional[str] = None
    twitter_url: Optional[str] = None
    custom_links: Optional[List[dict]] = None
    roster_export_fields: Optional[List[str]] = None
    
    class Config:
        from_attributes = True

class CreatorCreateRequest(BaseModel):
    display_name: str
    legal_name: Optional[str] = None
    email: Optional[str] = None
    roles: List[str]
    primary_territory: Optional[str] = None
    primary_pro: Optional[str] = None
    primary_ipi: Optional[str] = None
    hero_image_url: Optional[str] = None
    bio: Optional[str] = None
    spotify_url: Optional[str] = None
    apple_music_url: Optional[str] = None
    youtube_url: Optional[str] = None
    instagram_url: Optional[str] = None
    twitter_url: Optional[str] = None
    custom_links: Optional[List[dict]] = None
    roster_export_fields: Optional[List[str]] = None

class CreatorUpdateRequest(BaseModel):
    display_name: Optional[str] = None
    legal_name: Optional[str] = None
    email: Optional[str] = None
    roles: Optional[List[str]] = None
    primary_territory: Optional[str] = None
    primary_pro: Optional[str] = None
    primary_ipi: Optional[str] = None
    hero_image_url: Optional[str] = None
    publisher_contact_id: Optional[int] = None
    admin_contact_id: Optional[int] = None
    bio: Optional[str] = None
    spotify_url: Optional[str] = None
    apple_music_url: Optional[str] = None
    youtube_url: Optional[str] = None
    instagram_url: Optional[str] = None
    twitter_url: Optional[str] = None
    custom_links: Optional[List[dict]] = None
    roster_export_fields: Optional[List[str]] = None

class CreatorDetailResponse(BaseModel):
    id: int
    display_name: str
    legal_name: Optional[str]
    email: Optional[str]
    roles: List[str]
    primary_territory: Optional[str]
    primary_pro: Optional[str]
    primary_ipi: Optional[str]
    hero_image_url: Optional[str]
    linked_user_id: Optional[int]
    song_count: int
    avg_health_score: float
    placement_count: int
    publisher_contact_id: Optional[int] = None
    publisher_contact: Optional[dict] = None
    admin_contact_id: Optional[int] = None
    admin_contact: Optional[dict] = None
    bio: Optional[str] = None
    spotify_url: Optional[str] = None
    apple_music_url: Optional[str] = None
    youtube_url: Optional[str] = None
    instagram_url: Optional[str] = None
    twitter_url: Optional[str] = None
    custom_links: Optional[List[dict]] = None
    roster_export_fields: Optional[List[str]] = None
    
    class Config:
        from_attributes = True

@router.get("/org/{org_id}", response_model=List[CreatorResponse])
def get_organization_creators(
    org_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    membership = db.query(OrganizationMember).filter(
        OrganizationMember.user_id == current_user.id,
        OrganizationMember.organization_id == org_id
    ).first()
    
    if not membership:
        raise HTTPException(status_code=403, detail="Not authorized to access this organization")
    
    creators = db.query(Creator).filter(Creator.organization_id == org_id).all()
    
    # Collect all creator IDs
    creator_ids = [creator.id for creator in creators]
    
    # Run ONE query to get song counts grouped by creator_id
    counts = db.query(SongCredit.creator_id, func.count(SongCredit.id)).filter(
        SongCredit.creator_id.in_(creator_ids)
    ).group_by(SongCredit.creator_id).all()
    count_map = {cid: cnt for cid, cnt in counts}
    
    # Run ONE query to get average health scores grouped by creator_id
    avgs = db.query(SongCredit.creator_id, func.avg(Song.status_health_score)).join(
        Song, Song.id == SongCredit.song_id
    ).filter(
        SongCredit.creator_id.in_(creator_ids)
    ).group_by(SongCredit.creator_id).all()
    avg_map = {cid: float(avg) if avg else 0.0 for cid, avg in avgs}
    
    result = []
    for creator in creators:
        song_count = count_map.get(creator.id, 0)
        avg_health = avg_map.get(creator.id, 0.0)
        
        result.append({
            "id": creator.id,
            "display_name": creator.display_name,
            "legal_name": creator.legal_name,
            "email": creator.email,
            "roles": creator.roles,
            "primary_territory": creator.primary_territory,
            "primary_pro": creator.primary_pro,
            "primary_ipi": creator.primary_ipi,
            "hero_image_url": creator.hero_image_url,
            "linked_user_id": creator.linked_user_id,
            "song_count": song_count,
            "avg_health_score": float(avg_health) if avg_health else 0.0,
            "bio": creator.bio,
            "spotify_url": creator.spotify_url,
            "apple_music_url": creator.apple_music_url,
            "youtube_url": creator.youtube_url,
            "instagram_url": creator.instagram_url,
            "twitter_url": creator.twitter_url,
            "custom_links": creator.custom_links or [],
            "roster_export_fields": creator.roster_export_fields or [],
        })
    
    return result

def check_roster_permission(membership):
    if membership.role in ("OWNER", "ADMIN"):
        return True
    return getattr(membership, 'can_manage_roster', False) or False

@router.post("/org/{org_id}", response_model=CreatorResponse)
def create_creator(
    org_id: int,
    request: CreatorCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    membership = db.query(OrganizationMember).filter(
        OrganizationMember.user_id == current_user.id,
        OrganizationMember.organization_id == org_id
    ).first()
    
    if not membership:
        raise HTTPException(status_code=403, detail="Not authorized to access this organization")

    if not check_roster_permission(membership):
        raise HTTPException(status_code=403, detail="You do not have permission to manage the roster")
    
    creator = Creator(
        organization_id=org_id,
        display_name=request.display_name,
        legal_name=request.legal_name,
        email=request.email,
        roles=request.roles,
        primary_territory=request.primary_territory,
        primary_pro=request.primary_pro,
        primary_ipi=request.primary_ipi,
        hero_image_url=request.hero_image_url,
        bio=request.bio,
        spotify_url=request.spotify_url,
        apple_music_url=request.apple_music_url,
        youtube_url=request.youtube_url,
        instagram_url=request.instagram_url,
        twitter_url=request.twitter_url,
        custom_links=request.custom_links or [],
        roster_export_fields=request.roster_export_fields or [],
    )
    db.add(creator)
    db.flush()
    from ..services.audit_service import log_action
    log_action(db, org_id, current_user.id, "CREATE", "CREATOR", creator.id, creator.display_name)
    db.commit()
    db.refresh(creator)

    creative_contact = CreativeContact(
        organization_id=org_id,
        creator_id=creator.id,
        display_name=creator.display_name,
        legal_name=creator.legal_name,
        email=creator.email,
        pro=creator.primary_pro,
        ipi=creator.primary_ipi,
        publisher_name=creator.publisher_name,
        roles=creator.roles or [],
        phone=creator.phone,
        territory=creator.primary_territory,
    )
    db.add(creative_contact)
    db.commit()
    
    return {
        "id": creator.id,
        "display_name": creator.display_name,
        "legal_name": creator.legal_name,
        "email": creator.email,
        "roles": creator.roles,
        "primary_territory": creator.primary_territory,
        "primary_pro": creator.primary_pro,
        "primary_ipi": creator.primary_ipi,
        "hero_image_url": creator.hero_image_url,
        "linked_user_id": creator.linked_user_id,
        "song_count": 0,
        "avg_health_score": 0.0,
        "roster_export_fields": creator.roster_export_fields or [],
    }

@router.get("/{creator_id}", response_model=CreatorDetailResponse)
def get_creator(
    creator_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    creator = db.query(Creator).filter(Creator.id == creator_id).first()
    
    if not creator:
        raise HTTPException(status_code=404, detail="Creator not found")
    
    membership = db.query(OrganizationMember).filter(
        OrganizationMember.user_id == current_user.id,
        OrganizationMember.organization_id == creator.organization_id
    ).first()
    
    if not membership:
        raise HTTPException(status_code=403, detail="Not authorized to access this creator")
    
    song_count = db.query(func.count(SongCredit.id)).filter(
        SongCredit.creator_id == creator.id
    ).scalar() or 0
    
    avg_health = db.query(func.avg(Song.status_health_score)).join(
        SongCredit, Song.id == SongCredit.song_id
    ).filter(
        SongCredit.creator_id == creator.id
    ).scalar() or 0.0
    
    placement_count = db.query(func.count(Song.id)).join(
        SongCredit, Song.id == SongCredit.song_id
    ).filter(
        SongCredit.creator_id == creator.id,
        Song.is_paid == "Yes"
    ).scalar() or 0
    
    publisher_contact = None
    if creator.publisher_contact_id:
        pc = db.query(CreativeContact).filter(CreativeContact.id == creator.publisher_contact_id).first()
        if pc:
            publisher_contact = {"id": pc.id, "display_name": pc.display_name, "company": pc.publisher_name, "primary_role": (pc.roles or [None])[0] if pc.roles else None}
    
    admin_contact = None
    if creator.admin_contact_id:
        ac = db.query(CreativeContact).filter(CreativeContact.id == creator.admin_contact_id).first()
        if ac:
            admin_contact = {"id": ac.id, "display_name": ac.display_name, "company": ac.publisher_name, "primary_role": (ac.roles or [None])[0] if ac.roles else None}
    
    return {
        "id": creator.id,
        "display_name": creator.display_name,
        "legal_name": creator.legal_name,
        "email": creator.email,
        "roles": creator.roles,
        "primary_territory": creator.primary_territory,
        "primary_pro": creator.primary_pro,
        "primary_ipi": creator.primary_ipi,
        "hero_image_url": creator.hero_image_url,
        "linked_user_id": creator.linked_user_id,
        "song_count": song_count,
        "avg_health_score": float(avg_health) if avg_health else 0.0,
        "placement_count": placement_count,
        "publisher_contact_id": creator.publisher_contact_id,
        "publisher_contact": publisher_contact,
        "admin_contact_id": creator.admin_contact_id,
        "admin_contact": admin_contact,
        "bio": creator.bio,
        "spotify_url": creator.spotify_url,
        "apple_music_url": creator.apple_music_url,
        "youtube_url": creator.youtube_url,
        "instagram_url": creator.instagram_url,
        "twitter_url": creator.twitter_url,
        "custom_links": creator.custom_links or [],
        "roster_export_fields": creator.roster_export_fields or [],
    }

@router.put("/{creator_id}", response_model=CreatorResponse)
def update_creator(
    creator_id: int,
    request: CreatorUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    creator = db.query(Creator).filter(Creator.id == creator_id).first()
    
    if not creator:
        raise HTTPException(status_code=404, detail="Creator not found")
    
    membership = db.query(OrganizationMember).filter(
        OrganizationMember.user_id == current_user.id,
        OrganizationMember.organization_id == creator.organization_id
    ).first()
    
    if not membership:
        raise HTTPException(status_code=403, detail="Not authorized to update this creator")

    if not check_roster_permission(membership):
        raise HTTPException(status_code=403, detail="You do not have permission to manage the roster")
    
    if request.display_name is not None:
        creator.display_name = request.display_name
    if request.legal_name is not None:
        creator.legal_name = request.legal_name
    if request.email is not None:
        creator.email = request.email
    if request.roles is not None:
        creator.roles = request.roles
    if request.primary_territory is not None:
        creator.primary_territory = request.primary_territory
    if request.primary_pro is not None:
        creator.primary_pro = request.primary_pro
    if request.primary_ipi is not None:
        creator.primary_ipi = request.primary_ipi
    if request.hero_image_url is not None:
        creator.hero_image_url = request.hero_image_url
    if request.publisher_contact_id is not None:
        creator.publisher_contact_id = request.publisher_contact_id if request.publisher_contact_id != 0 else None
    if request.admin_contact_id is not None:
        creator.admin_contact_id = request.admin_contact_id if request.admin_contact_id != 0 else None
    if request.bio is not None:
        creator.bio = request.bio
    if request.spotify_url is not None:
        creator.spotify_url = request.spotify_url
    if request.apple_music_url is not None:
        creator.apple_music_url = request.apple_music_url
    if request.youtube_url is not None:
        creator.youtube_url = request.youtube_url
    if request.instagram_url is not None:
        creator.instagram_url = request.instagram_url
    if request.twitter_url is not None:
        creator.twitter_url = request.twitter_url
    if request.custom_links is not None:
        creator.custom_links = request.custom_links
    if request.roster_export_fields is not None:
        creator.roster_export_fields = request.roster_export_fields
    
    db.commit()
    db.refresh(creator)
    
    song_count = db.query(func.count(SongCredit.id)).filter(
        SongCredit.creator_id == creator.id
    ).scalar() or 0
    
    avg_health = db.query(func.avg(Song.status_health_score)).join(
        SongCredit, Song.id == SongCredit.song_id
    ).filter(
        SongCredit.creator_id == creator.id
    ).scalar() or 0.0
    
    return {
        "id": creator.id,
        "display_name": creator.display_name,
        "legal_name": creator.legal_name,
        "email": creator.email,
        "roles": creator.roles,
        "primary_territory": creator.primary_territory,
        "primary_pro": creator.primary_pro,
        "primary_ipi": creator.primary_ipi,
        "hero_image_url": creator.hero_image_url,
        "linked_user_id": creator.linked_user_id,
        "song_count": song_count,
        "avg_health_score": float(avg_health) if avg_health else 0.0,
        "roster_export_fields": creator.roster_export_fields or [],
    }


@router.delete("/{creator_id}")
def delete_creator(
    creator_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    creator = db.query(Creator).filter(Creator.id == creator_id).first()
    if not creator:
        raise HTTPException(status_code=404, detail="Creator not found")

    membership = db.query(OrganizationMember).filter(
        OrganizationMember.user_id == current_user.id,
        OrganizationMember.organization_id == creator.organization_id
    ).first()
    if not membership and not current_user.is_super_admin:
        raise HTTPException(status_code=403, detail="Not authorized")

    if not check_roster_permission(membership):
        raise HTTPException(status_code=403, detail="You do not have permission to manage the roster")

    db.query(SongCredit).filter(SongCredit.creator_id == creator_id).delete()
    db.query(WorkCredit).filter(WorkCredit.creator_id == creator_id).delete()

    from ..services.audit_service import log_action
    log_action(db, creator.organization_id, current_user.id, "DELETE", "CREATOR", creator.id, creator.display_name)
    db.delete(creator)
    db.commit()
    return {"message": "Creator deleted successfully"}


UPLOADS_DIR = Path(__file__).parent.parent / "uploads" / "creators"
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)

ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}
MAX_IMAGE_SIZE = 5 * 1024 * 1024


@router.get("/{creator_id}/image")
def serve_creator_image(
    creator_id: int,
    db: Session = Depends(get_db),
):
    creator = db.query(Creator).filter(Creator.id == creator_id).first()
    if not creator:
        raise HTTPException(status_code=404, detail="Creator not found")

    if creator.hero_image_data:
        return Response(
            content=creator.hero_image_data,
            media_type=creator.hero_image_mime or "image/jpeg",
            headers={"Cache-Control": "public, max-age=3600"}
        )

    if creator.hero_image_url and creator.hero_image_url.startswith("/uploads/"):
        filename = creator.hero_image_url.split("/")[-1]
        filepath = UPLOADS_DIR / filename
        if filepath.exists():
            mime = "image/jpeg"
            if filename.endswith(".png"):
                mime = "image/png"
            elif filename.endswith(".webp"):
                mime = "image/webp"
            elif filename.endswith(".gif"):
                mime = "image/gif"
            return Response(
                content=filepath.read_bytes(),
                media_type=mime,
                headers={"Cache-Control": "public, max-age=3600"}
            )

    raise HTTPException(status_code=404, detail="No image found")


@router.post("/{creator_id}/image")
async def upload_creator_image(
    creator_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    creator = db.query(Creator).filter(Creator.id == creator_id).first()
    if not creator:
        raise HTTPException(status_code=404, detail="Creator not found")

    membership = db.query(OrganizationMember).filter(
        OrganizationMember.user_id == current_user.id,
        OrganizationMember.organization_id == creator.organization_id
    ).first()
    if not membership:
        raise HTTPException(status_code=403, detail="Not authorized")

    if not check_roster_permission(membership):
        raise HTTPException(status_code=403, detail="You do not have permission to manage the roster")

    if file.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(status_code=400, detail="Invalid image type. Use JPEG, PNG, WebP, or GIF.")

    content = await file.read()
    if len(content) > MAX_IMAGE_SIZE:
        raise HTTPException(status_code=400, detail="Image too large. Maximum size is 5MB.")

    creator.hero_image_data = content
    creator.hero_image_mime = file.content_type
    creator.hero_image_url = f"/api/creators/{creator_id}/image"
    db.commit()
    db.refresh(creator)

    return {"hero_image_url": creator.hero_image_url}


class RosterPDFRequest(BaseModel):
    creator_ids: List[int]


@router.post("/org/{org_id}/roster-pdf")
def export_roster_pdf(
    org_id: int,
    request: RosterPDFRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    import logging
    logger = logging.getLogger("rythm")
    
    membership = db.query(OrganizationMember).filter(
        OrganizationMember.user_id == current_user.id,
        OrganizationMember.organization_id == org_id
    ).first()
    if not membership:
        raise HTTPException(status_code=403, detail="Not authorized")

    org = db.query(Organization).filter(Organization.id == org_id).first()
    org_name = org.display_name or org.name if org else "Organization"

    creators = db.query(Creator).filter(
        Creator.id.in_(request.creator_ids),
        Creator.organization_id == org_id
    ).all()
    if not creators:
        raise HTTPException(status_code=404, detail="No creators found")
    
    try:
        return _build_roster_pdf(creators, org_name, request)
    except Exception as e:
        logger.error(f"Failed to generate roster PDF: {type(e).__name__}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to generate PDF: {str(e)}")


def _build_roster_pdf(creators, org_name, request):

    import io
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image as RLImage, KeepTogether, Table, TableStyle
    from reportlab.graphics.shapes import Drawing, Circle, String

    buffer = io.BytesIO()
    page_w, page_h = letter

    sage = colors.HexColor("#5B8A72")
    dark_text = colors.HexColor("#3D4A44")
    muted_text = colors.HexColor("#7A8580")
    light_bg = colors.HexColor("#F5F7F4")
    border_color = colors.HexColor("#E0E5E2")

    class RosterTemplate:
        def on_page(self, canvas, doc):
            canvas.saveState()
            grad_steps = 20
            for i in range(grad_steps):
                frac = i / grad_steps
                r = 0.357 + frac * (0.961 - 0.357)
                g = 0.541 + frac * (0.969 - 0.541)
                b = 0.447 + frac * (0.957 - 0.447)
                step_h = (1.6*inch) / grad_steps
                y = page_h - (i+1) * step_h
                canvas.setFillColor(colors.Color(r, g, b))
                canvas.rect(0, y, page_w, step_h + 1, fill=True, stroke=False)

            canvas.setFillColor(colors.white)
            canvas.setFont("Helvetica-Bold", 22)
            canvas.drawString(0.75*inch, page_h - 0.8*inch, f"{org_name}")
            canvas.setFont("Helvetica", 11)
            canvas.drawString(0.75*inch, page_h - 1.1*inch, "Roster Brief")
            canvas.setFont("Helvetica", 8)
            canvas.drawRightString(page_w - 0.75*inch, page_h - 0.5*inch, f"{len(creators)} Creator{'s' if len(creators) != 1 else ''}")

            canvas.setFillColor(muted_text)
            canvas.setFont("Helvetica", 7)
            canvas.drawCentredString(page_w/2, 0.4*inch, f"Generated by {org_name} via Rythm Catalog Intelligence | {datetime.utcnow().strftime('%B %d, %Y')}")
            canvas.restoreState()

    doc = SimpleDocTemplate(
        buffer, pagesize=letter,
        topMargin=1.8*inch, bottomMargin=0.8*inch,
        leftMargin=0.75*inch, rightMargin=0.75*inch
    )

    name_style = ParagraphStyle('Name', fontName='Helvetica-Bold', fontSize=16, textColor=dark_text, spaceAfter=2, leading=20)
    bio_style = ParagraphStyle('Bio', fontName='Helvetica', fontSize=9, textColor=muted_text, spaceAfter=6, leading=13)
    label_style = ParagraphStyle('Label', fontName='Helvetica', fontSize=7, textColor=muted_text, spaceAfter=1, leading=9)
    link_style = ParagraphStyle('Link', fontName='Helvetica', fontSize=9, textColor=sage, spaceAfter=4, leading=12)
    role_style = ParagraphStyle('Role', fontName='Helvetica', fontSize=8, textColor=sage, spaceAfter=4, leading=10)
    pill_style = ParagraphStyle('Pill', fontName='Helvetica-Bold', fontSize=7, textColor=colors.white, leading=9, alignment=1)

    elements = []

    id_order = {cid: idx for idx, cid in enumerate(request.creator_ids)}
    creators.sort(key=lambda c: id_order.get(c.id, 999))

    link_colors = {
        'spotify_url': ('#1DB954', 'Spotify'),
        'apple_music_url': ('#FA233B', 'Apple Music'),
        'youtube_url': ('#FF0000', 'YouTube'),
        'instagram_url': ('#E1306C', 'Instagram'),
        'twitter_url': ('#000000', 'X'),
        'website_url': ('#5B8A72', 'Website'),
    }

    for idx, creator in enumerate(creators):
        card_elements = []
        export_fields = creator.roster_export_fields or []
        show_all = len(export_fields) == 0

        if idx > 0:
            card_elements.append(Spacer(1, 16))

        photo_cell = None
        if creator.hero_image_data:
            try:
                img_buf = io.BytesIO(creator.hero_image_data)
                from PIL import Image as PILImage
                pil_img = PILImage.open(img_buf)
                pil_img.verify()
                img_buf.seek(0)
                photo_cell = RLImage(img_buf, width=0.9*inch, height=0.9*inch)
            except Exception:
                photo_cell = None
        if not photo_cell and creator.hero_image_url:
            try:
                import os
                url = creator.hero_image_url
                if url.startswith('/uploads/'):
                    file_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), url.lstrip('/'))
                    if os.path.exists(file_path):
                        photo_cell = RLImage(file_path, width=0.9*inch, height=0.9*inch)
            except Exception:
                photo_cell = None

        if not photo_cell:
            d = Drawing(65, 65)
            d.add(Circle(32.5, 32.5, 30, fillColor=sage, strokeColor=colors.transparent, strokeWidth=0))
            initials = ""
            parts = creator.display_name.split()
            if len(parts) >= 2:
                initials = parts[0][0].upper() + parts[-1][0].upper()
            elif parts:
                initials = parts[0][0].upper()
            d.add(String(32.5, 25, initials, fontSize=22, fillColor=colors.white, textAnchor='middle', fontName='Helvetica-Bold'))
            photo_cell = d

        info_parts = []
        info_parts.append(Paragraph(creator.display_name, name_style))

        if creator.roles:
            role_text = " · ".join(creator.roles)
            info_parts.append(Paragraph(role_text, role_style))

        if (show_all or 'bio' in export_fields) and creator.bio:
            bio_text = creator.bio[:300] + ("..." if len(creator.bio) > 300 else "")
            info_parts.append(Paragraph(bio_text, bio_style))

        pill_cells = []
        pill_bg_colors = []

        for field_key, (bg_hex, label) in link_colors.items():
            url_val = getattr(creator, field_key, None)
            if url_val and (show_all or field_key in export_fields):
                pill_para = Paragraph(f'<a href="{url_val}" color="#FFFFFF">{label}</a>', pill_style)
                pill_cells.append(pill_para)
                pill_bg_colors.append(colors.HexColor(bg_hex))

        custom = creator.custom_links or []
        for ci, cl in enumerate(custom):
            cl_name = cl.get("name", "Link")
            cl_url = cl.get("url", "")
            cl_key = f"custom_link_{ci}"
            if cl_url and (show_all or cl_key in export_fields):
                pill_para = Paragraph(f'<a href="{cl_url}" color="#FFFFFF">{cl_name}</a>', pill_style)
                pill_cells.append(pill_para)
                pill_bg_colors.append(colors.HexColor("#7A8580"))

        if pill_cells:
            max_per_row = 5
            rows = []
            row_colors = []
            for i in range(0, len(pill_cells), max_per_row):
                row = pill_cells[i:i+max_per_row]
                rc = pill_bg_colors[i:i+max_per_row]
                while len(row) < max_per_row:
                    row.append('')
                    rc.append(colors.transparent)
                rows.append(row)
                row_colors.append(rc)

            col_w = (page_w - 2.5*inch - 1.1*inch - 12) / max_per_row
            pill_table_style = [
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('TOPPADDING', (0, 0), (-1, -1), 4),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
                ('LEFTPADDING', (0, 0), (-1, -1), 6),
                ('RIGHTPADDING', (0, 0), (-1, -1), 6),
                ('ROUNDEDCORNERS', [4, 4, 4, 4]),
            ]
            for ri, rc in enumerate(row_colors):
                for ci_idx, bg_c in enumerate(rc):
                    if bg_c != colors.transparent:
                        pill_table_style.append(('BACKGROUND', (ci_idx, ri), (ci_idx, ri), bg_c))

            pill_table = Table(rows, colWidths=[col_w]*max_per_row, style=TableStyle(pill_table_style))
            info_parts.append(Spacer(1, 4))
            info_parts.append(pill_table)

        from reportlab.platypus import TableStyle as TS
        info_cell = []
        for p in info_parts:
            info_cell.append(p)

        card_table = Table(
            [[photo_cell, info_cell]],
            colWidths=[1.1*inch, page_w - 2.5*inch - 1.1*inch],
            style=TS([
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('LEFTPADDING', (0, 0), (0, 0), 0),
                ('LEFTPADDING', (1, 0), (1, 0), 12),
                ('RIGHTPADDING', (-1, -1), (-1, -1), 0),
                ('TOPPADDING', (0, 0), (-1, -1), 0),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ])
        )
        card_elements.append(card_table)

        if idx < len(creators) - 1:
            from reportlab.graphics.shapes import Drawing as D, Line
            sep = D(page_w - 1.5*inch, 1)
            sep.add(Line(0, 0, page_w - 1.5*inch, 0, strokeColor=border_color, strokeWidth=0.5))
            card_elements.append(sep)

        elements.append(KeepTogether(card_elements))

    tmpl = RosterTemplate()
    doc.build(elements, onFirstPage=tmpl.on_page, onLaterPages=tmpl.on_page)

    buffer.seek(0)
    from starlette.responses import Response
    filename = f"{org_name.replace(' ', '_')}_Roster_Brief.pdf"
    return Response(
        content=buffer.getvalue(),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )
