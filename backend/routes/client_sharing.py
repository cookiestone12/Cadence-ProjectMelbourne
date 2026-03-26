from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
import logging
from ..models import get_db, User, Organization, OrganizationMember, Creator, ClientShare, Song, SongCredit
from ..utils.auth import get_current_user
from .notifications import create_notification

logger = logging.getLogger("cadence")

router = APIRouter(prefix="/api/client-sharing", tags=["client-sharing"])


def has_shared_access(db: Session, user_id: int, creator_id: int, required_module: str = None):
    membership = db.query(OrganizationMember).filter(
        OrganizationMember.user_id == user_id
    ).first()
    if not membership:
        return None
    share = db.query(ClientShare).filter(
        ClientShare.creator_id == creator_id,
        ClientShare.recipient_org_id == membership.organization_id,
        ClientShare.status == "ACCEPTED"
    ).first()
    if share and required_module:
        modules = getattr(share, 'shared_modules', None) or ALL_SHARE_MODULES
        if required_module not in modules:
            return None
    return share


def get_user_org(db: Session, user: User):
    membership = db.query(OrganizationMember).filter(
        OrganizationMember.user_id == user.id
    ).first()
    if not membership:
        raise HTTPException(status_code=404, detail="Not a member of any organization")
    return membership


ALL_SHARE_MODULES = ["catalog", "contracts", "placements", "royalties", "contacts"]

class ShareRequest(BaseModel):
    creator_id: int
    recipient_email: str
    recipient_org_name: str
    role: str
    passcode: str
    shared_modules: Optional[list] = None


class AcceptRequest(BaseModel):
    passcode: str
    org_name: str


class RoleUpdateRequest(BaseModel):
    role: str

class ModulesUpdateRequest(BaseModel):
    shared_modules: list


def share_to_dict(share, db, include_passcode=False):
    creator = db.query(Creator).filter(Creator.id == share.creator_id).first()
    primary_org = db.query(Organization).filter(Organization.id == share.primary_org_id).first()
    shared_by = db.query(User).filter(User.id == share.shared_by_user_id).first()
    recipient_org = None
    if share.recipient_org_id:
        recipient_org = db.query(Organization).filter(Organization.id == share.recipient_org_id).first()
    accepted_by = None
    if share.accepted_by_user_id:
        accepted_by = db.query(User).filter(User.id == share.accepted_by_user_id).first()

    modules = getattr(share, 'shared_modules', None) or ALL_SHARE_MODULES
    result = {
        "id": share.id,
        "creator_id": share.creator_id,
        "creator_name": creator.display_name if creator else None,
        "primary_org_id": share.primary_org_id,
        "primary_org_name": primary_org.name if primary_org else None,
        "recipient_org_id": share.recipient_org_id,
        "recipient_org_name": recipient_org.name if recipient_org else None,
        "recipient_user_email": share.recipient_user_email,
        "recipient_org_name_verification": share.recipient_org_name_verification,
        "role": share.role,
        "status": share.status,
        "shared_modules": modules,
        "shared_by_user_id": share.shared_by_user_id,
        "shared_by_username": shared_by.username if shared_by else None,
        "accepted_by_user_id": share.accepted_by_user_id,
        "accepted_by_username": accepted_by.username if accepted_by else None,
        "created_at": share.created_at.isoformat() if share.created_at else None,
        "accepted_at": share.accepted_at.isoformat() if share.accepted_at else None,
        "revoked_at": share.revoked_at.isoformat() if share.revoked_at else None,
    }
    if include_passcode:
        result["passcode"] = share.passcode
    return result


