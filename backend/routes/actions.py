from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func, case, desc, asc
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime, timedelta
from ..models import get_db, ActionItem, Song, Creator, OrganizationMember, User
from ..utils.auth import get_current_user

router = APIRouter(prefix="/api/actions", tags=["actions"])

class ActionItemCreate(BaseModel):
    creator_id: Optional[int] = None
    song_id: Optional[int] = None
    action_type: str
    title: str
    description: Optional[str] = None
    priority: int = 2
    deadline: Optional[datetime] = None
    reminder_days_before: int = 3
    assigned_to_user_id: Optional[int] = None

class ActionItemUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    priority: Optional[int] = None
    status: Optional[str] = None
    deadline: Optional[datetime] = None
    reminder_days_before: Optional[int] = None
    assigned_to_user_id: Optional[int] = None

class ActionItemResponse(BaseModel):
    id: int
    organization_id: int
    creator_id: Optional[int]
    song_id: Optional[int]
    action_type: str
    title: str
    description: Optional[str]
    priority: int
    status: str
    deadline: Optional[datetime]
    reminder_days_before: int
    assigned_to_user_id: Optional[int]
    created_at: datetime
    updated_at: datetime
    creator_name: Optional[str] = None
    song_title: Optional[str] = None
    assigned_to_name: Optional[str] = None
    days_until_deadline: Optional[int] = None
    is_overdue: bool = False

    class Config:
        from_attributes = True


def get_user_organization_id(db: Session, user: User) -> int:
    membership = db.query(OrganizationMember).filter(
        OrganizationMember.user_id == user.id
    ).first()
    if not membership:
        raise HTTPException(status_code=403, detail="No organization membership")
    return membership.organization_id


