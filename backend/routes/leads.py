from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from html import escape as html_escape
import logging
import re
import os
import uuid

from ..models import get_db, Lead, User
from ..utils.auth import get_current_super_admin

logger = logging.getLogger("cadence")

router = APIRouter(prefix="/api/public", tags=["Public Leads"])
admin_router = APIRouter(prefix="/api/admin", tags=["Public Leads"])


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


class InvestorInquiryRequest(BaseModel):
    name: str
    email: str
    firm: str
    investment_focus: Optional[str] = None
    message: Optional[str] = None


@router.post("/investor-inquiry")
def submit_investor_inquiry(request: InvestorInquiryRequest, db: Session = Depends(get_db)):
    email = _validate_email(request.email)

    lead = Lead(
        email=email,
        name=request.name.strip() if request.name else None,
        company=request.firm.strip() if request.firm else None,
        message=f"Investment Focus: {request.investment_focus or 'N/A'}\n{request.message or ''}".strip(),
        lead_type="INVESTOR_INQUIRY",
    )
    db.add(lead)
    db.commit()

    try:
        from ..services.email_provider import get_email_provider
        provider = get_email_provider()
        safe_inv = {
            "name": html_escape(request.name or "") or "N/A",
            "email": html_escape(email),
            "firm": html_escape(request.firm or "") or "N/A",
            "focus": html_escape(request.investment_focus or "") or "N/A",
            "message": html_escape(request.message or "") or "N/A",
        }
        provider.send_email(
            to="communication@cadence-ci.com",
            subject=f"New Investor Inquiry: {request.name or email}",
            html_body=f"""
            <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 600px; margin: 0 auto;">
                <div style="background: linear-gradient(135deg, #5B8A72, #7BA594); padding: 30px; border-radius: 12px 12px 0 0;">
                    <h1 style="color: white; margin: 0; font-size: 24px;">New Investor Inquiry</h1>
                </div>
                <div style="background: #f9fafb; padding: 30px; border-radius: 0 0 12px 12px;">
                    <p style="color: #3D4A44; font-size: 16px; margin: 0 0 8px;"><strong>Name:</strong> {safe_inv['name']}</p>
                    <p style="color: #3D4A44; font-size: 16px; margin: 0 0 8px;"><strong>Email:</strong> {safe_inv['email']}</p>
                    <p style="color: #3D4A44; font-size: 16px; margin: 0 0 8px;"><strong>Firm / Fund:</strong> {safe_inv['firm']}</p>
                    <p style="color: #3D4A44; font-size: 16px; margin: 0 0 8px;"><strong>Investment Focus:</strong> {safe_inv['focus']}</p>
                    <p style="color: #3D4A44; font-size: 16px; margin: 0 0 8px;"><strong>Message:</strong> {safe_inv['message']}</p>
                    <p style="color: #7A8580; font-size: 14px; margin: 16px 0 0;">Submitted at {datetime.utcnow().strftime('%B %d, %Y at %I:%M %p')} UTC</p>
                </div>
            </div>
            """,
        )
    except Exception as e:
        logger.error(f"Failed to send investor inquiry notification: {e}")

    return {"message": "Thank you for your interest. Our team will be in touch shortly.", "status": "created"}


RESUME_UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "uploads", "resumes")
ALLOWED_RESUME_TYPES = {
    "application/pdf",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}
MAX_RESUME_SIZE = 10 * 1024 * 1024