@router.post("/share")
def create_share(
    req: ShareRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    membership = get_user_org(db, current_user)

    creator = db.query(Creator).filter(
        Creator.id == req.creator_id,
        Creator.organization_id == membership.organization_id
    ).first()
    if not creator:
        raise HTTPException(status_code=404, detail="Creator not found in your organization")

    valid_roles = ["COPRIMARY", "SECONDARY", "READER"]
    if req.role.upper() not in valid_roles:
        raise HTTPException(status_code=400, detail=f"Invalid role. Must be one of: {', '.join(valid_roles)}")

    if not req.passcode or len(req.passcode) != 6 or not req.passcode.isdigit():
        raise HTTPException(status_code=400, detail="Passcode must be exactly 6 digits")

    existing = db.query(ClientShare).filter(
        ClientShare.creator_id == req.creator_id,
        ClientShare.recipient_user_email == req.recipient_email.lower(),
        ClientShare.status.in_(["PENDING", "ACCEPTED"])
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="An active share already exists for this creator and recipient")

    modules = req.shared_modules if req.shared_modules else ALL_SHARE_MODULES
    for m in modules:
        if m not in ALL_SHARE_MODULES:
            raise HTTPException(status_code=400, detail=f"Invalid module: {m}. Valid: {', '.join(ALL_SHARE_MODULES)}")

    share = ClientShare(
        creator_id=req.creator_id,
        primary_org_id=membership.organization_id,
        recipient_user_email=req.recipient_email.lower(),
        recipient_org_name_verification=req.recipient_org_name,
        passcode=req.passcode,
        role=req.role.upper(),
        status="PENDING",
        shared_by_user_id=current_user.id,
        shared_modules=modules,
    )
    db.add(share)
    db.commit()
    db.refresh(share)

    try:
        recipient_user = db.query(User).filter(
            User.email == req.recipient_email.lower()
        ).first()
        if recipient_user:
            creator_name = creator.display_name or f"Creator #{creator.id}"
            sender_org = db.query(Organization).filter(Organization.id == membership.organization_id).first()
            org_label = sender_org.name if sender_org else "an organization"
            create_notification(
                db=db,
                user_id=recipient_user.id,
                notification_type="CLIENT_SHARE",
                title="Catalog Share Invitation",
                message=f"{org_label} has shared {creator_name} with you. Check your pending invitations to accept.",
                link="/roster",
                organization_id=None,
            )
    except Exception as e:
        logger.warning(f"Failed to send share notification to recipient: {e}")

    return {"id": share.id, "passcode": share.passcode, "message": "Share invitation created successfully"}


@router.get("/sent")
def get_sent_shares(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    membership = get_user_org(db, current_user)
    shares = db.query(ClientShare).filter(
        ClientShare.primary_org_id == membership.organization_id
    ).order_by(ClientShare.created_at.desc()).all()
    return [share_to_dict(s, db, include_passcode=True) for s in shares]


@router.get("/received")
def get_received_shares(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    shares = db.query(ClientShare).filter(
        ClientShare.recipient_user_email == current_user.email.lower(),
        ClientShare.status == "PENDING"
    ).order_by(ClientShare.created_at.desc()).all()
    return [share_to_dict(s, db) for s in shares]


@router.get("/received-active")
def get_received_active_shares(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    membership = get_user_org(db, current_user)
    shares = db.query(ClientShare).filter(
        ClientShare.recipient_org_id == membership.organization_id,
        ClientShare.status == "ACCEPTED"
    ).order_by(ClientShare.created_at.desc()).all()
    return [share_to_dict(s, db) for s in shares]


@router.post("/accept/{share_id}")
def accept_share(
    share_id: int,
    req: AcceptRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    share = db.query(ClientShare).filter(
        ClientShare.id == share_id,
        ClientShare.recipient_user_email == current_user.email.lower(),
        ClientShare.status == "PENDING"
    ).first()
    if not share:
        raise HTTPException(status_code=404, detail="Share invitation not found")

    if share.passcode != req.passcode:
        raise HTTPException(status_code=400, detail="Invalid passcode")

    if share.recipient_org_name_verification:
        if req.org_name.strip().lower() != share.recipient_org_name_verification.strip().lower():
            raise HTTPException(status_code=400, detail="Organization name does not match")

    membership = get_user_org(db, current_user)

    share.status = "ACCEPTED"
    share.recipient_org_id = membership.organization_id
    share.accepted_by_user_id = current_user.id
    share.accepted_at = datetime.utcnow()
    db.commit()

    try:
        creator = db.query(Creator).filter(Creator.id == share.creator_id).first()
        creator_name = creator.display_name if creator else f"Creator #{share.creator_id}"
        recipient_org = db.query(Organization).filter(Organization.id == membership.organization_id).first()
        org_label = recipient_org.name if recipient_org else "the recipient"
        create_notification(
            db=db,
            user_id=share.shared_by_user_id,
            notification_type="CLIENT_SHARE",
            title="Share Accepted",
            message=f"{org_label} has accepted your share of {creator_name}.",
            link="/roster",
            organization_id=share.primary_org_id,
        )
    except Exception as e:
        logger.warning(f"Failed to send share accepted notification: {e}")

    return {"message": "Share accepted successfully"}


@router.post("/reject/{share_id}")
def reject_share(
    share_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    share = db.query(ClientShare).filter(
        ClientShare.id == share_id,
        ClientShare.recipient_user_email == current_user.email.lower(),
        ClientShare.status == "PENDING"
    ).first()
    if not share:
        raise HTTPException(status_code=404, detail="Share invitation not found")

    share.status = "REJECTED"
    db.commit()

    try:
        creator = db.query(Creator).filter(Creator.id == share.creator_id).first()
        creator_name = creator.display_name if creator else f"Creator #{share.creator_id}"
        create_notification(
            db=db,
            user_id=share.shared_by_user_id,
            notification_type="CLIENT_SHARE",
            title="Share Rejected",
            message=f"Your share invitation for {creator_name} was declined.",
            link="/roster",
            organization_id=share.primary_org_id,
        )
    except Exception as e:
        logger.warning(f"Failed to send share rejected notification: {e}")

    return {"message": "Share rejected"}


@router.post("/revoke/{share_id}")
def revoke_share(
    share_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    membership = get_user_org(db, current_user)

    share = db.query(ClientShare).filter(
        ClientShare.id == share_id,
        ClientShare.primary_org_id == membership.organization_id,
        ClientShare.status.in_(["ACCEPTED", "PENDING"])
    ).first()
    if not share:
        raise HTTPException(status_code=404, detail="Share not found or not authorized")

    was_pending = share.status == "PENDING"
    share.status = "CANCELLED" if was_pending else "REVOKED"
    share.revoked_at = datetime.utcnow()
    db.commit()

    try:
        creator = db.query(Creator).filter(Creator.id == share.creator_id).first()
        creator_name = creator.display_name if creator else f"Creator #{share.creator_id}"
        if not was_pending and share.recipient_org_id:
            recipient_members = db.query(OrganizationMember).filter(
                OrganizationMember.organization_id == share.recipient_org_id
            ).all()
            sender_org = db.query(Organization).filter(Organization.id == share.primary_org_id).first()
            org_label = sender_org.name if sender_org else "The sharing organization"
            for member in recipient_members:
                create_notification(
                    db=db,
                    user_id=member.user_id,
                    notification_type="CLIENT_SHARE",
                    title="Share Access Revoked",
                    message=f"{org_label} has revoked your access to {creator_name}.",
                    link="/roster",
                    organization_id=member.organization_id,
                )
        elif was_pending:
            recipient_user = db.query(User).filter(
                User.email == share.recipient_user_email
            ).first()
            if recipient_user:
                create_notification(
                    db=db,
                    user_id=recipient_user.id,
                    notification_type="CLIENT_SHARE",
                    title="Share Invitation Cancelled",
                    message=f"A share invitation for {creator_name} has been cancelled.",
                    link="/roster",
                    organization_id=None,
                )
    except Exception as e:
        logger.warning(f"Failed to send revoke/cancel notification: {e}")

    return {"message": "Share invitation cancelled" if was_pending else "Share access revoked"}


@router.put("/{share_id}/role")
def update_share_role(
    share_id: int,
    req: RoleUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    membership = get_user_org(db, current_user)

    valid_roles = ["COPRIMARY", "SECONDARY", "READER"]
    if req.role.upper() not in valid_roles:
        raise HTTPException(status_code=400, detail=f"Invalid role. Must be one of: {', '.join(valid_roles)}")

    share = db.query(ClientShare).filter(
        ClientShare.id == share_id,
        ClientShare.status == "ACCEPTED"
    ).first()
    if not share:
        raise HTTPException(status_code=404, detail="Share not found")

    if share.primary_org_id != membership.organization_id:
        coprimary_check = db.query(ClientShare).filter(
            ClientShare.creator_id == share.creator_id,
            ClientShare.recipient_org_id == membership.organization_id,
            ClientShare.status == "ACCEPTED",
            ClientShare.role == "COPRIMARY"
        ).first()
        if not coprimary_check:
            raise HTTPException(status_code=403, detail="Only primary or co-primary users can update roles")

    share.role = req.role.upper()
    db.commit()

    return {"message": "Role updated successfully"}


@router.put("/{share_id}/modules")
def update_share_modules(
    share_id: int,
    req: ModulesUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    membership = get_user_org(db, current_user)

    for m in req.shared_modules:
        if m not in ALL_SHARE_MODULES:
            raise HTTPException(status_code=400, detail=f"Invalid module: {m}. Valid: {', '.join(ALL_SHARE_MODULES)}")

    if not req.shared_modules:
        raise HTTPException(status_code=400, detail="At least one module must be selected")

    share = db.query(ClientShare).filter(
        ClientShare.id == share_id,
        ClientShare.status.in_(["PENDING", "ACCEPTED"])
    ).first()
    if not share:
        raise HTTPException(status_code=404, detail="Share not found")

    if share.primary_org_id != membership.organization_id:
        coprimary_check = db.query(ClientShare).filter(
            ClientShare.creator_id == share.creator_id,
            ClientShare.recipient_org_id == membership.organization_id,
            ClientShare.status == "ACCEPTED",
            ClientShare.role == "COPRIMARY"
        ).first()
        if not coprimary_check:
            raise HTTPException(status_code=403, detail="Only primary or co-primary users can update shared modules")

    share.shared_modules = req.shared_modules
    db.commit()

    return {"message": "Shared modules updated successfully", "shared_modules": req.shared_modules}


@router.get("/shared-clients")
def get_shared_clients(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    membership = get_user_org(db, current_user)

    shares = db.query(ClientShare).filter(
        ClientShare.recipient_org_id == membership.organization_id,
        ClientShare.status == "ACCEPTED"
    ).all()

    results = []
    for share in shares:
        creator = db.query(Creator).filter(Creator.id == share.creator_id).first()
        primary_org = db.query(Organization).filter(Organization.id == share.primary_org_id).first()
        if creator:
            results.append({
                "share_id": share.id,
                "creator_id": creator.id,
                "creator_name": creator.display_name,
                "creator_email": creator.email,
                "primary_org_name": primary_org.name if primary_org else None,
                "role": share.role,
                "shared_modules": getattr(share, 'shared_modules', None) or ALL_SHARE_MODULES,
                "accepted_at": share.accepted_at.isoformat() if share.accepted_at else None,
            })

    return results


@router.get("/shared-songs")
def get_shared_songs(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    membership = get_user_org(db, current_user)

    shares = db.query(ClientShare).filter(
        ClientShare.recipient_org_id == membership.organization_id,
        ClientShare.status == "ACCEPTED"
    ).all()

    catalog_shares = [s for s in shares if "catalog" in (getattr(s, 'shared_modules', None) or ALL_SHARE_MODULES)]
    creator_ids = [s.creator_id for s in catalog_shares]
    if not creator_ids:
        return []

    songs = db.query(Song).join(SongCredit).filter(
        SongCredit.creator_id.in_(creator_ids)
    ).distinct().all()

    creator_map = {}
    for s in shares:
        creator = db.query(Creator).filter(Creator.id == s.creator_id).first()
        if creator:
            creator_map[s.creator_id] = creator.display_name

    results = []
    for song in songs:
        credits = db.query(SongCredit).filter(SongCredit.song_id == song.id).all()
        credit_creator_ids = [c.creator_id for c in credits]
        shared_creator_names = [creator_map[cid] for cid in credit_creator_ids if cid in creator_map]

        shared_credit_creator_ids = [cid for cid in credit_creator_ids if cid in creator_map]
        results.append({
            "id": song.id,
            "title": song.title,
            "primary_artist": song.primary_artist,
            "isrc": song.isrc,
            "iswc": song.iswc,
            "status_health_score": song.status_health_score,
            "is_released": song.is_released,
            "shared_from_creators": shared_creator_names,
            "shared_creator_ids": shared_credit_creator_ids,
            "organization_id": song.organization_id,
            "shared": True,
        })

    return results
