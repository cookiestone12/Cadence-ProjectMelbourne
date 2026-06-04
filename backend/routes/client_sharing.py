from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
import logging
from ..models import get_db, User, Organization, OrganizationMember, Creator, ClientShare, Song, SongCredit
from ..utils.auth import get_current_user, resolve_active_org_id
from ..services.audit_service import log_action, make_diff
from ..services.plan_entitlements import (
    is_professional,
    is_enterprise,
    catalog_limit,
    count_catalogs,
)
from .notifications import create_notification


def _share_audit_label(share: 'ClientShare', creator_name: str = None) -> str:
    name = creator_name or f"Creator #{share.creator_id}"
    return f"{name} → {share.recipient_user_email or 'unknown'}"


def _share_snapshot(share: 'ClientShare') -> dict:
    return {
        "creator_id": share.creator_id,
        "primary_org_id": share.primary_org_id,
        "recipient_org_id": share.recipient_org_id,
        "recipient_user_email": share.recipient_user_email,
        "role": share.role,
        "status": share.status,
        "shared_modules": getattr(share, 'shared_modules', None),
    }


def _audit_share(
    db: Session,
    organization_id: int,
    user_id: int,
    action: str,
    share: 'ClientShare',
    creator_name: str = None,
    before: dict = None,
    after: dict = None,
    extra: dict = None,
):
    """Wrapper around log_action that pre-fills ClientShare audit fields.

    Normalizes every audit row to the shape ``{before, after, diff, ...context}``
    so downstream viewers / exports can render share history with one schema
    regardless of which lifecycle path produced the entry.
    """
    diff = make_diff(before or {}, after or {})
    details = {"before": before, "after": after, "diff": diff}
    if extra:
        details.update(extra)
    log_action(
        db,
        organization_id=organization_id,
        user_id=user_id,
        action=action,
        entity_type="ClientShare",
        entity_id=share.id,
        entity_name=_share_audit_label(share, creator_name),
        details=details,
    )

logger = logging.getLogger("cadence")

router = APIRouter(prefix="/api/client-sharing", tags=["Client Sharing"])


def has_shared_access(db: Session, user_id: int, creator_id: int, required_module: str = None):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return None
    # Task #216: resolve the org the user is *actively* in (honors the
    # active-org pointer), not an arbitrary `.first()` membership. For a
    # multi-org user this guarantees the shared-access check is evaluated
    # against the same org the rest of the request is scoped to.
    org_id = resolve_active_org_id(db, user)
    if org_id is None:
        return None
    share = db.query(ClientShare).filter(
        ClientShare.creator_id == creator_id,
        ClientShare.recipient_org_id == org_id,
        ClientShare.status == "ACCEPTED"
    ).first()
    if share and required_module:
        modules = getattr(share, 'shared_modules', None) or ALL_SHARE_MODULES
        if required_module not in modules:
            return None
    return share


