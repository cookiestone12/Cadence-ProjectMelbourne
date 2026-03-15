from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
import os
import uuid
from pathlib import Path

from ..models import get_db, Song, SongContract, Organization, OrganizationMember, User, AccountLink
from ..utils.auth import get_current_user, verify_token

def check_linked_access(db: Session, user_id: int, target_org_id: int, permission_level: str = "VIEW") -> bool:
    """Check if user has access to target org via an active, non-expired account link."""
    user_memberships = db.query(OrganizationMember).filter(
        OrganizationMember.user_id == user_id
    ).all()
    user_org_ids = [m.organization_id for m in user_memberships]
    
    now = datetime.utcnow()
    
    for org_id in user_org_ids:
        link = db.query(AccountLink).filter(
            AccountLink.status == "ACTIVE",
            (
                (AccountLink.individual_org_id == org_id) & (AccountLink.enterprise_org_id == target_org_id) |
                (AccountLink.enterprise_org_id == org_id) & (AccountLink.individual_org_id == target_org_id)
            )
        ).first()
        
        if link:
            if link.expiration_date and link.expiration_date < now:
                link.status = "EXPIRED"
                db.commit()
                continue
            
            if permission_level == "VIEW":
                return True
            elif permission_level == "MANAGE" and link.permission_level in ["MANAGE", "FULL"]:
                return True
            elif permission_level == "FULL" and link.permission_level == "FULL":
                return True
    
    return False

router = APIRouter(prefix="/api/contracts", tags=["contracts"])

UPLOAD_DIR = Path("uploads/contracts")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

class ContractResponse(BaseModel):
    id: int
    song_id: int
    file_name: str
    file_size_bytes: Optional[int]
    mime_type: str
    contract_type: Optional[str]
    description: Optional[str]
    created_at: datetime
    
    class Config:
        from_attributes = True

@router.post("/upload/{song_id}", response_model=ContractResponse)
async def upload_contract(
    song_id: int,
    file: UploadFile = File(...),
    contract_type: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    song = db.query(Song).filter(Song.id == song_id).first()
    if not song:
        raise HTTPException(status_code=404, detail="Song not found")
    
    membership = db.query(OrganizationMember).filter(
        OrganizationMember.user_id == current_user.id,
        OrganizationMember.organization_id == song.organization_id
    ).first()
    
    if not membership:
        raise HTTPException(status_code=403, detail="Not authorized to upload contracts for this song")
    
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")
    
    if file.content_type and file.content_type != 'application/pdf':
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")
    
    file_id = str(uuid.uuid4())
    safe_filename = f"{file_id}_{file.filename}"
    file_path = UPLOAD_DIR / safe_filename
    
    content = await file.read()
    file_size = len(content)
    
    with open(file_path, "wb") as f:
        f.write(content)
    
    contract = SongContract(
        song_id=song_id,
        organization_id=song.organization_id,
        file_name=file.filename,
        file_path=str(file_path),
        file_size_bytes=file_size,
        mime_type="application/pdf",
        contract_type=contract_type,
        description=description,
        uploaded_by_user_id=current_user.id
    )
    
    db.add(contract)
    
    song.has_contract_executed = True
    song.has_contract_sent = True
    
    db.flush()
    from ..services.audit_service import log_action
    log_action(db, song.organization_id, current_user.id, "UPLOAD", "CONTRACT", contract.id, file.filename,
               details={"song_id": song_id, "song_title": song.title, "contract_type": contract_type})

    db.commit()
    db.refresh(contract)
    
    return contract

@router.get("/song/{song_id}", response_model=List[ContractResponse])
def get_contracts_for_song(
    song_id: int, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    song = db.query(Song).filter(Song.id == song_id).first()
    if not song:
        raise HTTPException(status_code=404, detail="Song not found")
    
    membership = db.query(OrganizationMember).filter(
        OrganizationMember.user_id == current_user.id,
        OrganizationMember.organization_id == song.organization_id
    ).first()
    
    has_linked_access = check_linked_access(db, current_user.id, song.organization_id, "VIEW")
    
    if not membership and not has_linked_access:
        raise HTTPException(status_code=403, detail="Not authorized to view contracts for this song")
    
    contracts = db.query(SongContract).filter(SongContract.song_id == song_id).all()
    return contracts

@router.get("/download/{contract_id}")
def download_contract(
    contract_id: int, 
    db: Session = Depends(get_db),
    token: Optional[str] = Query(None)
):
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    username = verify_token(token)
    if not username:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    
    contract = db.query(SongContract).filter(SongContract.id == contract_id).first()
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")
    
    membership = db.query(OrganizationMember).filter(
        OrganizationMember.user_id == user.id,
        OrganizationMember.organization_id == contract.organization_id
    ).first()
    
    has_linked_access = check_linked_access(db, user.id, contract.organization_id, "VIEW")
    
    if not membership and not has_linked_access:
        raise HTTPException(status_code=403, detail="Not authorized to download this contract")
    
    file_path = Path(contract.file_path)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Contract file not found")
    
    return FileResponse(
        path=str(file_path),
        filename=contract.file_name,
        media_type="application/pdf"
    )

@router.delete("/{contract_id}")
def delete_contract(
    contract_id: int, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    contract = db.query(SongContract).filter(SongContract.id == contract_id).first()
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")
    
    membership = db.query(OrganizationMember).filter(
        OrganizationMember.user_id == current_user.id,
        OrganizationMember.organization_id == contract.organization_id
    ).first()
    
    if not membership:
        raise HTTPException(status_code=403, detail="Not authorized to delete this contract")
    
    file_path = Path(contract.file_path)
    if file_path.exists():
        os.remove(file_path)
    
    remaining = db.query(SongContract).filter(
        SongContract.song_id == contract.song_id,
        SongContract.id != contract_id
    ).count()
    
    song = db.query(Song).filter(Song.id == contract.song_id).first()
    if song and remaining == 0:
        song.has_contract_executed = False
        song.has_contract_sent = False
    
    from ..services.audit_service import log_action
    log_action(db, contract.organization_id, current_user.id, "DELETE", "CONTRACT", contract.id, contract.file_name,
               details={"song_id": contract.song_id})

    db.delete(contract)
    db.commit()
    
    return {"message": "Contract deleted successfully"}