@router.post("/intern-application")
async def submit_intern_application(
    name: str = Form(...),
    email: str = Form(...),
    role: str = Form(...),
    location: Optional[str] = Form(None),
    linkedin: Optional[str] = Form(None),
    portfolio: Optional[str] = Form(None),
    experience: Optional[str] = Form(None),
    why_cadence: Optional[str] = Form(None),
    resume: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
):
    validated_email = _validate_email(email)

    name = (name or "").strip()
    role = (role or "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="Name is required.")
    if not role:
        raise HTTPException(status_code=400, detail="Role is required.")

    resume_path = None
    resume_data = None
    resume_filename = None
    resume_mime = None
    if resume and resume.filename:
        if resume.content_type not in ALLOWED_RESUME_TYPES:
            raise HTTPException(status_code=400, detail="Resume must be a PDF or Word document.")
        content = await resume.read()
        if len(content) > MAX_RESUME_SIZE:
            raise HTTPException(status_code=400, detail="Resume file must be under 10MB.")
        resume_data = content
        resume_filename = resume.filename
        resume_mime = resume.content_type or "application/pdf"
        ext = os.path.splitext(resume.filename)[1] or ".pdf"
        filename = f"{uuid.uuid4().hex}{ext}"
        resume_path = f"uploads/resumes/{filename}"

    details = []
    if location:
        details.append(f"Location: {location.strip()}")
    if linkedin:
        details.append(f"LinkedIn: {linkedin.strip()}")
    if portfolio:
        details.append(f"Portfolio: {portfolio.strip()}")
    if experience:
        details.append(f"Experience: {experience.strip()}")
    if why_cadence:
        details.append(f"Why Cadence: {why_cadence.strip()}")
    message_text = "\n".join(details) if details else None

    lead = Lead(
        email=validated_email,
        name=name,
        company=role,
        message=message_text,
        lead_type="INTERN_APPLICATION",
        resume_path=resume_path,
        resume_data=resume_data,
        resume_filename=resume_filename,
        resume_mime=resume_mime,
    )
    db.add(lead)
    db.commit()

    try:
        from ..services.email_provider import get_email_provider
        provider = get_email_provider()
        safe = {
            "name": html_escape(name),
            "email": html_escape(validated_email),
            "role": html_escape(role),
            "location": html_escape(location or "") or "N/A",
            "linkedin": html_escape(linkedin or "") or "N/A",
            "portfolio": html_escape(portfolio or "") or "N/A",
            "experience": html_escape(experience or "") or "N/A",
            "why_cadence": html_escape(why_cadence or "") or "N/A",
        }
        resume_line = f'<p style="color: #3D4A44; font-size: 16px; margin: 0 0 8px;"><strong>Resume:</strong> Attached ({html_escape(resume.filename)})</p>' if resume_path else ''
        provider.send_email(
            to="communication@cadence-ci.com",
            subject=f"New Intern Application: {name} - {role}",
            html_body=f"""
            <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 600px; margin: 0 auto;">
                <div style="background: linear-gradient(135deg, #5B8A72, #7BA594); padding: 30px; border-radius: 12px 12px 0 0;">
                    <h1 style="color: white; margin: 0; font-size: 24px;">New Intern Application</h1>
                </div>
                <div style="background: #f9fafb; padding: 30px; border-radius: 0 0 12px 12px;">
                    <p style="color: #3D4A44; font-size: 16px; margin: 0 0 8px;"><strong>Name:</strong> {safe['name']}</p>
                    <p style="color: #3D4A44; font-size: 16px; margin: 0 0 8px;"><strong>Email:</strong> {safe['email']}</p>
                    <p style="color: #3D4A44; font-size: 16px; margin: 0 0 8px;"><strong>Role:</strong> {safe['role']}</p>
                    <p style="color: #3D4A44; font-size: 16px; margin: 0 0 8px;"><strong>Location:</strong> {safe['location']}</p>
                    <p style="color: #3D4A44; font-size: 16px; margin: 0 0 8px;"><strong>LinkedIn:</strong> {safe['linkedin']}</p>
                    <p style="color: #3D4A44; font-size: 16px; margin: 0 0 8px;"><strong>Portfolio:</strong> {safe['portfolio']}</p>
                    <p style="color: #3D4A44; font-size: 16px; margin: 0 0 8px;"><strong>Experience:</strong> {safe['experience']}</p>
                    <p style="color: #3D4A44; font-size: 16px; margin: 0 0 8px;"><strong>Why Cadence:</strong> {safe['why_cadence']}</p>
                    {resume_line}
                    <p style="color: #7A8580; font-size: 14px; margin: 16px 0 0;">Submitted at {datetime.utcnow().strftime('%B %d, %Y at %I:%M %p')} UTC</p>
                </div>
            </div>
            """,
        )
    except Exception as e:
        logger.error(f"Failed to send intern application notification: {e}")

    return {"message": "Application submitted! We'll review it and reach out if there's a fit.", "status": "created"}


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
                "resume_path": l.resume_path,
                "created_at": l.created_at.isoformat() if l.created_at else None,
            }
            for l in leads
        ],
        "total": len(leads),
    }


@admin_router.get("/leads/{lead_id}/resume")
def download_resume(
    lead_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_super_admin),
):
    lead = db.query(Lead).filter(Lead.id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Resume not found.")

    if lead.resume_data:
        from fastapi.responses import Response
        filename = lead.resume_filename or "resume.pdf"
        mime = lead.resume_mime or "application/octet-stream"
        return Response(
            content=lead.resume_data,
            media_type=mime,
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )

    if lead.resume_path:
        filepath = os.path.join(os.path.dirname(os.path.dirname(__file__)), lead.resume_path)
        if os.path.exists(filepath):
            return FileResponse(filepath, filename=os.path.basename(filepath), media_type="application/octet-stream")

    raise HTTPException(status_code=404, detail="Resume file not found.")
