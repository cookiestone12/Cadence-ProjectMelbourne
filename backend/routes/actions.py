from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func, case, desc, asc
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime, timedelta
from ..models import get_db, ActionItem, Song, Creator, OrganizationMember, User, Work, Release, Contract, Placement
from ..utils.auth import get_current_user

router = APIRouter(prefix="/api/actions", tags=["Action Items"])

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


def _build_lookup(db, model, ids, name_attr):
    if not ids:
        return {}
    items = db.query(model).filter(model.id.in_(ids)).all()
    return {item.id: getattr(item, name_attr, None) for item in items}


def enrich_actions_batch(actions: list, db: Session, now: datetime) -> list:
    creator_ids = {a.creator_id for a in actions if a.creator_id}
    song_ids = {a.song_id for a in actions if a.song_id}
    work_ids = {a.work_id for a in actions if a.work_id}
    release_ids = {a.release_id for a in actions if a.release_id}
    contract_ids = {a.contract_id for a in actions if a.contract_id}
    placement_ids = {a.placement_id for a in actions if a.placement_id}
    user_ids = {a.assigned_to_user_id for a in actions if a.assigned_to_user_id}

    creators = _build_lookup(db, Creator, creator_ids, 'display_name')
    songs = _build_lookup(db, Song, song_ids, 'title')
    works = _build_lookup(db, Work, work_ids, 'title')
    releases = _build_lookup(db, Release, release_ids, 'title')
    contracts = _build_lookup(db, Contract, contract_ids, 'title')
    placements = _build_lookup(db, Placement, placement_ids, 'title')
    users = _build_lookup(db, User, user_ids, 'username')

    results = []
    for action in actions:
        days_until = None
        is_overdue = False
        if action.deadline:
            delta = (action.deadline - now).days
            days_until = delta
            is_overdue = delta < 0 and action.status != "COMPLETED"

        results.append({
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
            "creator_name": creators.get(action.creator_id),
            "song_title": songs.get(action.song_id),
            "work_title": works.get(action.work_id),
            "release_title": releases.get(action.release_id),
            "contract_title": contracts.get(action.contract_id),
            "placement_title": placements.get(action.placement_id),
            "assigned_to_name": users.get(action.assigned_to_user_id),
            "days_until_deadline": days_until,
            "is_overdue": is_overdue,
            "is_auto_generated": getattr(action, 'is_auto_generated', False),
        })
    return results


def enrich_action(action: ActionItem, db: Session, now: datetime) -> dict:
    return enrich_actions_batch([action], db, now)[0] if action else {}


@router.get("/org/{org_id}", summary="List action items in an org", description="Returns the org's action item queue with optional status / priority / due-date filters.")
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
    return enrich_actions_batch(actions, db, now)


@router.get("/creator/{creator_id}", summary="List action items for a creator", description="Returns every action item attached to a specific creator.")
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
    return enrich_actions_batch(actions, db, now)


@router.post("/org/{org_id}", summary="Create an action item", description="Manually creates an action item (most are auto-generated by the gap engine).")
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


@router.put("/{action_id}", summary="Update an action item", description="Patches title, description, due date, priority, or assigned user.")
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


@router.post("/{action_id}/complete", summary="Mark an action item complete", description="Closes an action item and stamps the completion time + user.")
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


@router.post("/generate-org/{org_id}", summary="Regenerate action items for an org", description="Re-runs the gap-detection engine across the entire organization. Idempotent.")
def generate_org_actions(
    org_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    import logging
    logger = logging.getLogger("cadence")
    from ..utils.catalog_gaps import generate_actions_from_gaps
    
    membership = db.query(OrganizationMember).filter(
        OrganizationMember.user_id == current_user.id,
        OrganizationMember.organization_id == org_id
    ).first()
    
    if not membership and not current_user.is_super_admin:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    try:
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
    except Exception as e:
        logger.error(f"generate-org/{org_id} failed: {type(e).__name__}: {e}", exc_info=True)
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to generate actions: {str(e)}")


@router.post("/generate-cross-module/{org_id}")
def generate_cross_module_actions(
    org_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    import logging
    logger = logging.getLogger("cadence")
    from ..utils.cross_module_tasks import generate_cross_module_tasks

    membership = db.query(OrganizationMember).filter(
        OrganizationMember.user_id == current_user.id,
        OrganizationMember.organization_id == org_id
    ).first()

    if not membership and not current_user.is_super_admin:
        raise HTTPException(status_code=403, detail="Not authorized")

    try:
        created_count = generate_cross_module_tasks(db, org_id, current_user.id)

        return {
            "message": f"Generated {created_count} cross-module action items",
            "created_count": created_count
        }
    except Exception as e:
        logger.error(f"generate-cross-module/{org_id} failed: {type(e).__name__}: {e}", exc_info=True)
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to scan modules: {str(e)}")


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