def get_user_org(db: Session, user: User):
    # Task #216: resolve the user's *active* org (honors the active-org
    # pointer with self-heal) instead of an arbitrary `.first()` membership.
    # Sharing create/accept and all other flows that scope by this membership
    # are now deterministic for users who belong to multiple organizations.
    org_id = resolve_active_org_id(db, user)
    if org_id is None:
        raise HTTPException(status_code=404, detail="Not a member of any organization")
    membership = db.query(OrganizationMember).filter(
        OrganizationMember.user_id == user.id,
        OrganizationMember.organization_id == org_id,
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


@router.post(
    "/share",
    summary='Share an entity with another account',
    description='Creates a ClientShare row offering one of the org\'s entities (creator, contract, etc.) to a target account with a chosen role + module set. The target sees it under `/received` until they accept.\n\n**Body:** `{ entity_type: string, entity_id: int, target_user_id: int, role: "viewer"|"editor"|"manager", modules: string[] }`.\n**Auth:** Bearer JWT.\n**Response:** the created ClientShare object.',
)
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

    # Task #213 — directional sharing rule. A Professional org may only share
    # its catalog OUT to an Enterprise account, enforced at both share-creation
    # (here) and share-acceptance (a Professional org can never receive).
    sender_org = db.query(Organization).filter(
        Organization.id == membership.organization_id
    ).first()
    if sender_org and is_professional(sender_org):
        # A Professional sender may only target a recipient we can positively
        # verify is an Enterprise account; otherwise reject outright rather than
        # creating an invitation that can never be accepted.
        recipient_user = db.query(User).filter(
            User.email == req.recipient_email.lower()
        ).first()
        # Deterministic across multi-org recipients: the target is valid iff ANY
        # of the recipient user's org memberships is an Enterprise org. This
        # avoids row-order dependence from picking a single membership.
        recipient_is_enterprise = False
        if recipient_user:
            recipient_orgs = (
                db.query(Organization)
                .join(OrganizationMember, OrganizationMember.organization_id == Organization.id)
                .filter(OrganizationMember.user_id == recipient_user.id)
                .all()
            )
            recipient_is_enterprise = any(is_enterprise(o) for o in recipient_orgs)
        if not recipient_is_enterprise:
            raise HTTPException(
                status_code=403,
                detail="Professional accounts can only share their catalog with verified Enterprise accounts.",
            )

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
    db.flush()

    _audit_share(
        db,
        organization_id=membership.organization_id,
        user_id=current_user.id,
        action="CREATE",
        share=share,
        creator_name=creator.display_name,
        before=None,
        after=_share_snapshot(share),
        extra={
            "creator_id": share.creator_id,
            "recipient_email": share.recipient_user_email,
            "role": share.role,
            "shared_modules": modules,
        },
    )

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


@router.get(
    "/sent",
    summary='List shares the current user has sent out',
    description='Returns every ClientShare the calling user originated, with the current acceptance status.\n\n**Query:** `status` (`pending|accepted|rejected|revoked`), `entity_type`.\n**Auth:** Bearer JWT.\n**Response:** `{ shares: [{id, entity_type, entity_id, target_user_id, target_email, role, modules, status, created_at}] }`.',
)
def get_sent_shares(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    membership = get_user_org(db, current_user)
    shares = db.query(ClientShare).filter(
        ClientShare.primary_org_id == membership.organization_id
    ).order_by(ClientShare.created_at.desc()).all()
    return [share_to_dict(s, db, include_passcode=True) for s in shares]


@router.get(
    "/received",
    summary='List shares offered to the current user',
    description='Returns every ClientShare addressed to the calling user regardless of status (pending invites + already accepted/rejected).\n\n**Query:** `status`.\n**Auth:** Bearer JWT.\n**Response:** `{ shares: [{id, entity_type, entity_id, from_user_id, from_org_name, role, modules, status, created_at}] }`.',
)
def get_received_shares(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    shares = db.query(ClientShare).filter(
        ClientShare.recipient_user_email == current_user.email.lower(),
        ClientShare.status == "PENDING"
    ).order_by(ClientShare.created_at.desc()).all()
    return [share_to_dict(s, db) for s in shares]


@router.get(
    "/received-active",
    summary='List actively-accepted shares for the current user',
    description='Convenience filter on `/received` returning only `status = accepted` rows. This is what populates the user\'s "shared with me" workspace.\n\n**Auth:** Bearer JWT.\n**Response:** `{ shares: [...] }`.',
)
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


@router.post(
    "/accept/{share_id}",
    summary='Accept a pending share',
    description='Marks the share as `accepted` so the receiver can begin using the granted access.\n\n**Path parameter:** `share_id`.\n**Auth:** Bearer JWT — must be the receiver.\n**Response:** `{ success: true, share: {...} }`.',
)
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

    # Task #213 — recipient-side plan enforcement (the hard guarantee).
    recipient_org = db.query(Organization).filter(
        Organization.id == membership.organization_id
    ).first()
    if recipient_org and is_professional(recipient_org):
        raise HTTPException(
            status_code=403,
            detail="Your Professional plan can't receive shared catalogs. Upgrade to Enterprise to manage shared client catalogs.",
        )
    # An accepted share occupies a catalog slot in the recipient's roster, so
    # respect the recipient Enterprise org's remaining capacity.
    if recipient_org:
        limit = catalog_limit(recipient_org)
        current = count_catalogs(db, recipient_org.id)
        if current + 1 > limit:
            raise HTTPException(
                status_code=403,
                detail=f"Accepting this share would exceed your plan's limit of {limit} client catalogs.",
            )

    before = _share_snapshot(share)
    share.status = "ACCEPTED"
    share.recipient_org_id = membership.organization_id
    share.accepted_by_user_id = current_user.id
    share.accepted_at = datetime.utcnow()
    after = _share_snapshot(share)

    creator_for_audit = db.query(Creator).filter(Creator.id == share.creator_id).first()
    _audit_share(
        db,
        organization_id=share.primary_org_id,
        user_id=current_user.id,
        action="ACCEPT",
        share=share,
        creator_name=creator_for_audit.display_name if creator_for_audit else None,
        before=before,
        after=after,
        extra={"recipient_org_id": membership.organization_id},
    )

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


@router.post(
    "/reject/{share_id}",
    summary='Reject a pending share',
    description='Marks the share as `rejected`. Sender is notified.\n\n**Path parameter:** `share_id`.\n**Auth:** Bearer JWT — must be the receiver.\n**Response:** `{ success: true }`.',
)
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

    before = _share_snapshot(share)
    share.status = "REJECTED"
    after = _share_snapshot(share)

    creator_for_audit = db.query(Creator).filter(Creator.id == share.creator_id).first()
    _audit_share(
        db,
        organization_id=share.primary_org_id,
        user_id=current_user.id,
        action="REJECT",
        share=share,
        creator_name=creator_for_audit.display_name if creator_for_audit else None,
        before=before,
        after=after,
    )

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


@router.post(
    "/revoke/{share_id}",
    summary='Revoke a share you previously sent',
    description='Marks the share as `revoked` so the receiver loses access. Different from delete — keeps audit history.\n\n**Path parameter:** `share_id`.\n**Auth:** Bearer JWT — must be the sender.\n**Response:** `{ success: true }`.',
)
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
    before = _share_snapshot(share)
    share.status = "CANCELLED" if was_pending else "REVOKED"
    share.revoked_at = datetime.utcnow()
    after = _share_snapshot(share)

    creator_for_audit = db.query(Creator).filter(Creator.id == share.creator_id).first()
    _audit_share(
        db,
        organization_id=share.primary_org_id,
        user_id=current_user.id,
        action="CANCEL" if was_pending else "REVOKE",
        share=share,
        creator_name=creator_for_audit.display_name if creator_for_audit else None,
        before=before,
        after=after,
    )

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


@router.put(
    "/{share_id}/role",
    summary="Change a share's access role",
    description="Upgrades/downgrades the receiver's role between `viewer`, `editor`, and `manager`.\n\n**Path parameter:** `share_id`.\n**Body:** `{ role: string }`.\n**Auth:** Bearer JWT — must be the sender.\n**Response:** `{ share: {...} }`.",
)
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

    before = _share_snapshot(share)
    share.role = req.role.upper()
    after = _share_snapshot(share)
    diff = make_diff(before, after)

    if diff:
        creator_for_audit = db.query(Creator).filter(Creator.id == share.creator_id).first()
        _audit_share(
            db,
            organization_id=share.primary_org_id,
            user_id=current_user.id,
            action="UPDATE_ROLE",
            share=share,
            creator_name=creator_for_audit.display_name if creator_for_audit else None,
            before=before,
            after=after,
        )

    db.commit()

    return {"message": "Role updated successfully"}


@router.put(
    "/{share_id}/modules",
    summary='Update which modules a share grants access to',
    description="Replaces the share's module list (catalog, royalties, contracts, etc.). Only the listed modules are visible to the receiver.\n\n**Path parameter:** `share_id`.\n**Body:** `{ modules: string[] }`.\n**Auth:** Bearer JWT — must be the sender.\n**Response:** `{ share: {...} }`.",
)
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

    before = _share_snapshot(share)
    share.shared_modules = req.shared_modules
    after = _share_snapshot(share)
    diff = make_diff(before, after)

    if diff:
        creator_for_audit = db.query(Creator).filter(Creator.id == share.creator_id).first()
        _audit_share(
            db,
            organization_id=share.primary_org_id,
            user_id=current_user.id,
            action="UPDATE_MODULES",
            share=share,
            creator_name=creator_for_audit.display_name if creator_for_audit else None,
            before=before,
            after=after,
        )

    db.commit()

    return {"message": "Shared modules updated successfully", "shared_modules": req.shared_modules}


@router.get(
    "/shared-clients",
    summary='List clients (creators) the user has access to via shares',
    description="Aggregates over the user's accepted shares to return the distinct creator set they can see across all sharing orgs.\n\n**Auth:** Bearer JWT.\n**Response:** `{ creators: [{id, display_name, from_org_id, from_org_name, role, modules}] }`.",
)
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


@router.get(
    "/shared-songs",
    summary='List songs the user has access to via shares',
    description="Aggregates over the user's accepted shares to return the distinct song set they can see.\n\n**Query:** `creator_id` (filter to one shared creator), `q`.\n**Auth:** Bearer JWT.\n**Response:** `{ songs: [{id, title, artist, creator_id, from_org_id, role}] }`.",
)
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
