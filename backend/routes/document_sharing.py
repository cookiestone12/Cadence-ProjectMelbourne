from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse, Response
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional
from pathlib import Path
from ..models import (
    get_db, User, OrganizationMember, Organization,
    SharedItem, ContractDocument, AudioAsset, RoyaltyStatement,
    CreativeContact, Song, Contract, ContractParty, ContractAsset,
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


def _verify_item_ownership(db: Session, item_type: str, item_id: int, org_id: int):
    if item_type == "DOCUMENT":
        item = db.query(ContractDocument).filter(ContractDocument.id == item_id, ContractDocument.organization_id == org_id).first()
    elif item_type == "AUDIO":
        item = db.query(AudioAsset).filter(AudioAsset.id == item_id, AudioAsset.org_id == org_id).first()
    elif item_type == "STATEMENT":
        item = db.query(RoyaltyStatement).filter(RoyaltyStatement.id == item_id, RoyaltyStatement.organization_id == org_id).first()
    elif item_type == "CONTACT_CARD":
        item = db.query(CreativeContact).filter(CreativeContact.id == item_id, CreativeContact.organization_id == org_id).first()
    elif item_type == "SONG":
        item = db.query(Song).filter(Song.id == item_id, Song.organization_id == org_id).first()
    elif item_type == "CONTRACT":
        item = db.query(Contract).filter(Contract.id == item_id, Contract.organization_id == org_id).first()
    else:
        item = None
    if not item:
        raise HTTPException(status_code=404, detail=f"Item not found in your organization")
    return item


def _resolve_item_name(db: Session, item_type: str, item_id: int, fallback_name: str = None):
    if fallback_name:
        return fallback_name
    if item_type == "DOCUMENT":
        doc = db.query(ContractDocument).filter(ContractDocument.id == item_id).first()
        return doc.file_name if doc else f"Document #{item_id}"
    elif item_type == "AUDIO":
        audio = db.query(AudioAsset).filter(AudioAsset.id == item_id).first()
        return audio.name if audio else f"Audio #{item_id}"
    elif item_type == "STATEMENT":
        stmt = db.query(RoyaltyStatement).filter(RoyaltyStatement.id == item_id).first()
        return stmt.source_name if stmt else f"Statement #{item_id}"
    elif item_type == "CONTACT_CARD":
        contact = db.query(CreativeContact).filter(CreativeContact.id == item_id).first()
        return contact.display_name if contact else f"Contact #{item_id}"
    elif item_type == "SONG":
        song = db.query(Song).filter(Song.id == item_id).first()
        return f"{song.title} - {song.primary_artist}" if song else f"Song #{item_id}"
    elif item_type == "CONTRACT":
        contract = db.query(Contract).filter(Contract.id == item_id).first()
        return contract.title if contract else f"Contract #{item_id}"
    return f"Item #{item_id}"


def _build_attachment(db: Session, item_type: str, item_id: int, org_id: int):
    import base64
    if item_type == "DOCUMENT":
        doc = db.query(ContractDocument).filter(ContractDocument.id == item_id, ContractDocument.organization_id == org_id).first()
        if doc and doc.file_path and Path(doc.file_path).exists():
            with open(doc.file_path, "rb") as f:
                content = base64.b64encode(f.read()).decode("utf-8")
            return [{"filename": doc.file_name, "content": content, "type": doc.mime_type or "application/octet-stream"}]
    elif item_type == "AUDIO":
        pass
    elif item_type == "STATEMENT":
        stmt = db.query(RoyaltyStatement).filter(RoyaltyStatement.id == item_id, RoyaltyStatement.organization_id == org_id).first()
        if stmt and stmt.file_path and Path(stmt.file_path).exists():
            with open(stmt.file_path, "rb") as f:
                content = base64.b64encode(f.read()).decode("utf-8")
            return [{"filename": stmt.file_name or "statement", "content": content, "type": "application/octet-stream"}]
    return None


@router.post("/email")
def share_via_email(
    request: ShareViaEmailRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    org_id = _get_user_org(db, current_user)
    _verify_item_ownership(db, request.item_type, request.item_id, org_id)
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

    attachments = _build_attachment(db, request.item_type, request.item_id, org_id)

    provider = get_email_provider()
    type_label = request.item_type.replace("_", " ").title()
    sent_count = 0

    for email in request.recipient_emails:
        success = provider.send_email(
            to=email,
            subject=f"{type_label} Shared: {item_name}",
            html_body=html_body,
            attachments=attachments,
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
    _verify_item_ownership(db, request.item_type, request.item_id, org_id)
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
        recipient = db.query(User).filter(User.id == uid, User.is_active == True).first()
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


@router.post("/{share_id}/dismiss")
def dismiss_share(
    share_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    item = db.query(SharedItem).filter(SharedItem.id == share_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Shared item not found")
    if item.shared_with_user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Only the recipient can dismiss a share")

    item.status = "DISMISSED"
    db.commit()
    return {"success": True, "message": "Share dismissed"}


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


def _verify_share_recipient(share: SharedItem, current_user: User):
    if share.shared_with_user_id != current_user.id:
        raise HTTPException(status_code=403, detail="You do not have access to this shared item")
    if share.status != "ACTIVE":
        raise HTTPException(status_code=410, detail="This share has been revoked")


def _song_to_detail(song: Song):
    return {
        "title": song.title,
        "primary_artist": song.primary_artist,
        "isrc": song.isrc,
        "iswc": song.iswc,
        "project_title": song.project_title,
        "release_date": song.release_date.isoformat() if song.release_date else None,
        "label": song.label,
        "publishing_percentage": song.publishing_percentage,
        "master_percentage": song.master_percentage,
        "advance_amount": song.advance_amount,
        "recording_code": song.recording_code,
        "notes": song.notes,
        "asset_type": song.asset_type,
        "lyrics": song.lyrics,
        "spotify_link": song.spotify_link,
        "media_url": song.media_url,
    }


def _contact_to_detail(contact: CreativeContact):
    return {
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
        "photo_url": f"/api/creative-directory/{contact.id}/image" if contact.photo_data else None,
    }


@router.get("/{share_id}/details")
def get_shared_item_details(
    share_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    share = db.query(SharedItem).filter(SharedItem.id == share_id).first()
    if not share:
        raise HTTPException(status_code=404, detail="Shared item not found")
    _verify_share_recipient(share, current_user)

    detail = {"item_type": share.item_type, "item_name": share.item_name}

    source_org_id = share.organization_id

    if share.item_type == "SONG":
        song = db.query(Song).filter(Song.id == share.item_id, Song.organization_id == source_org_id).first()
        if song:
            detail["data"] = _song_to_detail(song)
        else:
            detail["data"] = None
            detail["error"] = "Original song no longer exists"
    elif share.item_type == "CONTACT_CARD":
        contact = db.query(CreativeContact).filter(CreativeContact.id == share.item_id, CreativeContact.organization_id == source_org_id).first()
        if contact:
            detail["data"] = _contact_to_detail(contact)
        else:
            detail["data"] = None
            detail["error"] = "Original contact no longer exists"
    elif share.item_type == "DOCUMENT":
        doc = db.query(ContractDocument).filter(ContractDocument.id == share.item_id, ContractDocument.organization_id == source_org_id).first()
        if doc:
            detail["data"] = {
                "file_name": doc.file_name,
                "file_size_bytes": doc.file_size_bytes,
                "mime_type": doc.mime_type,
                "description": doc.description,
                "has_file": bool(doc.file_path and Path(doc.file_path).exists()),
            }
        else:
            detail["data"] = None
            detail["error"] = "Original document no longer exists"
    elif share.item_type == "AUDIO":
        audio = db.query(AudioAsset).filter(AudioAsset.id == share.item_id, AudioAsset.org_id == source_org_id).first()
        if audio:
            detail["data"] = {
                "name": audio.name,
                "provider": audio.provider,
                "size_bytes": audio.size_bytes,
                "mime_type": audio.mime_type,
                "duration_seconds": audio.duration_seconds,
            }
        else:
            detail["data"] = None
            detail["error"] = "Original audio file no longer exists"
    elif share.item_type == "STATEMENT":
        stmt = db.query(RoyaltyStatement).filter(RoyaltyStatement.id == share.item_id, RoyaltyStatement.organization_id == source_org_id).first()
        if stmt:
            detail["data"] = {
                "source_name": stmt.source_name,
                "source_type": stmt.source_type,
                "period_start": stmt.period_start.isoformat() if stmt.period_start else None,
                "period_end": stmt.period_end.isoformat() if stmt.period_end else None,
                "file_name": stmt.file_name,
                "has_file": bool(stmt.file_path and Path(stmt.file_path).exists()),
            }
        else:
            detail["data"] = None
            detail["error"] = "Original statement no longer exists"
    elif share.item_type == "CONTRACT":
        contract = db.query(Contract).filter(Contract.id == share.item_id, Contract.organization_id == source_org_id).first()
        if contract:
            parties = db.query(ContractParty).filter(ContractParty.contract_id == contract.id).all()
            assets = db.query(ContractAsset).filter(ContractAsset.contract_id == contract.id).all()
            docs = db.query(ContractDocument).filter(ContractDocument.contract_id == contract.id).all()

            asset_names = []
            for a in assets:
                if a.asset_type == "SONG":
                    song = db.query(Song).filter(Song.id == a.asset_id).first()
                    asset_names.append({"type": a.asset_type, "name": song.title if song else f"Song #{a.asset_id}"})
                else:
                    asset_names.append({"type": a.asset_type, "name": f"{a.asset_type} #{a.asset_id}"})

            detail["data"] = {
                "title": contract.title,
                "contract_type": contract.contract_type,
                "status": contract.status,
                "payment_direction": contract.payment_direction,
                "reference_number": contract.reference_number,
                "start_date": contract.start_date.isoformat() if contract.start_date else None,
                "end_date": contract.end_date.isoformat() if contract.end_date else None,
                "territory": contract.territory or [],
                "advance_amount": contract.advance_amount,
                "advance_currency": contract.advance_currency,
                "advance_recouped": contract.advance_recouped,
                "notes": contract.notes,
                "terms_summary": contract.terms_summary,
                "parties": [
                    {"party_name": p.party_name, "party_role": p.party_role, "contact_email": p.contact_email}
                    for p in parties
                ],
                "assets": asset_names,
                "documents": [
                    {
                        "file_name": d.file_name,
                        "description": d.description,
                        "has_file": bool(d.file_path and Path(d.file_path).exists()),
                        "document_id": d.id,
                    }
                    for d in docs
                ],
            }
        else:
            detail["data"] = None
            detail["error"] = "Original contract no longer exists"

    return detail


@router.get("/{share_id}/download")
def download_shared_item(
    share_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    share = db.query(SharedItem).filter(SharedItem.id == share_id).first()
    if not share:
        raise HTTPException(status_code=404, detail="Shared item not found")
    _verify_share_recipient(share, current_user)

    source_org_id = share.organization_id

    if share.item_type == "DOCUMENT":
        doc = db.query(ContractDocument).filter(ContractDocument.id == share.item_id, ContractDocument.organization_id == source_org_id).first()
        if not doc:
            raise HTTPException(status_code=404, detail="Document no longer exists")
        file_path = Path(doc.file_path) if doc.file_path else None
        if not file_path or not file_path.exists():
            raise HTTPException(status_code=404, detail="Document file not found on disk")
        return FileResponse(
            path=str(file_path),
            filename=doc.file_name,
            media_type=doc.mime_type or "application/octet-stream",
        )
    elif share.item_type == "STATEMENT":
        stmt = db.query(RoyaltyStatement).filter(RoyaltyStatement.id == share.item_id, RoyaltyStatement.organization_id == source_org_id).first()
        if not stmt:
            raise HTTPException(status_code=404, detail="Statement no longer exists")
        file_path = Path(stmt.file_path) if stmt.file_path else None
        if not file_path or not file_path.exists():
            raise HTTPException(status_code=404, detail="Statement file not found on disk")
        return FileResponse(
            path=str(file_path),
            filename=stmt.file_name or "statement",
            media_type="application/octet-stream",
        )
    else:
        raise HTTPException(status_code=400, detail=f"Download not supported for {share.item_type} items")


@router.post("/{share_id}/import")
def import_shared_item(
    share_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    share = db.query(SharedItem).filter(SharedItem.id == share_id).first()
    if not share:
        raise HTTPException(status_code=404, detail="Shared item not found")
    _verify_share_recipient(share, current_user)

    recipient_org_id = _get_user_org(db, current_user)
    source_org_id = share.organization_id

    if share.item_type == "SONG":
        source_song = db.query(Song).filter(Song.id == share.item_id, Song.organization_id == source_org_id).first()
        if not source_song:
            raise HTTPException(status_code=404, detail="Original song no longer exists")

        new_song = Song(
            organization_id=recipient_org_id,
            asset_type=source_song.asset_type or "TRACK",
            title=source_song.title,
            primary_artist=source_song.primary_artist,
            isrc=source_song.isrc,
            iswc=source_song.iswc,
            project_title=source_song.project_title,
            release_date=source_song.release_date,
            label=source_song.label,
            publishing_percentage=source_song.publishing_percentage,
            master_percentage=source_song.master_percentage,
            advance_amount=source_song.advance_amount,
            recording_code=source_song.recording_code,
            notes=f"Imported from shared item. Original notes: {source_song.notes or ''}".strip(),
            media_url=source_song.media_url,
            lyrics=source_song.lyrics,
            spotify_link=source_song.spotify_link,
        )
        db.add(new_song)
        db.flush()

        from ..services.audit_service import log_action
        log_action(
            db, recipient_org_id, current_user.id,
            "IMPORT_SHARED_SONG", "SONG", new_song.id,
            new_song.title,
            {"source_share_id": share.id, "source_song_id": source_song.id, "source_org_id": share.organization_id}
        )

        db.commit()
        logger.info(f"User {current_user.id} imported shared song {source_song.id} as new song {new_song.id} in org {recipient_org_id}")
        return {
            "success": True,
            "message": f"'{source_song.title}' has been added to your catalog",
            "new_item_id": new_song.id,
            "item_type": "SONG",
        }

    elif share.item_type == "CONTACT_CARD":
        source_contact = db.query(CreativeContact).filter(CreativeContact.id == share.item_id, CreativeContact.organization_id == source_org_id).first()
        if not source_contact:
            raise HTTPException(status_code=404, detail="Original contact no longer exists")

        new_contact = CreativeContact(
            organization_id=recipient_org_id,
            display_name=source_contact.display_name,
            legal_name=source_contact.legal_name,
            email=source_contact.email,
            phone=source_contact.phone,
            pro=source_contact.pro,
            ipi=source_contact.ipi,
            isni=source_contact.isni,
            publisher_name=source_contact.publisher_name,
            publisher_ipi=source_contact.publisher_ipi,
            publisher_pro=source_contact.publisher_pro,
            roles=source_contact.roles,
            representation_name=source_contact.representation_name,
            representation_email=source_contact.representation_email,
            representation_phone=source_contact.representation_phone,
            territory=source_contact.territory,
            notes=f"Imported from shared contact. Original notes: {source_contact.notes or ''}".strip(),
            photo_data=source_contact.photo_data,
            photo_mime=source_contact.photo_mime,
        )
        if new_contact.photo_data:
            db.add(new_contact)
            db.flush()
            new_contact.photo_url = f"/api/creative-directory/{new_contact.id}/image"
        else:
            db.add(new_contact)
            db.flush()

        from ..services.audit_service import log_action
        log_action(
            db, recipient_org_id, current_user.id,
            "IMPORT_SHARED_CONTACT", "CONTACT", new_contact.id,
            new_contact.display_name,
            {"source_share_id": share.id, "source_contact_id": source_contact.id, "source_org_id": share.organization_id}
        )

        db.commit()
        logger.info(f"User {current_user.id} imported shared contact {source_contact.id} as new contact {new_contact.id} in org {recipient_org_id}")
        return {
            "success": True,
            "message": f"'{source_contact.display_name}' has been added to your directory",
            "new_item_id": new_contact.id,
            "item_type": "CONTACT_CARD",
        }

    else:
        raise HTTPException(status_code=400, detail=f"Import not supported for {share.item_type} items. Use the download option instead.")
