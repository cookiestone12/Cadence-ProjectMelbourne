from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
import io
from ..models import get_db, CreativeContact, Creator, OrganizationMember, User, Organization
from ..utils.auth import get_current_user

router = APIRouter(prefix="/api/creative-directory", tags=["creative-directory"])


def verify_org_access(user: User, org_id: int, db: Session):
    membership = db.query(OrganizationMember).filter(
        OrganizationMember.user_id == user.id,
        OrganizationMember.organization_id == org_id
    ).first()
    if not membership and not user.is_super_admin:
        raise HTTPException(status_code=403, detail="Access denied")
    return membership


class CreativeContactCreate(BaseModel):
    display_name: str
    legal_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    pro: Optional[str] = None
    ipi: Optional[str] = None
    isni: Optional[str] = None
    publisher_name: Optional[str] = None
    publisher_ipi: Optional[str] = None
    publisher_pro: Optional[str] = None
    roles: Optional[List[str]] = []
    representation_name: Optional[str] = None
    representation_email: Optional[str] = None
    representation_phone: Optional[str] = None
    territory: Optional[str] = None
    notes: Optional[str] = None


class CreativeContactUpdate(BaseModel):
    display_name: Optional[str] = None
    legal_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    pro: Optional[str] = None
    ipi: Optional[str] = None
    isni: Optional[str] = None
    publisher_name: Optional[str] = None
    publisher_ipi: Optional[str] = None
    publisher_pro: Optional[str] = None
    roles: Optional[List[str]] = None
    representation_name: Optional[str] = None
    representation_email: Optional[str] = None
    representation_phone: Optional[str] = None
    territory: Optional[str] = None
    notes: Optional[str] = None


def _contact_to_dict(contact: CreativeContact):
    return {
        "id": contact.id,
        "organization_id": contact.organization_id,
        "creator_id": contact.creator_id,
        "display_name": contact.display_name,
        "legal_name": contact.legal_name,
        "email": contact.email,
        "phone": contact.phone,
        "pro": contact.pro,
        "ipi": contact.ipi,
        "isni": contact.isni,
        "publisher_name": contact.publisher_name,
        "publisher_ipi": contact.publisher_ipi,
        "publisher_pro": contact.publisher_pro,
        "roles": contact.roles or [],
        "representation_name": contact.representation_name,
        "representation_email": contact.representation_email,
        "representation_phone": contact.representation_phone,
        "territory": contact.territory,
        "notes": contact.notes,
        "created_at": contact.created_at.isoformat() if contact.created_at else None,
        "updated_at": contact.updated_at.isoformat() if contact.updated_at else None,
    }


