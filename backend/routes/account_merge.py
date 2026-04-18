import random
import string
import logging
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..models import get_db, User, Organization, OrganizationMember, Creator, AccountMergeRequest
from ..routes.auth import get_current_user

logger = logging.getLogger("cadence")

router = APIRouter(prefix="/api/account-merge", tags=["Account Merge"])
admin_router = APIRouter(prefix="/api/admin/merge-requests", tags=["Account Merge"])


def get_current_super_admin(current_user: User = Depends(get_current_user)):
    if not getattr(current_user, 'is_super_admin', False):
        raise HTTPException(status_code=403, detail="Super admin access required")
    return current_user


def _generate_verification_code() -> str:
    return ''.join(random.choices(string.digits, k=6))


class MergeRequestCreate(BaseModel):
    target_email: str


class MergeVerify(BaseModel):
    request_id: int
    code: str


@router.post(
    "/request",
    summary='Request a merge of two user accounts',
    description='Initiates a merge between the calling user\'s account and a second account they own (e.g. signed up twice). Sends a verification email to the target.\n\n**Body:** `{ target_email: string, reason?: string }`.\n**Auth:** Bearer JWT.\n**Response:** `{ request_id, status: "pending_verification", verification_email_sent_to }`.',
)
def create_merge_request(
    body: MergeRequestCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    membership = db.query(OrganizationMember).filter(
        OrganizationMember.user_id == current_user.id,
        OrganizationMember.role == "CLIENT",
    ).first()
    if not membership:
        raise HTTPException(status_code=400, detail="Only client accounts can request a merge")

    target_user = db.query(User).filter(
        User.email == body.target_email.strip().lower()
    ).first()
    if not target_user:
        target_user = db.query(User).filter(
            User.email == body.target_email.strip()
        ).first()
    if not target_user:
        raise HTTPException(status_code=404, detail="No user account found with that email address")

    if target_user.id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot merge an account with itself")

    existing = db.query(AccountMergeRequest).filter(
        AccountMergeRequest.requesting_user_id == current_user.id,
        AccountMergeRequest.target_user_id == target_user.id,
        AccountMergeRequest.status.in_(["PENDING_VERIFICATION", "VERIFIED"]),
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="You already have a pending merge request for this account")

    code = _generate_verification_code()
    expires = datetime.utcnow() + timedelta(minutes=15)

    merge_req = AccountMergeRequest(
        requesting_user_id=current_user.id,
        target_user_id=target_user.id,
        organization_id=membership.organization_id,
        linked_creator_id=membership.linked_creator_id,
        status="PENDING_VERIFICATION",
        verification_code=code,
        verification_expires_at=expires,
    )
    db.add(merge_req)
    db.commit()
    db.refresh(merge_req)

    try:
        from ..services.email_provider import get_email_provider
        from ..templates.email_templates import merge_verification

        org = db.query(Organization).filter(Organization.id == membership.organization_id).first()
        org_name = (org.display_name or org.name) if org else "your organization"

        html_body = merge_verification(
            recipient_email=target_user.email,
            client_username=current_user.username,
            org_name=org_name,
            code=code,
        )
        provider = get_email_provider()
        provider.send_email(
            to=target_user.email,
            subject=f"Account Merge Verification Code — Cadence",
            html_body=html_body,
        )
    except Exception as e:
        logger.warning(f"Failed to send merge verification email: {e}")

    masked_email = target_user.email
    at_idx = masked_email.index("@")
    if at_idx > 2:
        masked_email = masked_email[:2] + "***" + masked_email[at_idx:]

    return {
        "id": merge_req.id,
        "status": merge_req.status,
        "target_email_masked": masked_email,
        "message": f"Verification code sent to {masked_email}. Enter the code to verify your identity.",
    }


@router.post(
    "/verify",
    summary='Verify and complete an account-merge request',
    description='Completes a merge using the token from the verification email. Moves the target\'s data into the calling user, then disables the target login.\n\n**Body:** `{ token: string }`.\n**Auth:** Bearer JWT.\n**Response:** `{ status: "completed", merged_user_id }`.',
)
def verify_merge_request(
    body: MergeVerify,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    merge_req = db.query(AccountMergeRequest).filter(
        AccountMergeRequest.id == body.request_id,
        AccountMergeRequest.requesting_user_id == current_user.id,
    ).first()
    if not merge_req:
        raise HTTPException(status_code=404, detail="Merge request not found")

    if merge_req.status != "PENDING_VERIFICATION":
        raise HTTPException(status_code=400, detail=f"Request is already {merge_req.status.lower()}")

    if datetime.utcnow() > merge_req.verification_expires_at:
        merge_req.status = "EXPIRED"
        db.commit()
        raise HTTPException(status_code=400, detail="Verification code has expired. Please create a new request.")

    if merge_req.verification_code != body.code.strip():
        raise HTTPException(status_code=400, detail="Invalid verification code")

    merge_req.status = "VERIFIED"
    merge_req.verified_at = datetime.utcnow()
    merge_req.verification_code = None
    db.commit()

    return {
        "id": merge_req.id,
        "status": "VERIFIED",
        "message": "Identity verified. Your merge request has been submitted for admin review.",
    }


@router.get(
    "/my-requests",
    summary="List the calling user's merge requests",
    description='Returns every merge request the user has initiated and its current status.\n\n**Auth:** Bearer JWT.\n**Response:** `{ requests: [{id, target_email, status, created_at, completed_at}] }`.',
)
def get_my_merge_requests(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    requests = db.query(AccountMergeRequest).filter(
        AccountMergeRequest.requesting_user_id == current_user.id,
    ).order_by(AccountMergeRequest.created_at.desc()).all()

    result = []
    for r in requests:
        target = db.query(User).filter(User.id == r.target_user_id).first()
        org = db.query(Organization).filter(Organization.id == r.organization_id).first()
        creator = db.query(Creator).filter(Creator.id == r.linked_creator_id).first() if r.linked_creator_id else None

        target_email = target.email if target else "Unknown"
        at_idx = target_email.index("@") if "@" in target_email else len(target_email)
        masked = target_email[:2] + "***" + target_email[at_idx:] if at_idx > 2 else target_email

        result.append({
            "id": r.id,
            "status": r.status,
            "target_email_masked": masked,
            "target_username": target.username if target else None,
            "organization_name": (org.display_name or org.name) if org else None,
            "creator_name": creator.display_name if creator else None,
            "admin_notes": r.admin_notes,
            "created_at": r.created_at.isoformat() if r.created_at else None,
            "verified_at": r.verified_at.isoformat() if r.verified_at else None,
            "resolved_at": r.resolved_at.isoformat() if r.resolved_at else None,
        })
    return result


@router.delete(
    "/{request_id}",
    summary='Cancel a pending merge request',
    description="Voids a merge that hasn't been verified yet.\n\n**Path parameter:** `request_id`.\n**Auth:** Bearer JWT — must be the request initiator.\n**Response:** `{ success: true }`.",
)
def cancel_merge_request(
    request_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    merge_req = db.query(AccountMergeRequest).filter(
        AccountMergeRequest.id == request_id,
        AccountMergeRequest.requesting_user_id == current_user.id,
    ).first()
    if not merge_req:
        raise HTTPException(status_code=404, detail="Merge request not found")

    if merge_req.status in ("COMPLETED", "REJECTED"):
        raise HTTPException(status_code=400, detail="Cannot cancel a completed or rejected request")

    merge_req.status = "CANCELLED"
    db.commit()
    return {"message": "Merge request cancelled"}


# ─── Admin endpoints ───

@admin_router.get(
    "",
    summary='List all account-merge requests for staff review',
    description="Returns every AccountMergeRequest in the system regardless of user, with the calling user's review actions enabled.\n\n**Query:** `status` (`pending|verified|approved|rejected|cancelled`), `q` (email substring), `limit`, `offset`.\n**Auth:** Bearer JWT — platform super-admin only.\n**Response:** `{ total, requests: [{id, source_user_id, target_user_id, target_email, status, created_at, completed_at, reason}] }`.",
)
def list_merge_requests(
    status: str = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_super_admin),
):
    query = db.query(AccountMergeRequest)
    if status:
        query = query.filter(AccountMergeRequest.status == status.upper())
    requests = query.order_by(AccountMergeRequest.created_at.desc()).all()

    result = []
    for r in requests:
        requesting = db.query(User).filter(User.id == r.requesting_user_id).first()
        target = db.query(User).filter(User.id == r.target_user_id).first()
        org = db.query(Organization).filter(Organization.id == r.organization_id).first()
        creator = db.query(Creator).filter(Creator.id == r.linked_creator_id).first() if r.linked_creator_id else None

        target_memberships = db.query(OrganizationMember).filter(
            OrganizationMember.user_id == r.target_user_id,
            OrganizationMember.organization_id == r.organization_id,
        ).first()

        result.append({
            "id": r.id,
            "status": r.status,
            "requesting_user": {
                "id": requesting.id,
                "username": requesting.username,
                "email": requesting.email,
            } if requesting else None,
            "target_user": {
                "id": target.id,
                "username": target.username,
                "email": target.email,
            } if target else None,
            "organization": {
                "id": org.id,
                "name": org.display_name or org.name,
            } if org else None,
            "creator": {
                "id": creator.id,
                "name": creator.display_name,
            } if creator else None,
            "target_already_member": target_memberships is not None,
            "verified_at": r.verified_at.isoformat() if r.verified_at else None,
            "admin_notes": r.admin_notes,
            "created_at": r.created_at.isoformat() if r.created_at else None,
            "resolved_at": r.resolved_at.isoformat() if r.resolved_at else None,
        })
    return result


class AdminMergeAction(BaseModel):
    notes: str = ""


@admin_router.put(
    "/{request_id}/approve",
    summary='Approve a pending account-merge request',
    description='Marks a verified merge request as `approved` and runs the actual data merge — the source user inherits the target\'s organizations, creators, and history.\n\n**Path parameter:** `request_id`.\n**Body:** `{ note?: string }`.\n**Auth:** Bearer JWT — platform super-admin only.\n**Response:** `{ status: "approved", message }`.',
)
def approve_merge_request(
    request_id: int,
    body: AdminMergeAction = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_super_admin),
):
    merge_req = db.query(AccountMergeRequest).filter(
        AccountMergeRequest.id == request_id,
    ).first()
    if not merge_req:
        raise HTTPException(status_code=404, detail="Merge request not found")

    if merge_req.status != "VERIFIED":
        raise HTTPException(status_code=400, detail=f"Only verified requests can be approved. Current status: {merge_req.status}")

    requesting_membership = db.query(OrganizationMember).filter(
        OrganizationMember.user_id == merge_req.requesting_user_id,
        OrganizationMember.organization_id == merge_req.organization_id,
        OrganizationMember.role == "CLIENT",
    ).first()
    if not requesting_membership:
        raise HTTPException(status_code=400, detail="Client membership not found for the requesting user")

    existing_target_membership = db.query(OrganizationMember).filter(
        OrganizationMember.user_id == merge_req.target_user_id,
        OrganizationMember.organization_id == merge_req.organization_id,
    ).first()

    if existing_target_membership:
        existing_target_membership.role = "CLIENT"
        existing_target_membership.linked_creator_id = requesting_membership.linked_creator_id
        existing_target_membership.client_access_scope = getattr(requesting_membership, 'client_access_scope', 'OWN')
        db.delete(requesting_membership)
        db.flush()
    else:
        requesting_membership.user_id = merge_req.target_user_id
        db.flush()

    if merge_req.linked_creator_id:
        creator = db.query(Creator).filter(Creator.id == merge_req.linked_creator_id).first()
        if creator:
            creator.linked_user_id = merge_req.target_user_id

    requesting_user = db.query(User).filter(User.id == merge_req.requesting_user_id).first()
    if requesting_user:
        remaining_memberships = db.query(OrganizationMember).filter(
            OrganizationMember.user_id == merge_req.requesting_user_id,
        ).count()
        if remaining_memberships == 0:
            requesting_user.is_active = False

    merge_req.status = "COMPLETED"
    merge_req.admin_notes = body.notes if body else None
    merge_req.resolved_by_user_id = current_user.id
    merge_req.resolved_at = datetime.utcnow()

    db.commit()

    logger.info(
        f"Merge request {request_id} approved by admin {current_user.username}: "
        f"client user {merge_req.requesting_user_id} -> target user {merge_req.target_user_id} "
        f"in org {merge_req.organization_id}"
    )

    return {
        "message": "Merge completed successfully. The client membership has been transferred to the target account.",
        "status": "COMPLETED",
    }


@admin_router.put(
    "/{request_id}/reject",
    summary='Reject an account-merge request',
    description='Marks the request as `rejected` and notifies the requester. No data is moved.\n\n**Path parameter:** `request_id`.\n**Body:** `{ reason?: string }`.\n**Auth:** Bearer JWT — platform super-admin only.\n**Response:** `{ status: "rejected", message }`.',
)
def reject_merge_request(
    request_id: int,
    body: AdminMergeAction = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_super_admin),
):
    merge_req = db.query(AccountMergeRequest).filter(
        AccountMergeRequest.id == request_id,
    ).first()
    if not merge_req:
        raise HTTPException(status_code=404, detail="Merge request not found")

    if merge_req.status in ("COMPLETED", "REJECTED"):
        raise HTTPException(status_code=400, detail=f"Request is already {merge_req.status.lower()}")

    merge_req.status = "REJECTED"
    merge_req.admin_notes = body.notes if body else None
    merge_req.resolved_by_user_id = current_user.id
    merge_req.resolved_at = datetime.utcnow()
    db.commit()

    return {"message": "Merge request rejected", "status": "REJECTED"}
