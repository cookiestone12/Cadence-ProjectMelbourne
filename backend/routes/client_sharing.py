from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from ..models import get_db, User, Organization, OrganizationMember, Creator, ClientShare
from ..utils.auth import get_current_user

router = APIRouter(prefix="/api/client-sharing", tags=["client-sharing"])


def get_user_org(db: Session, user: User):
    membership = db.query(OrganizationMember).filter(
        OrganizationMember.user_id == user.id
    ).first()
    if not membership:
        raise HTTPException(status_code=404, detail="Not a member of any organization")
    return membership


class ShareRequest(BaseModel):
    creator_id: int
    recipient_email: str
    recipient_org_name: str
    role: str
    passcode: str


class AcceptRequest(BaseModel):
    passcode: str
    org_name: str


class RoleUpdateRequest(BaseModel):
    role: str


def share_to_dict(share, db):
    creator = db.query(Creator).filter(Creator.id == share.creator_id).first()
    primary_org = db.query(Organization).filter(Organization.id == share.primary_org_id).first()
    shared_by = db.query(User).filter(User.id == share.shared_by_user_id).first()
    recipient_org = None
    if share.recipient_org_id:
        recipient_org = db.query(Organization).filter(Organization.id == share.recipient_org_id).first()
    accepted_by = None
    if share.accepted_by_user_id:
        accepted_by = db.query(User).filter(User.id == share.accepted_by_user_id).first()

    return {
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
        "shared_by_user_id": share.shared_by_user_id,
        "shared_by_username": shared_by.username if shared_by else None,
        "accepted_by_user_id": share.accepted_by_user_id,
        "accepted_by_username": accepted_by.username if accepted_by else None,
        "created_at": share.created_at.isoformat() if share.created_at else None,
        "accepted_at": share.accepted_at.isoformat() if share.accepted_at else None,
        "revoked_at": share.revoked_at.isoformat() if share.revoked_at else None,
    }


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

    share = ClientShare(
        creator_id=req.creator_id,
        primary_org_id=membership.organization_id,
        recipient_user_email=req.recipient_email.lower(),
        recipient_org_name_verification=req.recipient_org_name,
        passcode=req.passcode,
        role=req.role.upper(),
        status="PENDING",
        shared_by_user_id=current_user.id,
    )
    db.add(share)
    db.commit()
    db.refresh(share)

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
    return [share_to_dict(s, db) for s in shares]


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
        ClientShare.status == "ACCEPTED"
    ).first()
    if not share:
        raise HTTPException(status_code=404, detail="Share not found or not authorized")

    share.status = "REVOKED"
    share.revoked_at = datetime.utcnow()
    db.commit()

    return {"message": "Share access revoked"}


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
                "accepted_at": share.accepted_at.isoformat() if share.accepted_at else None,
            })

    return results
