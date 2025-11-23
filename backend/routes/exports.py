from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from io import StringIO
from ..models import get_db, Creator, OrganizationMember, User
from ..utils.auth import get_current_user
from ..services.schedule_a_service import generate_schedule_a_csv

router = APIRouter(prefix="/api/creators", tags=["exports"])

@router.get("/{creator_id}/schedule-a")
def export_schedule_a(
    creator_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Export Schedule A CSV for a creator's catalog"""
    
    creator = db.query(Creator).filter(Creator.id == creator_id).first()
    
    if not creator:
        raise HTTPException(status_code=404, detail="Creator not found")
    
    membership = db.query(OrganizationMember).filter(
        OrganizationMember.user_id == current_user.id,
        OrganizationMember.organization_id == creator.organization_id
    ).first()
    
    if not membership:
        raise HTTPException(status_code=403, detail="Not authorized to access this creator")
    
    try:
        csv_content = generate_schedule_a_csv(creator_id, db)
        
        return StreamingResponse(
            iter([csv_content]),
            media_type="text/csv",
            headers={
                "Content-Disposition": f"attachment; filename=schedule_a_{creator.display_name.replace(' ', '_')}.csv"
            }
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
