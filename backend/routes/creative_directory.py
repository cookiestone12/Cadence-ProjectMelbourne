from fastapi import APIRouter, Depends, HTTPException, Query, File, UploadFile
from fastapi.responses import Response
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
import io
from ..models import get_db, CreativeContact, Creator, OrganizationMember, User, Organization, SharedContactLink, ClientSharedContact, SharedItem
from ..utils.auth import get_current_user

ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}
MAX_IMAGE_SIZE = 5 * 1024 * 1024

router = APIRouter(prefix="/api/creative-directory", tags=["Creative Directory"])
public_router = APIRouter(prefix="/api/public", tags=["Creative Directory"])


def verify_org_access(user: User, org_id: int, db: Session):
    membership = db.query(OrganizationMember).filter(
        OrganizationMember.user_id == user.id,
        OrganizationMember.organization_id == org_id
    ).first()
    if not membership and not user.is_super_admin:
        raise HTTPException(status_code=403, detail="Access denied")
    return membership


def verify_private_access(contact: CreativeContact, user: User):
    if contact.is_private and contact.created_by_user_id != user.id:
        raise HTTPException(status_code=403, detail="This is a private contact")


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
    is_private: Optional[bool] = False


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
    is_private: Optional[bool] = None


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
        "photo_url": contact.photo_url,
        "is_private": bool(contact.is_private) if contact.is_private else False,
        "created_by_user_id": contact.created_by_user_id,
        "created_at": contact.created_at.isoformat() if contact.created_at else None,
        "updated_at": contact.updated_at.isoformat() if contact.updated_at else None,
    }


