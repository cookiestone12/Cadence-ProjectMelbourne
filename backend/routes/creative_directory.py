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
    existing_creator_ids = set(
        r[0] for r in db.query(CreativeContact.creator_id).filter(
            CreativeContact.organization_id == org_id,
            CreativeContact.creator_id.isnot(None),
        ).all()
    )

    created = []
    for creator in creators:
        if creator.id in existing_creator_ids:
            continue
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

    if created:
        db.commit()

    return {
        "message": f"Synced {len(created)} creator(s) to creative contacts",
        "created_count": len(created),
        "created_names": created,
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

    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, HRFlowable

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, topMargin=0.6*inch, bottomMargin=0.6*inch,
                            leftMargin=0.75*inch, rightMargin=0.75*inch)

    styles = getSampleStyleSheet()
    brand_color = colors.HexColor("#5B8A72")
    dark_text = colors.HexColor("#3D4A44")
    muted_text = colors.HexColor("#7A8580")

    title_style = ParagraphStyle('CardTitle', parent=styles['Title'], fontSize=22, textColor=dark_text, spaceAfter=4)
    subtitle_style = ParagraphStyle('CardSubtitle', parent=styles['Normal'], fontSize=12, textColor=muted_text, spaceAfter=12)
    section_style = ParagraphStyle('Section', parent=styles['Heading3'], fontSize=11, textColor=brand_color, spaceBefore=14, spaceAfter=6)
    field_label_style = ParagraphStyle('FieldLabel', parent=styles['Normal'], fontSize=9, textColor=muted_text)
    field_value_style = ParagraphStyle('FieldValue', parent=styles['Normal'], fontSize=11, textColor=dark_text, spaceAfter=4)
    footer_style = ParagraphStyle('Footer', parent=styles['Normal'], fontSize=8, textColor=muted_text, alignment=1)

    elements = []

    elements.append(Paragraph(f"CREATIVE CARD", ParagraphStyle('Header', parent=styles['Normal'], fontSize=9, textColor=brand_color, spaceAfter=2)))
    elements.append(Paragraph(contact.display_name, title_style))
    if contact.legal_name:
        elements.append(Paragraph(f"Legal: {contact.legal_name}", subtitle_style))
    if contact.roles:
        roles_text = " &bull; ".join(contact.roles)
        elements.append(Paragraph(roles_text, ParagraphStyle('Roles', parent=styles['Normal'], fontSize=10, textColor=brand_color, spaceAfter=8)))
    elements.append(HRFlowable(width="100%", color=colors.HexColor("#E0E5E2"), thickness=1, spaceAfter=8))

    def add_field(label, value):
        if value:
            elements.append(Paragraph(label, field_label_style))
            elements.append(Paragraph(str(value), field_value_style))

    elements.append(Paragraph("IDENTIFICATION", section_style))
    add_field("PRO Affiliation", contact.pro)
    add_field("IPI Number", contact.ipi)
    add_field("ISNI", contact.isni)
    add_field("Territory", contact.territory)

    if contact.publisher_name or contact.publisher_ipi or contact.publisher_pro:
        elements.append(Paragraph("PUBLISHING", section_style))
        add_field("Publisher", contact.publisher_name)
        add_field("Publisher IPI", contact.publisher_ipi)
        add_field("Publisher PRO", contact.publisher_pro)

    if contact.email or contact.phone:
        elements.append(Paragraph("CONTACT", section_style))
        add_field("Email", contact.email)
        add_field("Phone", contact.phone)

    if contact.representation_name or contact.representation_email or contact.representation_phone:
        elements.append(Paragraph("REPRESENTATION", section_style))
        add_field("Name", contact.representation_name)
        add_field("Email", contact.representation_email)
        add_field("Phone", contact.representation_phone)

    if contact.notes:
        elements.append(Paragraph("NOTES", section_style))
        elements.append(Paragraph(contact.notes, field_value_style))

    elements.append(Spacer(1, 30))
    elements.append(HRFlowable(width="100%", color=colors.HexColor("#E0E5E2"), thickness=1, spaceAfter=8))
    elements.append(Paragraph(f"Generated by {org_name} via Rythm Catalog Intelligence", footer_style))
    elements.append(Paragraph(f"Date: {datetime.utcnow().strftime('%B %d, %Y')}", footer_style))

    doc.build(elements)
    buffer.seek(0)

    safe_name = contact.display_name.replace(" ", "_").replace("/", "-")
    filename = f"Creative_Card_{safe_name}.pdf"

    return Response(
        content=buffer.read(),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )
