from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional
from ..models import (
    get_db, User, OrganizationMember, Organization,
    SharedItem, ContractDocument, AudioAsset, RoyaltyStatement,
    CreativeContact,
)
from ..utils.auth import get_current_user
import logging

logger = logging.getLogger("cadence")

router = APIRouter(prefix="/api/sharing", tags=["sharing"])


class ShareViaEmailRequest(BaseModel):
    item_type: str
    item_id: int
    item_name: Optional[str] = None
    recipient_emails: List[str]
    message: Optional[str] = ""

class ShareToAccountRequest(BaseModel):
    item_type: str
    item_id: int
    item_name: Optional[str] = None
    recipient_user_ids: Optional[List[int]] = []
    recipient_emails: Optional[List[str]] = []
    message: Optional[str] = ""

class UserSearchResult(BaseModel):
    id: int
    username: str
    email: Optional[str]
    organization_name: Optional[str]


def _get_user_org(db: Session, user: User):
    membership = db.query(OrganizationMember).filter(
        OrganizationMember.user_id == user.id
    ).first()
    if not membership:
        raise HTTPException(status_code=403, detail="No organization membership")
    return membership.organization_id


def _resolve_item_name(db: Session, item_type: str, item_id: int, fallback_name: str = None):
    if fallback_name:
        return fallback_name
    if item_type == "DOCUMENT":
        doc = db.query(ContractDocument).filter(ContractDocument.id == item_id).first()
        return doc.filename if doc else f"Document #{item_id}"
    elif item_type == "AUDIO":
        audio = db.query(AudioAsset).filter(AudioAsset.id == item_id).first()
        return audio.filename if audio else f"Audio #{item_id}"
    elif item_type == "STATEMENT":
        stmt = db.query(RoyaltyStatement).filter(RoyaltyStatement.id == item_id).first()
        return stmt.source_name if stmt else f"Statement #{item_id}"
    elif item_type == "CONTACT_CARD":
        contact = db.query(CreativeContact).filter(CreativeContact.id == item_id).first()
        return contact.display_name if contact else f"Contact #{item_id}"
    return f"Item #{item_id}"


