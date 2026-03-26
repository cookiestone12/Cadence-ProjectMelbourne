from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
import logging
import re

from ..models import get_db, Lead, User
from ..utils.auth import get_current_super_admin

logger = logging.getLogger("cadence")

router = APIRouter(prefix="/api/public", tags=["leads"])
admin_router = APIRouter(prefix="/api/admin", tags=["admin-leads"])


class WaitlistRequest(BaseModel):
    email: str


class DemoRequest(BaseModel):
    name: str
    email: str
    company: str
    message: Optional[str] = None


def _validate_email(email: str) -> str:
    email = email.strip().lower()
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(pattern, email):
        raise HTTPException(status_code=400, detail="Invalid email address")
    return email


def _send_lead_notification(lead_type: str, email: str, name: str = None, company: str = None, message: str = None):
    try:
        from ..services.email_provider import get_email_provider
        provider = get_email_provider()

        if lead_type == "WAITLIST":
            subject = f"New Waitlist Signup: {email}"
            html = f"""
            <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 600px; margin: 0 auto;">
                <div style="background: linear-gradient(135deg, #5B8A72, #7BA594); padding: 30px; border-radius: 12px 12px 0 0;">
                    <h1 style="color: white; margin: 0; font-size: 24px;">New Waitlist Signup</h1>
                </div>
                <div style="background: #f9fafb; padding: 30px; border-radius: 0 0 12px 12px;">
                    <p style="color: #3D4A44; font-size: 16px; margin: 0 0 8px;"><strong>Email:</strong> {email}</p>
                    <p style="color: #7A8580; font-size: 14px; margin: 16px 0 0;">Submitted at {datetime.utcnow().strftime('%B %d, %Y at %I:%M %p')} UTC</p>
                </div>
            </div>
            """
        else:
            subject = f"New Demo Request: {name or email}"
            html = f"""
            <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 600px; margin: 0 auto;">
                <div style="background: linear-gradient(135deg, #5B8A72, #7BA594); padding: 30px; border-radius: 12px 12px 0 0;">
                    <h1 style="color: white; margin: 0; font-size: 24px;">New Demo Request</h1>
                </div>
                <div style="background: #f9fafb; padding: 30px; border-radius: 0 0 12px 12px;">
                    <p style="color: #3D4A44; font-size: 16px; margin: 0 0 8px;"><strong>Name:</strong> {name or 'N/A'}</p>
                    <p style="color: #3D4A44; font-size: 16px; margin: 0 0 8px;"><strong>Email:</strong> {email}</p>
                    <p style="color: #3D4A44; font-size: 16px; margin: 0 0 8px;"><strong>Company:</strong> {company or 'N/A'}</p>
                    <p style="color: #3D4A44; font-size: 16px; margin: 0 0 8px;"><strong>Message:</strong> {message or 'N/A'}</p>
                    <p style="color: #7A8580; font-size: 14px; margin: 16px 0 0;">Submitted at {datetime.utcnow().strftime('%B %d, %Y at %I:%M %p')} UTC</p>
                </div>
            </div>
            """

        provider.send_email(
            to="communication@cadence-ci.com",
            subject=subject,
            html_body=html,
        )
    except Exception as e:
        logger.error(f"Failed to send lead notification email: {e}")


@router.post("/waitlist")
def join_waitlist(request: WaitlistRequest, db: Session = Depends(get_db)):
    email = _validate_email(request.email)

    existing = db.query(Lead).filter(
        Lead.email == email,
        Lead.lead_type == "WAITLIST",
    ).first()
    if existing:
        return {"message": "You're already on the waitlist!", "status": "existing"}

    lead = Lead(
        email=email,
        lead_type="WAITLIST",
    )
    db.add(lead)
    db.commit()

    _send_lead_notification("WAITLIST", email)

    return {"message": "You've been added to the waitlist!", "status": "created"}


@router.post("/demo-request")
def request_demo(request: DemoRequest, db: Session = Depends(get_db)):
    email = _validate_email(request.email)

    lead = Lead(
        email=email,
        name=request.name.strip() if request.name else None,
        company=request.company.strip() if request.company else None,
        message=request.message.strip() if request.message else None,
        lead_type="DEMO_REQUEST",
    )
    db.add(lead)
    db.commit()

    _send_lead_notification(
        "DEMO_REQUEST", email,
        name=request.name, company=request.company, message=request.message,
    )

    return {"message": "Demo request submitted! We'll be in touch soon.", "status": "created"}


@admin_router.get("/leads")
def list_leads(
    lead_type: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_super_admin),
):
    query = db.query(Lead).order_by(Lead.created_at.desc())
    if lead_type:
        query = query.filter(Lead.lead_type == lead_type)
    leads = query.all()

    return {
        "leads": [
            {
                "id": l.id,
                "email": l.email,
                "name": l.name,
                "company": l.company,
                "message": l.message,
                "lead_type": l.lead_type,
                "created_at": l.created_at.isoformat() if l.created_at else None,
            }
            for l in leads
        ],
        "total": len(leads),
    }