@router.get("/org/{org_id}")
def get_organization_actions(
    org_id: int,
    status: Optional[str] = None,
    creator_id: Optional[int] = None,
    priority: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    membership = db.query(OrganizationMember).filter(
        OrganizationMember.user_id == current_user.id,
        OrganizationMember.organization_id == org_id
    ).first()
    
    if not membership:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    query = db.query(ActionItem).filter(ActionItem.organization_id == org_id)
    
    if status:
        query = query.filter(ActionItem.status == status)
    else:
        query = query.filter(ActionItem.status != "COMPLETED")
    
    if creator_id:
        query = query.filter(ActionItem.creator_id == creator_id)
    
    if priority:
        query = query.filter(ActionItem.priority == priority)
    
    now = datetime.utcnow()
    query = query.order_by(
        asc(ActionItem.priority),
        asc(ActionItem.deadline.is_(None)),
        asc(ActionItem.deadline),
        desc(ActionItem.created_at)
    )
    
    actions = query.all()
    
    result = []
    for action in actions:
        creator_name = None
        if action.creator_id:
            creator = db.query(Creator).filter(Creator.id == action.creator_id).first()
            creator_name = creator.display_name if creator else None
        
        song_title = None
        if action.song_id:
            song = db.query(Song).filter(Song.id == action.song_id).first()
            song_title = song.title if song else None
        
        assigned_to_name = None
        if action.assigned_to_user_id:
            assigned = db.query(User).filter(User.id == action.assigned_to_user_id).first()
            assigned_to_name = assigned.username if assigned else None
        
        days_until = None
        is_overdue = False
        if action.deadline:
            delta = (action.deadline - now).days
            days_until = delta
            is_overdue = delta < 0 and action.status != "COMPLETED"
        
        result.append({
            "id": action.id,
            "organization_id": action.organization_id,
            "creator_id": action.creator_id,
            "song_id": action.song_id,
            "action_type": action.action_type,
            "title": action.title,
            "description": action.description,
            "priority": action.priority,
            "status": action.status,
            "deadline": action.deadline,
            "reminder_days_before": action.reminder_days_before,
            "assigned_to_user_id": action.assigned_to_user_id,
            "created_at": action.created_at,
            "updated_at": action.updated_at,
            "creator_name": creator_name,
            "song_title": song_title,
            "assigned_to_name": assigned_to_name,
            "days_until_deadline": days_until,
            "is_overdue": is_overdue
        })
    
    return result


@router.get("/creator/{creator_id}")
def get_creator_actions(
    creator_id: int,
    include_completed: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    creator = db.query(Creator).filter(Creator.id == creator_id).first()
    if not creator:
        raise HTTPException(status_code=404, detail="Creator not found")
    
    membership = db.query(OrganizationMember).filter(
        OrganizationMember.user_id == current_user.id,
        OrganizationMember.organization_id == creator.organization_id
    ).first()
    
    if not membership:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    query = db.query(ActionItem).filter(ActionItem.creator_id == creator_id)
    
    if not include_completed:
        query = query.filter(ActionItem.status != "COMPLETED")
    
    now = datetime.utcnow()
    query = query.order_by(
        asc(ActionItem.priority),
        asc(ActionItem.deadline.is_(None)),
        asc(ActionItem.deadline),
        desc(ActionItem.created_at)
    )
    
    actions = query.all()
    
    result = []
    for action in actions:
        song_title = None
        if action.song_id:
            song = db.query(Song).filter(Song.id == action.song_id).first()
            song_title = song.title if song else None
        
        days_until = None
        is_overdue = False
        if action.deadline:
            delta = (action.deadline - now).days
            days_until = delta
            is_overdue = delta < 0 and action.status != "COMPLETED"
        
        result.append({
            "id": action.id,
            "organization_id": action.organization_id,
            "creator_id": action.creator_id,
            "song_id": action.song_id,
            "action_type": action.action_type,
            "title": action.title,
            "description": action.description,
            "priority": action.priority,
            "status": action.status,
            "deadline": action.deadline,
            "reminder_days_before": action.reminder_days_before,
            "created_at": action.created_at,
            "updated_at": action.updated_at,
            "song_title": song_title,
            "days_until_deadline": days_until,
            "is_overdue": is_overdue
        })
    
    return result


@router.post("/org/{org_id}")
def create_action_item(
    org_id: int,
    action: ActionItemCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    membership = db.query(OrganizationMember).filter(
        OrganizationMember.user_id == current_user.id,
        OrganizationMember.organization_id == org_id
    ).first()
    
    if not membership:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    new_action = ActionItem(
        organization_id=org_id,
        creator_id=action.creator_id,
        song_id=action.song_id,
        action_type=action.action_type,
        title=action.title,
        description=action.description,
        priority=action.priority,
        deadline=action.deadline,
        reminder_days_before=action.reminder_days_before,
        assigned_to_user_id=action.assigned_to_user_id,
        created_by_user_id=current_user.id
    )
    db.add(new_action)
    db.commit()
    db.refresh(new_action)
    
    return {
        "id": new_action.id,
        "message": "Action item created"
    }


@router.put("/{action_id}")
def update_action_item(
    action_id: int,
    updates: ActionItemUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    action = db.query(ActionItem).filter(ActionItem.id == action_id).first()
    if not action:
        raise HTTPException(status_code=404, detail="Action item not found")
    
    membership = db.query(OrganizationMember).filter(
        OrganizationMember.user_id == current_user.id,
        OrganizationMember.organization_id == action.organization_id
    ).first()
    
    if not membership:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    update_data = updates.dict(exclude_unset=True)
    
    if "status" in update_data and update_data["status"] == "COMPLETED":
        action.completed_at = datetime.utcnow()
        action.completed_by_user_id = current_user.id
    
    for key, value in update_data.items():
        setattr(action, key, value)
    
    db.commit()
    
    return {"message": "Action item updated"}


@router.delete("/{action_id}")
def delete_action_item(
    action_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    action = db.query(ActionItem).filter(ActionItem.id == action_id).first()
    if not action:
        raise HTTPException(status_code=404, detail="Action item not found")
    
    membership = db.query(OrganizationMember).filter(
        OrganizationMember.user_id == current_user.id,
        OrganizationMember.organization_id == action.organization_id
    ).first()
    
    if not membership:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    db.delete(action)
    db.commit()
    
    return {"message": "Action item deleted"}


@router.post("/{action_id}/complete")
def complete_action_item(
    action_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    action = db.query(ActionItem).filter(ActionItem.id == action_id).first()
    if not action:
        raise HTTPException(status_code=404, detail="Action item not found")
    
    membership = db.query(OrganizationMember).filter(
        OrganizationMember.user_id == current_user.id,
        OrganizationMember.organization_id == action.organization_id
    ).first()
    
    if not membership:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    action.status = "COMPLETED"
    action.completed_at = datetime.utcnow()
    action.completed_by_user_id = current_user.id
    
    db.commit()
    
    return {"message": "Action item completed"}


@router.get("/summary/org/{org_id}")
def get_action_summary(
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
    
    total_pending = db.query(ActionItem).filter(
        ActionItem.organization_id == org_id,
        ActionItem.status == "PENDING"
    ).count()
    
    overdue = db.query(ActionItem).filter(
        ActionItem.organization_id == org_id,
        ActionItem.status != "COMPLETED",
        ActionItem.deadline < now
    ).count()
    
    due_this_week = db.query(ActionItem).filter(
        ActionItem.organization_id == org_id,
        ActionItem.status != "COMPLETED",
        ActionItem.deadline >= now,
        ActionItem.deadline <= now + timedelta(days=7)
    ).count()
    
    high_priority = db.query(ActionItem).filter(
        ActionItem.organization_id == org_id,
        ActionItem.status != "COMPLETED",
        ActionItem.priority == 1
    ).count()
    
    return {
        "total_pending": total_pending,
        "overdue": overdue,
        "due_this_week": due_this_week,
        "high_priority": high_priority
    }