@router.post("/email")
def share_via_email(
    request: ShareViaEmailRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    org_id = _get_user_org(db, current_user)
    item_name = _resolve_item_name(db, request.item_type, request.item_id, request.item_name)
    sender_name = getattr(current_user, 'full_name', None) or current_user.username

    from ..templates.email_templates import document_shared_email
    from ..services.email_provider import get_email_provider

    html_body = document_shared_email(
        sender_name=sender_name,
        item_name=item_name,
        item_type=request.item_type,
        message=request.message or "",
    )

    provider = get_email_provider()
    type_label = request.item_type.replace("_", " ").title()
    sent_count = 0

    for email in request.recipient_emails:
        success = provider.send_email(
            to=email,
            subject=f"{type_label} Shared: {item_name}",
            html_body=html_body,
        )
        if success:
            sent_count += 1
            shared_item = SharedItem(
                organization_id=org_id,
                item_type=request.item_type,
                item_id=request.item_id,
                item_name=item_name,
                shared_by_user_id=current_user.id,
                shared_with_email=email,
                message=request.message,
                status="ACTIVE",
            )
            db.add(shared_item)

    db.commit()
    return {"success": True, "sent_count": sent_count, "total": len(request.recipient_emails)}


@router.post("/account")
def share_to_account(
    request: ShareToAccountRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    org_id = _get_user_org(db, current_user)
    item_name = _resolve_item_name(db, request.item_type, request.item_id, request.item_name)

    recipient_ids = list(request.recipient_user_ids or [])

    if request.recipient_emails:
        for email in request.recipient_emails:
            user = db.query(User).filter(User.email == email, User.is_active == True).first()
            if user and user.id not in recipient_ids and user.id != current_user.id:
                recipient_ids.append(user.id)

    if not recipient_ids:
        raise HTTPException(status_code=400, detail="No valid recipients found")

    shared_count = 0
    for uid in recipient_ids:
        if uid == current_user.id:
            continue
        recipient = db.query(User).filter(User.id == uid).first()
        if not recipient:
            continue

        existing = db.query(SharedItem).filter(
            SharedItem.item_type == request.item_type,
            SharedItem.item_id == request.item_id,
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
            item_type=request.item_type,
            item_id=request.item_id,
            item_name=item_name,
            shared_by_user_id=current_user.id,
            shared_with_user_id=uid,
            shared_with_org_id=recipient_membership.organization_id if recipient_membership else None,
            message=request.message,
            status="ACTIVE",
        )
        db.add(shared_item)
        shared_count += 1

    db.commit()
    return {"success": True, "shared_count": shared_count}


@router.get("/shared-with-me")
def get_shared_with_me(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    items = db.query(SharedItem).filter(
        SharedItem.shared_with_user_id == current_user.id,
        SharedItem.status == "ACTIVE",
    ).order_by(SharedItem.created_at.desc()).all()

    results = []
    for item in items:
        sender = db.query(User).filter(User.id == item.shared_by_user_id).first()
        sender_org = None
        if sender:
            sender_membership = db.query(OrganizationMember).filter(
                OrganizationMember.user_id == sender.id
            ).first()
            if sender_membership:
                org = db.query(Organization).filter(Organization.id == sender_membership.organization_id).first()
                sender_org = org.display_name or org.name if org else None

        results.append({
            "id": item.id,
            "item_type": item.item_type,
            "item_id": item.item_id,
            "item_name": item.item_name,
            "message": item.message,
            "shared_by": {
                "id": sender.id if sender else None,
                "username": sender.username if sender else "Unknown",
                "email": sender.email if sender else None,
            },
            "shared_by_org": sender_org,
            "created_at": item.created_at.isoformat() if item.created_at else None,
        })

    return results


@router.get("/shared-by-me")
def get_shared_by_me(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    items = db.query(SharedItem).filter(
        SharedItem.shared_by_user_id == current_user.id,
    ).order_by(SharedItem.created_at.desc()).all()

    results = []
    for item in items:
        recipient_info = {}
        if item.shared_with_user_id:
            recipient = db.query(User).filter(User.id == item.shared_with_user_id).first()
            recipient_info = {
                "id": recipient.id if recipient else None,
                "username": recipient.username if recipient else "Unknown",
                "email": recipient.email if recipient else None,
            }
        elif item.shared_with_email:
            recipient_info = {"email": item.shared_with_email}

        results.append({
            "id": item.id,
            "item_type": item.item_type,
            "item_id": item.item_id,
            "item_name": item.item_name,
            "message": item.message,
            "shared_with": recipient_info,
            "status": item.status,
            "created_at": item.created_at.isoformat() if item.created_at else None,
        })

    return results


@router.post("/{share_id}/revoke")
def revoke_share(
    share_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    item = db.query(SharedItem).filter(SharedItem.id == share_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Shared item not found")
    if item.shared_by_user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Only the sender can revoke a share")

    item.status = "REVOKED"
    db.commit()
    return {"success": True, "message": "Share revoked"}


@router.get("/users/search")
def search_users(
    q: str = "",
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not q or len(q) < 2:
        return []

    from sqlalchemy import or_, func

    users = db.query(User).filter(
        User.is_active == True,
        User.id != current_user.id,
        or_(
            func.lower(User.username).contains(q.lower()),
            func.lower(User.email).contains(q.lower()),
        )
    ).limit(20).all()

    results = []
    for user in users:
        membership = db.query(OrganizationMember).filter(
            OrganizationMember.user_id == user.id
        ).first()
        org_name = None
        if membership:
            org = db.query(Organization).filter(Organization.id == membership.organization_id).first()
            org_name = org.display_name or org.name if org else None

        results.append({
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "organization_name": org_name,
        })

    return results
