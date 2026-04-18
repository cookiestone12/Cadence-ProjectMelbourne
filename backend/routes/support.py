from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import Optional, List
from datetime import datetime
import uuid
import os
import logging
from pathlib import Path

from ..models import (
    get_db, User, OrganizationMember, Organization,
    SupportTicket, SupportTicketAttachment,
)
from ..utils.auth import get_current_user

logger = logging.getLogger("cadence")
router = APIRouter(prefix="/api/support", tags=["Support"])

UPLOAD_DIR = Path("uploads/support")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
MAX_FILE_SIZE = 5 * 1024 * 1024
ALLOWED_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}
MAX_ATTACHMENTS = 2


def _ticket_to_dict(ticket: SupportTicket, include_admin_notes: bool = False):
    result = {
        "id": ticket.id,
        "user_id": ticket.user_id,
        "organization_id": ticket.organization_id,
        "category": ticket.category,
        "subject": ticket.subject,
        "description": ticket.description,
        "status": ticket.status,
        "created_at": ticket.created_at.isoformat() if ticket.created_at else None,
        "updated_at": ticket.updated_at.isoformat() if ticket.updated_at else None,
        "resolved_at": ticket.resolved_at.isoformat() if ticket.resolved_at else None,
        "closed_at": ticket.closed_at.isoformat() if ticket.closed_at else None,
        "user": {
            "id": ticket.user.id,
            "username": ticket.user.username,
            "email": ticket.user.email,
        } if ticket.user else None,
        "organization": {
            "id": ticket.organization.id,
            "name": ticket.organization.name,
        } if ticket.organization else None,
        "attachments": [
            {
                "id": a.id,
                "file_name": a.file_name,
                "mime_type": a.mime_type,
                "file_size": a.file_size,
                "url": f"/api/support/attachments/{a.id}",
            }
            for a in (ticket.attachments or [])
        ],
    }
    if include_admin_notes:
        result["admin_notes"] = ticket.admin_notes
    return result


@router.post(
    "/tickets",
    summary='File a support ticket',
    description='Creates a SupportTicket on behalf of the calling user. Optionally attach a screenshot via the attachment fields. Notifies platform staff.\n\n**Body:** `{ subject, body, severity?: "low"|"normal"|"high", attachment_storage_object_ids?: int[] }`.\n**Auth:** Bearer JWT.\n**Response:** the created ticket.',
)
async def create_ticket(
    category: str = Form(...),
    subject: str = Form(...),
    description: str = Form(...),
    attachments: Optional[List[UploadFile]] = File(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    valid_categories = {"BUG_REPORT", "FEATURE_REQUEST", "GENERAL_SUPPORT"}
    if category not in valid_categories:
        raise HTTPException(status_code=422, detail=f"Invalid category. Must be one of: {', '.join(sorted(valid_categories))}")

    if not subject.strip():
        raise HTTPException(status_code=422, detail="Subject is required")
    if not description.strip():
        raise HTTPException(status_code=422, detail="Description is required")
    if len(subject) > 500:
        raise HTTPException(status_code=422, detail="Subject must be 500 characters or less")

    membership = db.query(OrganizationMember).filter(
        OrganizationMember.user_id == current_user.id
    ).first()
    org_id = membership.organization_id if membership else None

    ticket = SupportTicket(
        user_id=current_user.id,
        organization_id=org_id,
        category=category,
        subject=subject.strip(),
        description=description.strip(),
        status="OPEN",
    )
    db.add(ticket)
    db.flush()

    if attachments:
        if len(attachments) > MAX_ATTACHMENTS:
            raise HTTPException(status_code=422, detail=f"Maximum {MAX_ATTACHMENTS} attachments allowed")

        for upload_file in attachments:
            if not upload_file.filename:
                continue

            content_type = upload_file.content_type or ""
            if content_type not in ALLOWED_TYPES:
                raise HTTPException(status_code=422, detail=f"File type '{content_type}' not allowed. Use JPEG, PNG, WebP, or GIF.")

            file_bytes = await upload_file.read()
            if len(file_bytes) > MAX_FILE_SIZE:
                raise HTTPException(status_code=422, detail=f"File '{upload_file.filename}' exceeds 5MB limit")

            file_id = str(uuid.uuid4())[:12]
            original_name = Path(upload_file.filename).name
            safe_name = f"{file_id}_{original_name}"
            safe_name = safe_name.replace("/", "_").replace("\\", "_").replace("..", "_")
            file_path = (UPLOAD_DIR / safe_name).resolve()

            if not str(file_path).startswith(str(UPLOAD_DIR.resolve())):
                raise HTTPException(status_code=422, detail="Invalid filename")

            with open(file_path, "wb") as f:
                f.write(file_bytes)

            attachment = SupportTicketAttachment(
                ticket_id=ticket.id,
                file_path=str(file_path),
                file_name=upload_file.filename,
                mime_type=content_type,
                file_size=len(file_bytes),
            )
            db.add(attachment)

    db.commit()
    db.refresh(ticket)

    logger.info(f"Support ticket #{ticket.id} created by user {current_user.username} ({category})")

    return _ticket_to_dict(ticket)


@router.get(
    "/tickets",
    summary="List the calling user's support tickets",
    description='Returns every ticket the user has filed and its current status.\n\n**Query:** `status`, `limit`, `offset`.\n**Auth:** Bearer JWT.\n**Response:** `{ total, tickets: [{id, subject, status, severity, created_at, last_reply_at}] }`.',
)
def list_my_tickets(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    tickets = (
        db.query(SupportTicket)
        .filter(SupportTicket.user_id == current_user.id)
        .order_by(SupportTicket.created_at.desc())
        .all()
    )
    return {"tickets": [_ticket_to_dict(t) for t in tickets]}


@router.get(
    "/tickets/{ticket_id}",
    summary='Get a single support ticket with its replies',
    description='Returns the ticket header plus the full reply thread (visible fields only — admin-only notes are excluded).\n\n**Path parameter:** `ticket_id`.\n**Auth:** Bearer JWT — must be the ticket creator.\n**Response:** `{ id, subject, body, status, severity, replies: [{id, author, body, created_at}], attachments: [...] }`.',
)
def get_ticket(
    ticket_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ticket = db.query(SupportTicket).filter(SupportTicket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    if ticket.user_id != current_user.id and not current_user.is_super_admin:
        raise HTTPException(status_code=403, detail="Access denied")

    return _ticket_to_dict(ticket, include_admin_notes=current_user.is_super_admin)


@router.get(
    "/attachments/{attachment_id}",
    summary='Download a support-ticket attachment',
    description='Streams the binary attachment file.\n\n**Path parameter:** `attachment_id`.\n**Auth:** Bearer JWT — must be the ticket creator or staff.\n**Response:** the file with the appropriate `Content-Type`.',
)
def get_attachment(
    attachment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from fastapi.responses import FileResponse

    attachment = db.query(SupportTicketAttachment).filter(SupportTicketAttachment.id == attachment_id).first()
    if not attachment:
        raise HTTPException(status_code=404, detail="Attachment not found")

    ticket = db.query(SupportTicket).filter(SupportTicket.id == attachment.ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Attachment not found")
    if ticket.user_id != current_user.id and not current_user.is_super_admin:
        raise HTTPException(status_code=403, detail="Access denied")

    if not os.path.exists(attachment.file_path):
        raise HTTPException(status_code=404, detail="File not found")

    return FileResponse(
        attachment.file_path,
        media_type=attachment.mime_type or "application/octet-stream",
        filename=attachment.file_name,
    )
