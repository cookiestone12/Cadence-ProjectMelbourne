from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

from ..models import get_db, Organization, AccountLink, User, OrganizationMember
from ..utils.auth import get_current_user

router = APIRouter(prefix="/api/account-links", tags=["account_links"])

class CreateLinkRequest(BaseModel):
    individual_org_id: int
    enterprise_org_id: int
    permission_level: str = "VIEW_ONLY"
    initiated_by: str
    agreement_terms: Optional[str] = None
    expiration_date: Optional[datetime] = None

class UpdateLinkRequest(BaseModel):
    permission_level: Optional[str] = None
    agreement_terms: Optional[str] = None
    expiration_date: Optional[datetime] = None

class ConsentRequest(BaseModel):
    consent_type: str

class LinkResponse(BaseModel):
    id: int
    individual_org_id: int
    enterprise_org_id: int
    status: str
    permission_level: str
    initiated_by: str
    individual_consent: bool
    enterprise_consent: bool
    agreement_terms: Optional[str]
    start_date: Optional[datetime]
    expiration_date: Optional[datetime]
    created_at: datetime
    individual_org_name: Optional[str] = None
    enterprise_org_name: Optional[str] = None
    
    class Config:
        from_attributes = True

@router.post("/request", response_model=LinkResponse)
def request_link(
    request: CreateLinkRequest, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    individual_org = db.query(Organization).filter(Organization.id == request.individual_org_id).first()
    if not individual_org:
        raise HTTPException(status_code=404, detail="Individual organization not found")
    
    if individual_org.account_type and individual_org.account_type != "INDIVIDUAL":
        raise HTTPException(status_code=400, detail="The individual_org must have account_type INDIVIDUAL")
    
    enterprise_org = db.query(Organization).filter(Organization.id == request.enterprise_org_id).first()
    if not enterprise_org:
        raise HTTPException(status_code=404, detail="Enterprise organization not found")
    
    if enterprise_org.account_type and enterprise_org.account_type != "ENTERPRISE":
        raise HTTPException(status_code=400, detail="The enterprise_org must have account_type ENTERPRISE")
    
    requester_org_id = request.individual_org_id if request.initiated_by == "INDIVIDUAL" else request.enterprise_org_id
    membership = db.query(OrganizationMember).filter(
        OrganizationMember.user_id == current_user.id,
        OrganizationMember.organization_id == requester_org_id
    ).first()
    
    if not membership:
        raise HTTPException(status_code=403, detail="Not authorized to request link for this organization")
    
    existing = db.query(AccountLink).filter(
        AccountLink.individual_org_id == request.individual_org_id,
        AccountLink.enterprise_org_id == request.enterprise_org_id,
        AccountLink.status.in_(["PENDING", "ACTIVE"])
    ).first()
    
    if existing:
        raise HTTPException(status_code=400, detail="Link already exists or is pending")
    
    link = AccountLink(
        individual_org_id=request.individual_org_id,
        enterprise_org_id=request.enterprise_org_id,
        permission_level=request.permission_level,
        initiated_by=request.initiated_by,
        agreement_terms=request.agreement_terms,
        expiration_date=request.expiration_date,
        individual_consent=(request.initiated_by == "INDIVIDUAL"),
        enterprise_consent=(request.initiated_by == "ENTERPRISE")
    )
    
    db.add(link)
    db.commit()
    db.refresh(link)
    
    return _build_link_response(link, db)

@router.post("/{link_id}/consent", response_model=LinkResponse)
def give_consent(
    link_id: int, 
    request: ConsentRequest, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    link = db.query(AccountLink).filter(AccountLink.id == link_id).first()
    if not link:
        raise HTTPException(status_code=404, detail="Link not found")
    
    consent_org_id = link.individual_org_id if request.consent_type == "INDIVIDUAL" else link.enterprise_org_id
    membership = db.query(OrganizationMember).filter(
        OrganizationMember.user_id == current_user.id,
        OrganizationMember.organization_id == consent_org_id
    ).first()
    
    if not membership:
        raise HTTPException(status_code=403, detail="Not authorized to consent for this organization")
    
    if link.status != "PENDING":
        raise HTTPException(status_code=400, detail="Link is not pending")
    
    if request.consent_type == "INDIVIDUAL":
        link.individual_consent = True
    elif request.consent_type == "ENTERPRISE":
        link.enterprise_consent = True
    else:
        raise HTTPException(status_code=400, detail="Invalid consent type")
    
    if link.individual_consent and link.enterprise_consent:
        link.status = "ACTIVE"
        link.start_date = datetime.utcnow()
    
    db.commit()
    db.refresh(link)
    
    return _build_link_response(link, db)

@router.post("/{link_id}/revoke", response_model=LinkResponse)
def revoke_link(
    link_id: int, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    link = db.query(AccountLink).filter(AccountLink.id == link_id).first()
    if not link:
        raise HTTPException(status_code=404, detail="Link not found")
    
    membership_individual = db.query(OrganizationMember).filter(
        OrganizationMember.user_id == current_user.id,
        OrganizationMember.organization_id == link.individual_org_id
    ).first()
    
    membership_enterprise = db.query(OrganizationMember).filter(
        OrganizationMember.user_id == current_user.id,
        OrganizationMember.organization_id == link.enterprise_org_id
    ).first()
    
    if not membership_individual and not membership_enterprise:
        raise HTTPException(status_code=403, detail="Not authorized to revoke this link")
    
    link.status = "REVOKED"
    db.commit()
    db.refresh(link)
    
    return _build_link_response(link, db)

@router.get("/organization/{org_id}", response_model=List[LinkResponse])
def get_links_for_organization(
    org_id: int, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    membership = db.query(OrganizationMember).filter(
        OrganizationMember.user_id == current_user.id,
        OrganizationMember.organization_id == org_id
    ).first()
    
    if not membership:
        raise HTTPException(status_code=403, detail="Not authorized to view links for this organization")
    
    links = db.query(AccountLink).filter(
        (AccountLink.individual_org_id == org_id) | 
        (AccountLink.enterprise_org_id == org_id)
    ).all()
    
    return [_build_link_response(link, db) for link in links]

@router.get("/pending/{org_id}", response_model=List[LinkResponse])
def get_pending_links(
    org_id: int, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    membership = db.query(OrganizationMember).filter(
        OrganizationMember.user_id == current_user.id,
        OrganizationMember.organization_id == org_id
    ).first()
    
    if not membership:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    links = db.query(AccountLink).filter(
        ((AccountLink.individual_org_id == org_id) | (AccountLink.enterprise_org_id == org_id)),
        AccountLink.status == "PENDING"
    ).all()
    
    return [_build_link_response(link, db) for link in links]

@router.get("/active/{org_id}", response_model=List[LinkResponse])
def get_active_links(
    org_id: int, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    membership = db.query(OrganizationMember).filter(
        OrganizationMember.user_id == current_user.id,
        OrganizationMember.organization_id == org_id
    ).first()
    
    if not membership:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    now = datetime.utcnow()
    links = db.query(AccountLink).filter(
        ((AccountLink.individual_org_id == org_id) | (AccountLink.enterprise_org_id == org_id)),
        AccountLink.status == "ACTIVE"
    ).all()
    
    active_links = []
    for link in links:
        if link.expiration_date and link.expiration_date < now:
            link.status = "EXPIRED"
        else:
            active_links.append(link)
    
    db.commit()
    
    return [_build_link_response(link, db) for link in active_links]

@router.put("/{link_id}", response_model=LinkResponse)
def update_link(
    link_id: int, 
    request: UpdateLinkRequest, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    link = db.query(AccountLink).filter(AccountLink.id == link_id).first()
    if not link:
        raise HTTPException(status_code=404, detail="Link not found")
    
    membership = db.query(OrganizationMember).filter(
        OrganizationMember.user_id == current_user.id,
        OrganizationMember.organization_id.in_([link.individual_org_id, link.enterprise_org_id])
    ).first()
    
    if not membership:
        raise HTTPException(status_code=403, detail="Not authorized to update this link")
    
    if request.permission_level:
        link.permission_level = request.permission_level
    if request.agreement_terms is not None:
        link.agreement_terms = request.agreement_terms
    if request.expiration_date is not None:
        link.expiration_date = request.expiration_date
    
    db.commit()
    db.refresh(link)
    
    return _build_link_response(link, db)

def _build_link_response(link: AccountLink, db: Session) -> dict:
    individual_org = db.query(Organization).filter(Organization.id == link.individual_org_id).first()
    enterprise_org = db.query(Organization).filter(Organization.id == link.enterprise_org_id).first()
    
    return {
        "id": link.id,
        "individual_org_id": link.individual_org_id,
        "enterprise_org_id": link.enterprise_org_id,
        "status": link.status,
        "permission_level": link.permission_level,
        "initiated_by": link.initiated_by,
        "individual_consent": link.individual_consent,
        "enterprise_consent": link.enterprise_consent,
        "agreement_terms": link.agreement_terms,
        "start_date": link.start_date,
        "expiration_date": link.expiration_date,
        "created_at": link.created_at,
        "individual_org_name": individual_org.name if individual_org else None,
        "enterprise_org_name": enterprise_org.name if enterprise_org else None
    }