@router.get("/org/{org_id}")
def list_creative_contacts(
    org_id: int,
    search: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    verify_org_access(current_user, org_id, db)
    query = db.query(CreativeContact).filter(CreativeContact.organization_id == org_id)

    if search:
        query = query.filter(CreativeContact.display_name.ilike(f"%{search}%"))

    contacts = query.order_by(CreativeContact.display_name).all()
    return {"contacts": [_contact_to_dict(c) for c in contacts], "total": len(contacts)}


@router.get("/{contact_id}")
def get_creative_contact(
    contact_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    contact = db.query(CreativeContact).filter(CreativeContact.id == contact_id).first()
    if not contact:
        raise HTTPException(status_code=404, detail="Creative contact not found")
    verify_org_access(current_user, contact.organization_id, db)
    return _contact_to_dict(contact)


@router.post("/org/{org_id}")
def create_creative_contact(
    org_id: int,
    data: CreativeContactCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    verify_org_access(current_user, org_id, db)

    contact = CreativeContact(
        organization_id=org_id,
        display_name=data.display_name,
        legal_name=data.legal_name,
        email=data.email,
        phone=data.phone,
        pro=data.pro,
        ipi=data.ipi,
        isni=data.isni,
        publisher_name=data.publisher_name,
        publisher_ipi=data.publisher_ipi,
        publisher_pro=data.publisher_pro,
        roles=data.roles or [],
        representation_name=data.representation_name,
        representation_email=data.representation_email,
        representation_phone=data.representation_phone,
        territory=data.territory,
        notes=data.notes,
    )
    db.add(contact)
    db.commit()
    db.refresh(contact)
    return _contact_to_dict(contact)


@router.put("/{contact_id}")
def update_creative_contact(
    contact_id: int,
    data: CreativeContactUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    contact = db.query(CreativeContact).filter(CreativeContact.id == contact_id).first()
    if not contact:
        raise HTTPException(status_code=404, detail="Creative contact not found")
    verify_org_access(current_user, contact.organization_id, db)

    for field, value in data.dict(exclude_unset=True).items():
        setattr(contact, field, value)

    if contact.creator_id:
        linked_creator = db.query(Creator).filter(Creator.id == contact.creator_id).first()
        if linked_creator:
            updated = data.dict(exclude_unset=True)
            sync_map = {
                'display_name': 'display_name',
                'legal_name': 'legal_name',
                'email': 'email',
                'phone': 'phone',
                'pro': 'primary_pro',
                'ipi': 'primary_ipi',
                'roles': 'roles',
                'territory': 'primary_territory',
            }
            for contact_field, creator_field in sync_map.items():
                if contact_field in updated:
                    setattr(linked_creator, creator_field, updated[contact_field])

    db.commit()
    db.refresh(contact)
    return _contact_to_dict(contact)


@router.delete("/{contact_id}")
def delete_creative_contact(
    contact_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    contact = db.query(CreativeContact).filter(CreativeContact.id == contact_id).first()
    if not contact:
        raise HTTPException(status_code=404, detail="Creative contact not found")
    verify_org_access(current_user, contact.organization_id, db)

    db.delete(contact)
    db.commit()
    return {"message": "Creative contact deleted successfully"}


@router.post("/org/{org_id}/from-creator/{creator_id}")
def create_from_creator(
    org_id: int,
    creator_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    verify_org_access(current_user, org_id, db)

    creator = db.query(Creator).filter(
        Creator.id == creator_id,
        Creator.organization_id == org_id,
    ).first()
    if not creator:
        raise HTTPException(status_code=404, detail="Creator not found in this organization")

    existing = db.query(CreativeContact).filter(
        CreativeContact.organization_id == org_id,
        CreativeContact.creator_id == creator_id,
    ).first()
    if existing:
        return _contact_to_dict(existing)

    contact = CreativeContact(
        organization_id=org_id,
        creator_id=creator.id,
        display_name=creator.display_name,
        legal_name=creator.legal_name,
        email=creator.email,
        phone=creator.phone,
        pro=creator.primary_pro,
        ipi=creator.primary_ipi,
        publisher_name=creator.publisher_name,
        roles=creator.roles or [],
        territory=creator.primary_territory,
    )
    db.add(contact)
    db.commit()
    db.refresh(contact)
    return _contact_to_dict(contact)


@router.get("/org/{org_id}/sync-creators")
def sync_creators(
    org_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    verify_org_access(current_user, org_id, db)

    creators = db.query(Creator).filter(Creator.organization_id == org_id).all()

    existing_contacts = {
        c.creator_id: c for c in db.query(CreativeContact).filter(
            CreativeContact.organization_id == org_id,
            CreativeContact.creator_id.isnot(None),
        ).all()
    }

    created = []
    updated = []
    for creator in creators:
        if creator.id in existing_contacts:
            contact = existing_contacts[creator.id]
            contact.display_name = creator.display_name
            contact.legal_name = creator.legal_name
            contact.email = creator.email
            contact.phone = creator.phone
            contact.pro = creator.primary_pro
            contact.ipi = creator.primary_ipi
            contact.publisher_name = creator.publisher_name
            contact.roles = creator.roles or []
            contact.territory = creator.primary_territory
            updated.append(creator.display_name)
        else:
            contact = CreativeContact(
                organization_id=org_id,
                creator_id=creator.id,
                display_name=creator.display_name,
                legal_name=creator.legal_name,
                email=creator.email,
                phone=creator.phone,
                pro=creator.primary_pro,
                ipi=creator.primary_ipi,
                publisher_name=creator.publisher_name,
                roles=creator.roles or [],
                territory=creator.primary_territory,
            )
            db.add(contact)
            created.append(creator.display_name)

    if created or updated:
        db.commit()

    return {
        "message": f"Synced {len(created)} new, {len(updated)} updated creator(s) to creative contacts",
        "created_count": len(created),
        "updated_count": len(updated),
        "created_names": created,
        "updated_names": updated,
    }


@router.get("/{contact_id}/pdf")
def download_creative_card_pdf(
    contact_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    contact = db.query(CreativeContact).filter(CreativeContact.id == contact_id).first()
    if not contact:
        raise HTTPException(status_code=404, detail="Creative contact not found")
    verify_org_access(current_user, contact.organization_id, db)

    org = db.query(Organization).filter(Organization.id == contact.organization_id).first()
    org_name = org.display_name or org.name if org else "Rythm"

    hero_image_data = None
    if contact.creator_id:
        linked_creator = db.query(Creator).filter(Creator.id == contact.creator_id).first()
        if linked_creator and linked_creator.hero_image_data:
            hero_image_data = linked_creator.hero_image_data

    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import inch, mm
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, KeepTogether
    from reportlab.graphics.shapes import Drawing, Rect, Circle, String, Line
    from reportlab.graphics import renderPDF

    buffer = io.BytesIO()
    page_w, page_h = letter

    class CreativeCardTemplate:
        def __init__(self, org_name_val, contact_name):
            self.org_name = org_name_val
            self.contact_name = contact_name

        def on_page(self, canvas, doc):
            canvas.saveState()
            sage = colors.HexColor("#5B8A72")
            light_sage = colors.HexColor("#F5F7F4")
            canvas.setFillColor(sage)
            canvas.rect(0, page_h - 2.4*inch, page_w, 2.4*inch, fill=True, stroke=False)
            grad_steps = 20
            for i in range(grad_steps):
                frac = i / grad_steps
                r = 0.357 + frac * (0.961 - 0.357)
                g = 0.541 + frac * (0.969 - 0.541)
                b = 0.447 + frac * (0.957 - 0.447)
                step_h = (2.4*inch) / grad_steps
                y = page_h - (i+1) * step_h
                canvas.setFillColor(colors.Color(r, g, b))
                canvas.rect(0, y, page_w, step_h + 1, fill=True, stroke=False)

            canvas.setFillColor(colors.white)
            canvas.setFont("Helvetica", 9)
            canvas.drawString(0.75*inch, page_h - 0.5*inch, "CREATIVE CARD")
            canvas.setFont("Helvetica", 8)
            canvas.drawRightString(page_w - 0.75*inch, page_h - 0.5*inch, self.org_name)

            canvas.setFillColor(colors.HexColor("#E0E5E2"))
            canvas.setLineWidth(0.5)
            canvas.setStrokeColor(colors.HexColor("#E0E5E2"))
            canvas.line(0.75*inch, 0.75*inch, page_w - 0.75*inch, 0.75*inch)

            canvas.setFillColor(colors.HexColor("#7A8580"))
            canvas.setFont("Helvetica", 7)
            footer_text = f"Generated by {self.org_name} via Rythm Catalog Intelligence"
            canvas.drawCentredString(page_w/2, 0.55*inch, footer_text)
            canvas.drawCentredString(page_w/2, 0.4*inch, f"Date: {datetime.utcnow().strftime('%B %d, %Y')}")
            canvas.restoreState()

    doc = SimpleDocTemplate(
        buffer, pagesize=letter,
        topMargin=2.6*inch, bottomMargin=1.0*inch,
        leftMargin=0.75*inch, rightMargin=0.75*inch
    )

    sage_hex = "#5B8A72"
    dark_hex = "#3D4A44"
    muted_hex = "#7A8580"
    sage = colors.HexColor(sage_hex)
    dark_text = colors.HexColor(dark_hex)
    muted_text = colors.HexColor(muted_hex)

    name_style = ParagraphStyle('Name', fontName='Helvetica-Bold', fontSize=28, textColor=colors.white, spaceAfter=2, leading=34)
    legal_style = ParagraphStyle('Legal', fontName='Helvetica', fontSize=12, textColor=colors.Color(1, 1, 1, 0.8), spaceAfter=6)
    roles_style = ParagraphStyle('Roles', fontName='Helvetica', fontSize=10, textColor=colors.Color(1, 1, 1, 0.7), spaceAfter=0)
    section_style = ParagraphStyle('Section', fontName='Helvetica-Bold', fontSize=10, textColor=sage, spaceBefore=18, spaceAfter=8, leading=14)
    label_style = ParagraphStyle('Label', fontName='Helvetica', fontSize=8, textColor=muted_text, spaceAfter=1, leading=10)
    value_style = ParagraphStyle('Value', fontName='Helvetica-Bold', fontSize=11, textColor=dark_text, spaceAfter=8, leading=14)
    notes_style = ParagraphStyle('Notes', fontName='Helvetica', fontSize=10, textColor=dark_text, spaceAfter=6, leading=14)

    elements = []

    has_photo = hero_image_data is not None
    if has_photo:
        try:
            img_buffer = io.BytesIO(hero_image_data)
            from PIL import Image as PILImage
            pil_img = PILImage.open(img_buffer)
            img_w, img_h = pil_img.size
            img_buffer.seek(0)

            photo_size = 1.3*inch
            photo = Image(img_buffer, width=photo_size, height=photo_size)
            elements.append(photo)
            elements.append(Spacer(1, 8))
        except Exception:
            has_photo = False

    if not has_photo:
        d = Drawing(80, 80)
        d.add(Circle(40, 40, 38, fillColor=colors.Color(1, 1, 1, 0.2), strokeColor=colors.Color(1, 1, 1, 0.4), strokeWidth=1.5))
        initials = ""
        parts = contact.display_name.split()
        if len(parts) >= 2:
            initials = parts[0][0].upper() + parts[-1][0].upper()
        elif parts:
            initials = parts[0][0].upper()
        d.add(String(40, 30, initials, fontName='Helvetica-Bold', fontSize=28, fillColor=colors.white, textAnchor='middle'))
        elements.append(d)
        elements.append(Spacer(1, 8))

    elements.append(Paragraph(contact.display_name, name_style))
    if contact.legal_name:
        elements.append(Paragraph(contact.legal_name, legal_style))
    if contact.roles:
        roles_text = " &bull; ".join(r.upper() for r in contact.roles)
        elements.append(Paragraph(roles_text, roles_style))

    elements.append(Spacer(1, 6))

    def add_section(title, fields):
        items = [(l, v) for l, v in fields if v]
        if not items:
            return
        elements.append(Paragraph(title, section_style))
        for label, val in items:
            elements.append(Paragraph(label, label_style))
            elements.append(Paragraph(str(val), value_style))

    add_section("IDENTIFICATION", [
        ("PRO Affiliation", contact.pro),
        ("IPI Number", contact.ipi),
        ("ISNI", contact.isni),
        ("Territory", contact.territory),
    ])

    add_section("PUBLISHING", [
        ("Publisher", contact.publisher_name),
        ("Publisher IPI", contact.publisher_ipi),
        ("Publisher PRO", contact.publisher_pro),
    ])

    add_section("CONTACT", [
        ("Email", contact.email),
        ("Phone", contact.phone),
    ])

    add_section("REPRESENTATION", [
        ("Name", contact.representation_name),
        ("Email", contact.representation_email),
        ("Phone", contact.representation_phone),
    ])

    if contact.notes:
        elements.append(Paragraph("NOTES", section_style))
        elements.append(Paragraph(contact.notes, notes_style))

    template = CreativeCardTemplate(org_name, contact.display_name)
    doc.build(elements, onFirstPage=template.on_page, onLaterPages=template.on_page)
    buffer.seek(0)

    safe_name = contact.display_name.replace(" ", "_").replace("/", "-")
    filename = f"Creative_Card_{safe_name}.pdf"

    return Response(
        content=buffer.read(),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )
