from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func, case, desc, asc
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime, timedelta
from ..models import get_db, ActionItem, Song, Creator, OrganizationMember, User, Work, Release, Contract, Placement
from ..utils.auth import get_current_user

router = APIRouter(prefix="/api/actions", tags=["actions"])

class ActionItemCreate(BaseModel):
    creator_id: Optional[int] = None
    song_id: Optional[int] = None
    work_id: Optional[int] = None
    release_id: Optional[int] = None
    contract_id: Optional[int] = None
    placement_id: Optional[int] = None
    entity_type: Optional[str] = None
    entity_label: Optional[str] = None
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


def get_user_organization_id(db: Session, user: User) -> int:
    membership = db.query(OrganizationMember).filter(
        OrganizationMember.user_id == user.id
    ).first()
    if not membership and not user.is_super_admin:
        raise HTTPException(status_code=403, detail="No organization membership")
    if not membership and user.is_super_admin:
        from ..models import Organization
        first_org = db.query(Organization).first()
        if first_org:
            return first_org.id
        raise HTTPException(status_code=403, detail="No organizations exist")
    return membership.organization_id


def enrich_action(action: ActionItem, db: Session, now: datetime) -> dict:
    creator_name = None
    if action.creator_id:
        creator = db.query(Creator).filter(Creator.id == action.creator_id).first()
        creator_name = creator.display_name if creator else None

    song_title = None
    if action.song_id:
        song = db.query(Song).filter(Song.id == action.song_id).first()
        song_title = song.title if song else None

    work_title = None
    if action.work_id:
        work = db.query(Work).filter(Work.id == action.work_id).first()
        work_title = work.title if work else None

    release_title = None
    if action.release_id:
        release = db.query(Release).filter(Release.id == action.release_id).first()
        release_title = release.title if release else None

    contract_title = None
    if action.contract_id:
        contract = db.query(Contract).filter(Contract.id == action.contract_id).first()
        contract_title = contract.title if contract else None

    placement_title = None
    if action.placement_id:
        placement = db.query(Placement).filter(Placement.id == action.placement_id).first()
        placement_title = placement.title if placement else None

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

    return {
        "id": action.id,
        "organization_id": action.organization_id,
        "creator_id": action.creator_id,
        "song_id": action.song_id,
        "work_id": action.work_id,
        "release_id": action.release_id,
        "contract_id": action.contract_id,
        "placement_id": action.placement_id,
        "entity_type": action.entity_type,
        "entity_label": action.entity_label,
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
        "work_title": work_title,
        "release_title": release_title,
        "contract_title": contract_title,
        "placement_title": placement_title,
        "assigned_to_name": assigned_to_name,
        "days_until_deadline": days_until,
        "is_overdue": is_overdue,
        "is_auto_generated": getattr(action, 'is_auto_generated', False),
    }


@router.get("/org/{org_id}")
def get_organization_actions(
    org_id: int,
    status: Optional[str] = None,
    creator_id: Optional[int] = None,
    priority: Optional[int] = None,
    entity_type: Optional[str] = None,
    action_type: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    membership = db.query(OrganizationMember).filter(
        OrganizationMember.user_id == current_user.id,
        OrganizationMember.organization_id == org_id
    ).first()
    
    if not membership and not current_user.is_super_admin:
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

    if entity_type:
        query = query.filter(ActionItem.entity_type == entity_type)

    if action_type:
        query = query.filter(ActionItem.action_type == action_type)
    
    now = datetime.utcnow()
    query = query.order_by(
        asc(ActionItem.priority),
        asc(ActionItem.deadline.is_(None)),
        asc(ActionItem.deadline),
        desc(ActionItem.created_at)
    )
    
    actions = query.all()
    return [enrich_action(a, db, now) for a in actions]


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
    
    if not membership and not current_user.is_super_admin:
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
    return [enrich_action(a, db, now) for a in actions]


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
    
    if not membership and not current_user.is_super_admin:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    new_action = ActionItem(
        organization_id=org_id,
        creator_id=action.creator_id,
        song_id=action.song_id,
        work_id=action.work_id,
        release_id=action.release_id,
        contract_id=action.contract_id,
        placement_id=action.placement_id,
        entity_type=action.entity_type,
        entity_label=action.entity_label,
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
    
    if not membership and not current_user.is_super_admin:
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
    
    if not membership and not current_user.is_super_admin:
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
    
    if not membership and not current_user.is_super_admin:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    action.status = "COMPLETED"
    action.completed_at = datetime.utcnow()
    action.completed_by_user_id = current_user.id
    
    db.commit()
    
    return {"message": "Action item completed"}


@router.post("/generate/{creator_id}")
def generate_suggested_actions(
    creator_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    from ..utils.catalog_gaps import generate_actions_from_gaps
    
    creator = db.query(Creator).filter(Creator.id == creator_id).first()
    if not creator:
        raise HTTPException(status_code=404, detail="Creator not found")
    
    membership = db.query(OrganizationMember).filter(
        OrganizationMember.user_id == current_user.id,
        OrganizationMember.organization_id == creator.organization_id
    ).first()
    
    if not membership and not current_user.is_super_admin:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    created_count = generate_actions_from_gaps(
        db, 
        creator_id, 
        creator.organization_id,
        current_user.id
    )
    
    return {
        "message": f"Generated {created_count} action items",
        "created_count": created_count
    }


@router.get("/gaps/{creator_id}")
def get_catalog_gaps(
    creator_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    from ..utils.catalog_gaps import analyze_creator_catalog_gaps
    
    creator = db.query(Creator).filter(Creator.id == creator_id).first()
    if not creator:
        raise HTTPException(status_code=404, detail="Creator not found")
    
    membership = db.query(OrganizationMember).filter(
        OrganizationMember.user_id == current_user.id,
        OrganizationMember.organization_id == creator.organization_id
    ).first()
    
    if not membership and not current_user.is_super_admin:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    gaps = analyze_creator_catalog_gaps(db, creator_id)
    return {"gaps": gaps, "total_gaps": len(gaps)}


@router.post("/generate-org/{org_id}")
def generate_org_actions(
    org_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    from ..utils.catalog_gaps import generate_actions_from_gaps
    
    membership = db.query(OrganizationMember).filter(
        OrganizationMember.user_id == current_user.id,
        OrganizationMember.organization_id == org_id
    ).first()
    
    if not membership and not current_user.is_super_admin:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    creators = db.query(Creator).filter(Creator.organization_id == org_id).all()
    
    total_created = 0
    for creator in creators:
        created_count = generate_actions_from_gaps(
            db,
            creator.id,
            org_id,
            current_user.id
        )
        total_created += created_count
    
    return {
        "message": f"Generated {total_created} action items across {len(creators)} creators",
        "created_count": total_created
    }


@router.post("/generate-cross-module/{org_id}")
def generate_cross_module_actions(
    org_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    from ..utils.cross_module_tasks import generate_cross_module_tasks

    membership = db.query(OrganizationMember).filter(
        OrganizationMember.user_id == current_user.id,
        OrganizationMember.organization_id == org_id
    ).first()

    if not membership and not current_user.is_super_admin:
        raise HTTPException(status_code=403, detail="Not authorized")

    created_count = generate_cross_module_tasks(db, org_id, current_user.id)

    return {
        "message": f"Generated {created_count} cross-module action items",
        "created_count": created_count
    }


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
    
    if not membership and not current_user.is_super_admin:
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

    by_entity_type = db.query(
        ActionItem.entity_type, func.count(ActionItem.id)
    ).filter(
        ActionItem.organization_id == org_id,
        ActionItem.status != "COMPLETED",
        ActionItem.entity_type.isnot(None)
    ).group_by(ActionItem.entity_type).all()

    by_action_type = db.query(
        ActionItem.action_type, func.count(ActionItem.id)
    ).filter(
        ActionItem.organization_id == org_id,
        ActionItem.status != "COMPLETED"
    ).group_by(ActionItem.action_type).all()
    
    return {
        "total_pending": total_pending,
        "overdue": overdue,
        "due_this_week": due_this_week,
        "high_priority": high_priority,
        "by_entity_type": {t: c for t, c in by_entity_type if t},
        "by_action_type": {t: c for t, c in by_action_type},
    }