@router.get(
    "/org/{org_id}",
    summary="List the org's creative-directory contacts",
    description=(
        "Returns every CreativeContact in the organization — the directory "
        "of writers, producers, A&Rs, attorneys, and other industry "
        "contacts curated by the org. Supports text search and tag filtering "
        "for the directory list view.\n\n"
        "**Path parameter:** `org_id` — Organization ID.\n"
        "**Optional query:** `q` (substring on name/email/company), "
        "`tag` (single tag slug), `linked_creator_id`, `limit`, `offset`.\n\n"
        "**Auth:** Bearer JWT. Caller must be a member of the organization.\n\n"
        "**Response:** `{ total, contacts: [{id, name, role, company, "
        "email, phone, tags, photo_url, pro_society, ipi, linked_creator_id, "
        "shared_to_client, updated_at}] }`."
    ),
)
def list_creative_contacts(
    org_id: int,
    search: Optional[str] = Query(None),
    visibility: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    verify_org_access(current_user, org_id, db)
    from sqlalchemy import or_
    query = db.query(CreativeContact).filter(CreativeContact.organization_id == org_id)

    if visibility == "private":
        query = query.filter(
            CreativeContact.is_private == True,
            CreativeContact.created_by_user_id == current_user.id,
        )
    elif visibility == "org":
        query = query.filter(CreativeContact.is_private == False)
    else:
        query = query.filter(
            or_(
                CreativeContact.is_private == False,
                CreativeContact.created_by_user_id == current_user.id,
            )
        )

    if search:
        query = query.filter(CreativeContact.display_name.ilike(f"%{search}%"))

    contacts = query.order_by(CreativeContact.display_name).all()
    return {"contacts": [_contact_to_dict(c) for c in contacts], "total": len(contacts)}


@router.get(
    "/{contact_id}",
    summary="Get a single creative-directory contact",
    description=(
        "Returns the full CreativeContact record including bio, social "
        "handles, PRO/IPI metadata, tags, share state, and the optional "
        "`linked_creator_id` if the contact mirrors a Creator in the org's "
        "roster.\n\n"
        "**Path parameter:** `contact_id` — CreativeContact id.\n\n"
        "**Auth:** Bearer JWT. Caller must be a member of the contact's "
        "organization.\n\n"
        "**Response:** the full contact object (see list endpoint for "
        "fields, plus `bio`, `socials`, `notes`, `created_at`)."
    ),
)
def get_creative_contact(
    contact_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    contact = db.query(CreativeContact).filter(CreativeContact.id == contact_id).first()
    if not contact:
        raise HTTPException(status_code=404, detail="Creative contact not found")
    verify_org_access(current_user, contact.organization_id, db)
    verify_private_access(contact, current_user)
    return _contact_to_dict(contact)


@router.post(
    "/org/{org_id}",
    summary="Create a creative-directory contact",
    description=(
        "Adds a new contact to the org's directory. Use the "
        "`from-creator` endpoint instead when mirroring a Creator that "
        "already exists in the roster, and `sync-creators` to bulk-import.\n\n"
        "**Path parameter:** `org_id` — Organization ID.\n"
        "**Body (`CreativeContactCreate`):** `name` (required), `role`, "
        "`company`, `email`, `phone`, `bio`, `socials`, `pro_society`, "
        "`ipi`, `tags`, `notes`, `linked_creator_id`.\n\n"
        "**Auth:** Bearer JWT. Caller must be a member of the organization.\n\n"
        "**Response:** the freshly created contact object."
    ),
)
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
        is_private=data.is_private or False,
        created_by_user_id=current_user.id,
    )
    db.add(contact)
    db.commit()
    db.refresh(contact)
    return _contact_to_dict(contact)


@router.put(
    "/{contact_id}",
    summary="Update a creative-directory contact",
    description=(
        "Patches editable fields on a CreativeContact. Use the dedicated "
        "image endpoints to change `photo_url`.\n\n"
        "**Path parameter:** `contact_id` — CreativeContact id.\n"
        "**Body (`CreativeContactUpdate`):** any subset of the writable "
        "fields from the create endpoint. Unspecified fields are untouched.\n\n"
        "**Auth:** Bearer JWT. Caller must be a member of the contact's "
        "organization.\n\n"
        "**Response:** the updated contact object."
    ),
)
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
    verify_private_access(contact, current_user)

    update_data = data.dict(exclude_unset=True)
    if 'is_private' in update_data:
        if contact.created_by_user_id is not None and contact.created_by_user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Only the contact owner can change privacy settings")
        if contact.created_by_user_id is None:
            contact.created_by_user_id = current_user.id

    for field, value in update_data.items():
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


@router.delete(
    "/{contact_id}",
    summary="Delete a creative-directory contact",
    description=(
        "Hard-deletes the CreativeContact and any associated client share "
        "rows. The linked Creator (if any) is preserved.\n\n"
        "**Path parameter:** `contact_id` — CreativeContact id.\n\n"
        "**Auth:** Bearer JWT. Caller must be a member of the contact's "
        "organization.\n\n"
        "**Response:** `{ message: \"Contact deleted\" }`."
    ),
)
def delete_creative_contact(
    contact_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    contact = db.query(CreativeContact).filter(CreativeContact.id == contact_id).first()
    if not contact:
        raise HTTPException(status_code=404, detail="Creative contact not found")
    verify_org_access(current_user, contact.organization_id, db)
    verify_private_access(contact, current_user)

    db.delete(contact)
    db.commit()
    return {"message": "Creative contact deleted successfully"}


@router.get(
    "/{contact_id}/image",
    summary="Stream a contact's profile image",
    description=(
        "Serves the binary image data behind the contact's `photo_url`. "
        "Used by the directory UI when the photo is stored privately and "
        "must be proxied with auth instead of fetched directly.\n\n"
        "**Path parameter:** `contact_id` — CreativeContact id.\n\n"
        "**Auth:** Bearer JWT. Caller must be a member of the contact's "
        "organization.\n\n"
        "**Response:** the image bytes with the appropriate `Content-Type`."
    ),
)
def serve_contact_image(
    contact_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    contact = db.query(CreativeContact).filter(CreativeContact.id == contact_id).first()
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")
    verify_org_access(current_user, contact.organization_id, db)
    verify_private_access(contact, current_user)

    if contact.photo_data:
        return Response(
            content=contact.photo_data,
            media_type=contact.photo_mime or "image/jpeg",
            headers={"Cache-Control": "public, max-age=3600"},
        )

    raise HTTPException(status_code=404, detail="No image found")


@router.post(
    "/{contact_id}/image",
    summary="Upload or replace a contact's profile image",
    description=(
        "Multipart upload of a new profile photo. The file is persisted to "
        "the configured object store and `photo_url` is updated to the "
        "resulting URL. Replaces any existing photo.\n\n"
        "**Path parameter:** `contact_id` — CreativeContact id.\n"
        "**Body (multipart/form-data):** `file` — the image (PNG/JPEG).\n\n"
        "**Auth:** Bearer JWT. Caller must be a member of the contact's "
        "organization.\n\n"
        "**Response:** `{ photo_url }`."
    ),
)
async def upload_contact_image(
    contact_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    contact = db.query(CreativeContact).filter(CreativeContact.id == contact_id).first()
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")
    verify_org_access(current_user, contact.organization_id, db)
    verify_private_access(contact, current_user)

    if file.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(status_code=400, detail="Invalid image type. Use JPEG, PNG, WebP, or GIF.")

    content = await file.read()
    if len(content) > MAX_IMAGE_SIZE:
        raise HTTPException(status_code=400, detail="Image too large. Maximum size is 5MB.")

    contact.photo_data = content
    contact.photo_mime = file.content_type
    contact.photo_url = f"/api/creative-directory/{contact_id}/image"
    db.commit()

    return {"photo_url": contact.photo_url}


@router.delete(
    "/{contact_id}/image",
    summary="Delete a contact's profile image",
    description=(
        "Removes the contact's photo from object storage and clears "
        "`photo_url`.\n\n"
        "**Path parameter:** `contact_id` — CreativeContact id.\n\n"
        "**Auth:** Bearer JWT. Caller must be a member of the contact's "
        "organization.\n\n"
        "**Response:** `{ message: \"Image deleted\" }`."
    ),
)
def delete_contact_image(
    contact_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    contact = db.query(CreativeContact).filter(CreativeContact.id == contact_id).first()
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")
    verify_org_access(current_user, contact.organization_id, db)
    verify_private_access(contact, current_user)

    contact.photo_data = None
    contact.photo_mime = None
    contact.photo_url = None
    db.commit()

    return {"message": "Photo removed"}


@router.post(
    "/org/{org_id}/from-creator/{creator_id}",
    summary="Mirror a Creator into the creative directory",
    description=(
        "Creates a CreativeContact whose fields are pre-filled from an "
        "existing Creator in the roster (name, photo, contact info, "
        "PRO/IPI), and sets `linked_creator_id` so future edits to either "
        "side can be kept in sync.\n\n"
        "**Path parameters:** `org_id` — Organization ID; `creator_id` — "
        "Creator to mirror.\n\n"
        "**Auth:** Bearer JWT. Caller must be a member of the organization.\n\n"
        "**Response:** the created CreativeContact object."
    ),
)
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
        created_by_user_id=current_user.id,
    )
    db.add(contact)
    db.commit()
    db.refresh(contact)
    return _contact_to_dict(contact)


@router.get(
    "/org/{org_id}/sync-creators",
    summary="Bulk-sync the creative directory from the Creator roster",
    description=(
        "Walks every Creator in the org and ensures a corresponding "
        "CreativeContact exists with `linked_creator_id` set. New contacts "
        "are created, existing linked contacts have their core fields "
        "refreshed from the Creator. Idempotent.\n\n"
        "**Path parameter:** `org_id` — Organization ID.\n\n"
        "**Auth:** Bearer JWT. Caller must be a member of the organization.\n\n"
        "**Response:** `{ message, created_count, created_names: [...], "
        "updated_count, updated_names: [...] }`."
    ),
)
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
                created_by_user_id=current_user.id,
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


class ShareContactRequest(BaseModel):
    recipient_email: str
    recipient_name: Optional[str] = None
    message: Optional[str] = None
    subject: Optional[str] = None
    include_pdf: Optional[bool] = True


@router.post(
    "/{contact_id}/share",
    summary="Email a contact's card to one or more recipients",
    description=(
        "Renders the contact card as HTML/PDF and emails it (via Resend) "
        "to the supplied addresses. Sender is the calling user's display "
        "name on behalf of the organization.\n\n"
        "**Path parameter:** `contact_id` — CreativeContact id.\n"
        "**Body:** `{ emails: string[], subject?, message? }`.\n\n"
        "**Auth:** Bearer JWT. Caller must be a member of the contact's "
        "organization.\n\n"
        "**Response:** `{ success: true, message }`."
    ),
)
def share_contact_card(
    contact_id: int,
    data: ShareContactRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    contact = db.query(CreativeContact).filter(CreativeContact.id == contact_id).first()
    if not contact:
        raise HTTPException(status_code=404, detail="Creative contact not found")
    verify_org_access(current_user, contact.organization_id, db)
    verify_private_access(contact, current_user)

    from ..templates.email_templates import share_contact_card as share_template
    from ..services.email_provider import get_email_provider

    sender_name = getattr(current_user, 'full_name', None) or current_user.username
    roles_str = ", ".join(contact.roles) if contact.roles else ""

    html_body = share_template(
        sender_name=sender_name,
        contact_name=contact.display_name,
        contact_role=roles_str,
        contact_email=contact.email or "",
        contact_phone=contact.phone or "",
        contact_company=contact.publisher_name or "",
        message=data.message or "",
    )

    attachments = []
    if data.include_pdf:
        try:
            org = db.query(Organization).filter(Organization.id == contact.organization_id).first()
            org_name = org.display_name or org.name if org else "Cadence"
            pdf_response = download_creative_card_pdf(contact_id, db, current_user)
            if hasattr(pdf_response, 'body'):
                import base64
                pdf_b64 = base64.b64encode(pdf_response.body).decode('utf-8')
                safe_name = contact.display_name.replace(" ", "_").replace("/", "-")
                attachments.append({
                    "filename": f"Creative_Card_{safe_name}.pdf",
                    "content": pdf_b64,
                })
        except Exception:
            pass

    email_subject = data.subject or f"Contact Shared: {contact.display_name}"
    provider = get_email_provider()
    success = provider.send_email(
        to=data.recipient_email,
        subject=email_subject,
        html_body=html_body,
        attachments=attachments if attachments else None,
    )

    if not success:
        raise HTTPException(status_code=500, detail="Failed to send email")

    return {"success": True, "message": f"Contact card shared with {data.recipient_email}"}


@router.get(
    "/{contact_id}/pro-info",
    summary="Get the contact's PRO / publisher info card",
    description=(
        "Returns a structured + plain-text snapshot of the contact's "
        "PRO/IPI/publisher metadata, ready to paste into a split sheet, "
        "email, or licensing form.\n\n"
        "**Path parameter:** `contact_id` — CreativeContact id.\n\n"
        "**Auth:** Bearer JWT. Caller must be a member of the contact's "
        "organization.\n\n"
        "**Response:** `{ data: { name, ipi, pro_society, "
        "publisher_name, publisher_ipi, publisher_pro }, text }`."
    ),
)
def get_pro_info(
    contact_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    contact = db.query(CreativeContact).filter(CreativeContact.id == contact_id).first()
    if not contact:
        raise HTTPException(status_code=404, detail="Creative contact not found")
    verify_org_access(current_user, contact.organization_id, db)
    verify_private_access(contact, current_user)

    lines = [contact.display_name]
    if contact.pro:
        lines.append(f"PRO: {contact.pro}")
    if contact.ipi:
        lines.append(f"IPI: {contact.ipi}")
    if contact.publisher_name:
        lines.append(f"Publisher: {contact.publisher_name}")
    if contact.publisher_ipi:
        lines.append(f"Publisher IPI: {contact.publisher_ipi}")
    if contact.publisher_pro:
        lines.append(f"Publisher PRO: {contact.publisher_pro}")

    return {
        "text": "\n".join(lines),
        "data": {
            "name": contact.display_name,
            "pro": contact.pro,
            "ipi": contact.ipi,
            "publisher_name": contact.publisher_name,
            "publisher_ipi": contact.publisher_ipi,
            "publisher_pro": contact.publisher_pro,
        }
    }


class QuickShareProRequest(BaseModel):
    recipient_email: str
    message: Optional[str] = None


@router.post(
    "/{contact_id}/quick-share-pro",
    summary="Email the contact's PRO/publisher info",
    description=(
        "Convenience wrapper around `/share` that emails just the formatted "
        "PRO info text (from `/pro-info`) to the supplied recipients.\n\n"
        "**Path parameter:** `contact_id` — CreativeContact id.\n"
        "**Body:** `{ emails: string[], subject?, message? }`.\n\n"
        "**Auth:** Bearer JWT. Caller must be a member of the contact's "
        "organization.\n\n"
        "**Response:** `{ success: true, message }`."
    ),
)
def quick_share_pro_info(
    contact_id: int,
    data: QuickShareProRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    contact = db.query(CreativeContact).filter(CreativeContact.id == contact_id).first()
    if not contact:
        raise HTTPException(status_code=404, detail="Creative contact not found")
    verify_org_access(current_user, contact.organization_id, db)
    verify_private_access(contact, current_user)

    from ..services.email_provider import get_email_provider

    sender_name = getattr(current_user, 'full_name', None) or current_user.username
    pro_lines = []
    if contact.pro:
        pro_lines.append(f"<b>PRO:</b> {contact.pro}")
    if contact.ipi:
        pro_lines.append(f"<b>IPI:</b> {contact.ipi}")
    if contact.publisher_name:
        pro_lines.append(f"<b>Publisher:</b> {contact.publisher_name}")
    if contact.publisher_ipi:
        pro_lines.append(f"<b>Publisher IPI:</b> {contact.publisher_ipi}")
    if contact.publisher_pro:
        pro_lines.append(f"<b>Publisher PRO:</b> {contact.publisher_pro}")

    html_body = f"""
    <div style="font-family: Arial, sans-serif; max-width: 500px; margin: 0 auto;">
        <p>{sender_name} shared PRO information for <b>{contact.display_name}</b>:</p>
        <div style="background: #f5f7f4; border-radius: 8px; padding: 16px; margin: 16px 0;">
            <h3 style="margin: 0 0 12px 0; color: #3D4A44;">{contact.display_name}</h3>
            {'<br>'.join(pro_lines) if pro_lines else '<em>No PRO details available</em>'}
        </div>
        {f'<p style="color: #7A8580;">{data.message}</p>' if data.message else ''}
        <hr style="border: none; border-top: 1px solid #e0e5e2; margin: 20px 0;">
        <p style="font-size: 12px; color: #7A8580;">Sent via Cadence</p>
    </div>
    """

    provider = get_email_provider()
    success = provider.send_email(
        to=data.recipient_email,
        subject=f"PRO Info: {contact.display_name}",
        html_body=html_body,
    )

    if not success:
        raise HTTPException(status_code=500, detail="Failed to send email")

    return {"success": True, "message": f"PRO info shared with {data.recipient_email}"}


@router.get(
    "/{contact_id}/pdf",
    summary="Download the contact's profile as a branded PDF card",
    description=(
        "Renders the contact's profile (photo, role, contact info, PRO "
        "details, bio) into a one-page PDF that follows the org's branding "
        "and streams it as an attachment.\n\n"
        "**Path parameter:** `contact_id` — CreativeContact id.\n\n"
        "**Auth:** Bearer JWT. Caller must be a member of the contact's "
        "organization.\n\n"
        "**Response:** `application/pdf` streaming download."
    ),
)
def download_creative_card_pdf(
    contact_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    contact = db.query(CreativeContact).filter(CreativeContact.id == contact_id).first()
    if not contact:
        raise HTTPException(status_code=404, detail="Creative contact not found")
    verify_org_access(current_user, contact.organization_id, db)
    verify_private_access(contact, current_user)

    org = db.query(Organization).filter(Organization.id == contact.organization_id).first()
    org_name = org.display_name or org.name if org else "Cadence"

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
            footer_text = f"Generated by {self.org_name} via Cadence Catalog Intelligence"
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


class BulkShareRequest(BaseModel):
    contact_ids: List[int]
    recipient_email: str
    recipient_name: Optional[str] = None
    message: Optional[str] = None
    subject: Optional[str] = None
    include_pdf: Optional[bool] = True


@router.post(
    "/org/{org_id}/bulk-share",
    summary="Email a batch of directory contacts to recipients",
    description=(
        "Sends a single combined email containing several contact cards "
        "to the supplied addresses. Each recipient gets one email with "
        "every selected contact rendered inline.\n\n"
        "**Path parameter:** `org_id` — Organization ID.\n"
        "**Body:** `{ contact_ids: int[], emails: string[], subject?, "
        "message? }`.\n\n"
        "**Auth:** Bearer JWT. Caller must be a member of the organization.\n\n"
        "**Response:** `{ success: true, message }`."
    ),
)
def bulk_share_contacts(
    org_id: int,
    data: BulkShareRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    verify_org_access(current_user, org_id, db)
    contacts = db.query(CreativeContact).filter(
        CreativeContact.id.in_(data.contact_ids),
        CreativeContact.organization_id == org_id,
    ).all()
    if not contacts:
        raise HTTPException(status_code=404, detail="No contacts found")
    contacts = [c for c in contacts if not c.is_private or c.created_by_user_id == current_user.id]
    if not contacts:
        raise HTTPException(status_code=403, detail="No shareable contacts found")

    from ..templates.email_templates import share_contact_card as share_template
    from ..services.email_provider import get_email_provider
    import base64

    sender_name = getattr(current_user, 'full_name', None) or current_user.username
    contact_names = ", ".join(c.display_name for c in contacts)

    summary_lines = []
    for c in contacts:
        roles_str = ", ".join(c.roles) if c.roles else ""
        line = f"<b>{c.display_name}</b>"
        if roles_str:
            line += f" — {roles_str}"
        if c.email:
            line += f" ({c.email})"
        summary_lines.append(line)

    html_body = share_template(
        sender_name=sender_name,
        contact_name=contact_names,
        contact_role=f"{len(contacts)} contacts shared",
        contact_email="",
        contact_phone="",
        contact_company="",
        message=(data.message or "") + "<br><br><b>Contacts included:</b><br>" + "<br>".join(summary_lines),
    )

    attachments = []
    if data.include_pdf:
        for contact in contacts:
            try:
                pdf_response = download_creative_card_pdf(contact.id, db, current_user)
                if hasattr(pdf_response, 'body'):
                    pdf_b64 = base64.b64encode(pdf_response.body).decode('utf-8')
                    safe_name = contact.display_name.replace(" ", "_").replace("/", "-")
                    attachments.append({
                        "filename": f"Creative_Card_{safe_name}.pdf",
                        "content": pdf_b64,
                    })
            except Exception:
                pass

    email_subject = data.subject or f"Creative Cards: {contact_names}"
    provider = get_email_provider()
    success = provider.send_email(
        to=data.recipient_email,
        subject=email_subject,
        html_body=html_body,
        attachments=attachments if attachments else None,
    )

    if not success:
        raise HTTPException(status_code=500, detail="Failed to send email")

    return {"success": True, "message": f"{len(contacts)} contact cards shared with {data.recipient_email}"}


class ShareLinkRequest(BaseModel):
    contact_ids: List[int]
    expires_in_days: Optional[int] = 7


@router.post(
    "/org/{org_id}/share-link",
    summary="Mint a public share link for a set of contacts",
    description=(
        "Creates a tokenised, optionally expiring URL that anyone can use "
        "(no auth) to view a curated subset of the org's directory in a "
        "read-only public page.\n\n"
        "**Path parameter:** `org_id` — Organization ID.\n"
        "**Body:** `{ contact_ids: int[], expires_in_days?: int }`. "
        "`expires_in_days` defaults to 30; pass `null` for no expiry.\n\n"
        "**Auth:** Bearer JWT. Caller must be a member of the organization.\n\n"
        "**Response:** `{ success: true, token, contact_count, expires_at }`. "
        "Public URL is `/share/directory/<token>`."
    ),
)
def create_share_link(
    org_id: int,
    data: ShareLinkRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    verify_org_access(current_user, org_id, db)
    contacts = db.query(CreativeContact).filter(
        CreativeContact.id.in_(data.contact_ids),
        CreativeContact.organization_id == org_id,
    ).all()
    if not contacts:
        raise HTTPException(status_code=404, detail="No contacts found")
    contacts = [c for c in contacts if not c.is_private or c.created_by_user_id == current_user.id]
    if not contacts:
        raise HTTPException(status_code=403, detail="No shareable contacts found")

    import uuid
    from datetime import timedelta
    token = uuid.uuid4().hex
    expires_at = datetime.utcnow() + timedelta(days=data.expires_in_days or 7)

    link = SharedContactLink(
        organization_id=org_id,
        contact_ids=[c.id for c in contacts],
        token=token,
        expires_at=expires_at,
        created_by_user_id=current_user.id,
    )
    db.add(link)
    db.commit()

    return {
        "success": True,
        "token": token,
        "expires_at": expires_at.isoformat(),
        "contact_count": len(contacts),
    }


@public_router.get(
    "/shared-contacts/{token}",
    summary="Public read-only view of contacts behind a share token",
    description=(
        "Public, unauthenticated counterpart to `/share-link`. Resolves a "
        "share token to the curated subset of CreativeContacts the org "
        "exposed and returns them in a read-only payload, or 404/410 if "
        "the token is invalid or expired.\n\n"
        "**Path parameter:** `token` — the opaque share token issued by "
        "`/org/{org_id}/share-link`.\n\n"
        "**Auth:** None — public endpoint.\n\n"
        "**Response:** `{ organization_name, expires_at, contacts: "
        "[{name, role, company, email, phone, photo_url, bio, "
        "socials, pro_society, ipi}] }`."
    ),
)
def get_shared_contacts(
    token: str,
    db: Session = Depends(get_db),
):
    link = db.query(SharedContactLink).filter(SharedContactLink.token == token).first()
    if not link:
        raise HTTPException(status_code=404, detail="Shared link not found")
    if link.expires_at < datetime.utcnow():
        raise HTTPException(status_code=410, detail="This shared link has expired")

    contacts = db.query(CreativeContact).filter(
        CreativeContact.id.in_(link.contact_ids),
    ).all()

    org = db.query(Organization).filter(Organization.id == link.organization_id).first()
    org_name = org.display_name or org.name if org else "Cadence"

    return {
        "organization_name": org_name,
        "contacts": [_contact_to_dict(c) for c in contacts],
        "expires_at": link.expires_at.isoformat(),
    }


class ShareToClientRequest(BaseModel):
    contact_ids: List[int]
    client_user_ids: List[int]


@router.post(
    "/org/{org_id}/share-to-client",
    summary="Share contacts with a single client (creator) account",
    description=(
        "Grants a creator user persistent in-app visibility into a set of "
        "the org's directory contacts — the contacts will appear in their "
        "creator portal under \"Shared with me.\" Idempotent per "
        "(creator, contact) pair.\n\n"
        "**Path parameter:** `org_id` — Organization ID.\n"
        "**Body:** `{ creator_id: int, contact_ids: int[] }`.\n\n"
        "**Auth:** Bearer JWT. Caller must be a member of the organization.\n\n"
        "**Response:** `{ success: true, message, created_count }`."
    ),
)
def share_contacts_to_client(
    org_id: int,
    data: ShareToClientRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    verify_org_access(current_user, org_id, db)

    contacts = db.query(CreativeContact).filter(
        CreativeContact.id.in_(data.contact_ids),
        CreativeContact.organization_id == org_id,
    ).all()
    if not contacts:
        raise HTTPException(status_code=404, detail="No contacts found")
    contacts = [c for c in contacts if not c.is_private or c.created_by_user_id == current_user.id]
    if not contacts:
        raise HTTPException(status_code=403, detail="No shareable contacts found")

    client_members = db.query(OrganizationMember).filter(
        OrganizationMember.organization_id == org_id,
        OrganizationMember.user_id.in_(data.client_user_ids),
        OrganizationMember.role == "CLIENT",
    ).all()
    if not client_members:
        raise HTTPException(status_code=404, detail="No valid client users found")

    valid_user_ids = {m.user_id for m in client_members}
    valid_contact_ids = {c.id for c in contacts}

    created_count = 0
    for user_id in valid_user_ids:
        for contact_id in valid_contact_ids:
            existing = db.query(ClientSharedContact).filter(
                ClientSharedContact.creative_contact_id == contact_id,
                ClientSharedContact.shared_with_user_id == user_id,
            ).first()
            if not existing:
                share = ClientSharedContact(
                    organization_id=org_id,
                    creative_contact_id=contact_id,
                    shared_with_user_id=user_id,
                    shared_by_user_id=current_user.id,
                )
                db.add(share)
                created_count += 1

    if created_count > 0:
        db.commit()

    return {
        "success": True,
        "message": f"Shared {len(valid_contact_ids)} contact(s) with {len(valid_user_ids)} client(s)",
        "created_count": created_count,
    }


class UnshareFromClientRequest(BaseModel):
    contact_ids: List[int]
    client_user_id: int


@router.delete(
    "/org/{org_id}/unshare-from-client",
    summary="Revoke client access to one or more shared contacts",
    description=(
        "Inverse of `/share-to-client`. Removes the share rows so the "
        "supplied creator no longer sees the listed contacts in their "
        "portal.\n\n"
        "**Path parameter:** `org_id` — Organization ID.\n"
        "**Body:** `{ creator_id: int, contact_ids: int[] }`.\n\n"
        "**Auth:** Bearer JWT. Caller must be a member of the organization.\n\n"
        "**Response:** `{ success: true, message, deleted_count }`."
    ),
)
def unshare_contacts_from_client(
    org_id: int,
    data: UnshareFromClientRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    verify_org_access(current_user, org_id, db)

    deleted = db.query(ClientSharedContact).filter(
        ClientSharedContact.organization_id == org_id,
        ClientSharedContact.creative_contact_id.in_(data.contact_ids),
        ClientSharedContact.shared_with_user_id == data.client_user_id,
    ).delete(synchronize_session=False)

    db.commit()

    return {
        "success": True,
        "message": f"Unshared {deleted} contact(s) from client",
        "deleted_count": deleted,
    }


@router.get(
    "/org/{org_id}/client-shares",
    summary="List which contacts are shared with which creators",
    description=(
        "Audit/lookup endpoint: returns every active "
        "(creator, contact) share pair in the org.\n\n"
        "**Path parameter:** `org_id` — Organization ID.\n"
        "**Optional query:** `creator_id` (filter to one creator), "
        "`contact_id` (filter to one contact).\n\n"
        "**Auth:** Bearer JWT. Caller must be a member of the organization.\n\n"
        "**Response:** `{ total, shares: [{creator_id, creator_name, "
        "contact_id, contact_name, shared_at}] }`."
    ),
)
def get_client_shares(
    org_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    verify_org_access(current_user, org_id, db)

    shares = db.query(ClientSharedContact).filter(
        ClientSharedContact.organization_id == org_id,
    ).all()

    result = []
    for share in shares:
        contact = db.query(CreativeContact).filter(CreativeContact.id == share.creative_contact_id).first()
        shared_with = db.query(User).filter(User.id == share.shared_with_user_id).first()
        shared_by = db.query(User).filter(User.id == share.shared_by_user_id).first()
        result.append({
            "id": share.id,
            "creative_contact_id": share.creative_contact_id,
            "contact_name": contact.display_name if contact else None,
            "shared_with_user_id": share.shared_with_user_id,
            "shared_with_username": shared_with.username if shared_with else None,
            "shared_by_user_id": share.shared_by_user_id,
            "shared_by_username": shared_by.username if shared_by else None,
            "created_at": share.created_at.isoformat() if share.created_at else None,
        })

    return {"shares": result, "total": len(result)}


class ShareToAccountsRequest(BaseModel):
    contact_ids: List[int]
    recipient_user_ids: Optional[List[int]] = []
    recipient_emails: Optional[List[str]] = []
    message: Optional[str] = ""


@router.post(
    "/org/{org_id}/share-to-accounts",
    summary="Share contacts with multiple client (creator) accounts at once",
    description=(
        "Bulk variant of `/share-to-client`: grants every supplied creator "
        "user persistent in-app visibility into every supplied contact. "
        "Idempotent per (creator, contact) pair.\n\n"
        "**Path parameter:** `org_id` — Organization ID.\n"
        "**Body:** `{ contact_ids: int[], client_user_ids: int[] }`.\n\n"
        "**Auth:** Bearer JWT. Caller must be a member of the organization.\n\n"
        "**Response:** `{ success: true, shared_count }`."
    ),
)
def share_contacts_to_accounts(
    org_id: int,
    data: ShareToAccountsRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    verify_org_access(current_user, org_id, db)

    contacts = db.query(CreativeContact).filter(
        CreativeContact.id.in_(data.contact_ids),
        CreativeContact.organization_id == org_id,
    ).all()
    if not contacts:
        raise HTTPException(status_code=404, detail="No contacts found")
    contacts = [c for c in contacts if not c.is_private or c.created_by_user_id == current_user.id]
    if not contacts:
        raise HTTPException(status_code=403, detail="No shareable contacts found")

    recipient_ids = list(data.recipient_user_ids or [])
    if data.recipient_emails:
        for email in data.recipient_emails:
            user = db.query(User).filter(User.email == email, User.is_active == True).first()
            if user and user.id not in recipient_ids and user.id != current_user.id:
                recipient_ids.append(user.id)

    if not recipient_ids:
        raise HTTPException(status_code=400, detail="No valid recipients found")

    shared_count = 0
    for contact in contacts:
        for uid in recipient_ids:
            if uid == current_user.id:
                continue
            recipient = db.query(User).filter(User.id == uid, User.is_active == True).first()
            if not recipient:
                continue

            existing = db.query(SharedItem).filter(
                SharedItem.item_type == "CONTACT_CARD",
                SharedItem.item_id == contact.id,
                SharedItem.shared_with_user_id == uid,
                SharedItem.status == "ACTIVE",
            ).first()
            if existing:
                continue

            recipient_membership = db.query(OrganizationMember).filter(
                OrganizationMember.user_id == uid
            ).first()

            shared_item = SharedItem(
                organization_id=org_id,
                item_type="CONTACT_CARD",
                item_id=contact.id,
                item_name=contact.display_name,
                shared_by_user_id=current_user.id,
                shared_with_user_id=uid,
                shared_with_org_id=recipient_membership.organization_id if recipient_membership else None,
                message=data.message,
                status="ACTIVE",
            )
            db.add(shared_item)
            shared_count += 1

    db.commit()
    return {"success": True, "shared_count": shared_count}
