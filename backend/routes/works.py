import logging
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_
from pydantic import BaseModel
from typing import List, Optional
from ..models import get_db, Work, WorkFolder, WorkTrack, WorkCredit, Song, Creator, OrganizationMember, User, ActionItem, ClientShare
from ..utils.auth import get_current_user

logger = logging.getLogger("cadence")

router = APIRouter(prefix="/api/works", tags=["works"])


class WorkCreate(BaseModel):
    title: str
    work_type: Optional[str] = "TRACK"
    iswc: Optional[str] = None
    alternative_titles: Optional[List[str]] = []
    language: Optional[str] = None
    genre: Optional[str] = None
    notes: Optional[str] = None
    lyrics: Optional[str] = None


class WorkUpdate(BaseModel):
    title: Optional[str] = None
    work_type: Optional[str] = None
    iswc: Optional[str] = None
    alternative_titles: Optional[List[str]] = None
    language: Optional[str] = None
    genre: Optional[str] = None
    notes: Optional[str] = None
    lyrics: Optional[str] = None


class WorkTrackLink(BaseModel):
    song_id: int
    is_primary: Optional[bool] = True


class WorkCreditCreate(BaseModel):
    creator_id: int
    role: str
    share_percentage: Optional[float] = None
    publisher_name: Optional[str] = None


class FolderCreate(BaseModel):
    name: str


class FolderUpdate(BaseModel):
    name: str


class WorkMove(BaseModel):
    folder_id: Optional[int] = None


def verify_org_access(user: User, org_id: int, db: Session):
    membership = db.query(OrganizationMember).filter(
        OrganizationMember.user_id == user.id,
        OrganizationMember.organization_id == org_id
    ).first()
    if not membership and not user.is_super_admin and not getattr(user, "is_cadence_staff", False):
        raise HTTPException(status_code=403, detail="Access denied")
    return membership


@router.get("/org/{org_id}")
def list_works(
    org_id: int,
    search: Optional[str] = None,
    limit: int = Query(default=100, le=500),
    offset: int = 0,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    verify_org_access(current_user, org_id, db)
    query = db.query(Work).filter(Work.organization_id == org_id)

    if search:
        query = query.filter(
            or_(
                Work.title.ilike(f"%{search}%"),
                Work.iswc.ilike(f"%{search}%")
            )
        )

    total = query.count()
    works = query.order_by(Work.title).offset(offset).limit(limit).all()

    folder_ids = set(w.folder_id for w in works if w.folder_id)
    folder_map = {}
    if folder_ids:
        folders = db.query(WorkFolder).filter(WorkFolder.id.in_(folder_ids)).all()
        folder_map = {f.id: f.name for f in folders}

    results = []
    for w in works:
        track_count = db.query(WorkTrack).filter(WorkTrack.work_id == w.id).count()
        credit_count = db.query(WorkCredit).filter(WorkCredit.work_id == w.id).count()
        results.append({
            "id": w.id,
            "title": w.title,
            "work_type": w.work_type or "TRACK",
            "iswc": w.iswc,
            "alternative_titles": w.alternative_titles or [],
            "language": w.language,
            "genre": w.genre,
            "notes": w.notes,
            "folder_id": w.folder_id,
            "folder_name": folder_map.get(w.folder_id) if w.folder_id else None,
            "status": w.status or "PENDING",
            "track_count": track_count,
            "credit_count": credit_count,
            "created_at": w.created_at.isoformat() if w.created_at else None,
            "updated_at": w.updated_at.isoformat() if w.updated_at else None,
        })

    return {"works": results, "total": total}


@router.get("/{work_id}")
def get_work(work_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    work = db.query(Work).filter(Work.id == work_id).first()
    if not work:
        raise HTTPException(status_code=404, detail="Work not found")
    verify_org_access(current_user, work.organization_id, db)

    tracks = []
    for wt in db.query(WorkTrack).filter(WorkTrack.work_id == work_id).all():
        song = db.query(Song).filter(Song.id == wt.song_id).first()
        if song:
            tracks.append({
                "id": wt.id,
                "song_id": song.id,
                "title": song.title,
                "primary_artist": song.primary_artist,
                "isrc": song.isrc,
                "is_primary": wt.is_primary,
            })

    credits = []
    for wc in db.query(WorkCredit).filter(WorkCredit.work_id == work_id).all():
        creator = db.query(Creator).filter(Creator.id == wc.creator_id).first()
        credits.append({
            "id": wc.id,
            "creator_id": wc.creator_id,
            "creator_name": creator.display_name if creator else "Unknown",
            "role": wc.role,
            "share_percentage": wc.share_percentage,
            "publisher_name": wc.publisher_name,
        })

    return {
        "id": work.id,
        "title": work.title,
        "work_type": work.work_type or "TRACK",
        "iswc": work.iswc,
        "alternative_titles": work.alternative_titles or [],
        "language": work.language,
        "genre": work.genre,
        "notes": work.notes,
        "lyrics": work.lyrics,
        "folder_id": work.folder_id,
        "status": work.status or "PENDING",
        "tracks": tracks,
        "credits": credits,
        "created_at": work.created_at.isoformat() if work.created_at else None,
        "updated_at": work.updated_at.isoformat() if work.updated_at else None,
    }


@router.post("/org/{org_id}")
def create_work(org_id: int, data: WorkCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    verify_org_access(current_user, org_id, db)

    work = Work(
        organization_id=org_id,
        title=data.title,
        work_type=data.work_type or "TRACK",
        iswc=data.iswc,
        alternative_titles=data.alternative_titles or [],
        language=data.language,
        genre=data.genre,
        notes=data.notes,
        lyrics=data.lyrics,
        status="PENDING",
    )
    db.add(work)
    db.flush()

    action_item = ActionItem(
        organization_id=org_id,
        work_id=work.id,
        action_type="WORK_PENDING_APPROVAL",
        title=f"Review & approve work: {work.title}",
        description=f"New composition '{work.title}' requires admin approval before it becomes active in the catalog.",
        priority=2,
        is_auto_generated=True,
    )
    db.add(action_item)
    db.commit()
    db.refresh(work)
    return {"id": work.id, "title": work.title, "message": "Work created successfully"}


@router.put("/{work_id}")
def update_work(work_id: int, data: WorkUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    work = db.query(Work).filter(Work.id == work_id).first()
    if not work:
        raise HTTPException(status_code=404, detail="Work not found")
    verify_org_access(current_user, work.organization_id, db)

    for field, value in data.dict(exclude_unset=True).items():
        setattr(work, field, value)

    db.commit()
    db.refresh(work)
    return {"id": work.id, "title": work.title, "message": "Work updated successfully"}


@router.delete("/{work_id}")
def delete_work(work_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    work = db.query(Work).filter(Work.id == work_id).first()
    if not work:
        raise HTTPException(status_code=404, detail="Work not found")
    verify_org_access(current_user, work.organization_id, db)

    db.query(ActionItem).filter(ActionItem.work_id == work_id).delete()
    db.delete(work)
    db.commit()
    return {"message": "Work deleted successfully"}


@router.post("/{work_id}/tracks")
def link_track_to_work(work_id: int, data: WorkTrackLink, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    work = db.query(Work).filter(Work.id == work_id).first()
    if not work:
        raise HTTPException(status_code=404, detail="Work not found")
    verify_org_access(current_user, work.organization_id, db)

    song = db.query(Song).filter(Song.id == data.song_id, Song.organization_id == work.organization_id).first()
    if not song:
        raise HTTPException(status_code=404, detail="Track not found in this organization")

    existing = db.query(WorkTrack).filter(WorkTrack.work_id == work_id, WorkTrack.song_id == data.song_id).first()
    if existing:
        raise HTTPException(status_code=400, detail="Track already linked to this work")

    link = WorkTrack(work_id=work_id, song_id=data.song_id, is_primary=data.is_primary)
    db.add(link)
    db.commit()
    return {"message": "Track linked to work successfully"}


@router.delete("/{work_id}/tracks/{song_id}")
def unlink_track_from_work(work_id: int, song_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    work = db.query(Work).filter(Work.id == work_id).first()
    if not work:
        raise HTTPException(status_code=404, detail="Work not found")
    verify_org_access(current_user, work.organization_id, db)

    link = db.query(WorkTrack).filter(WorkTrack.work_id == work_id, WorkTrack.song_id == song_id).first()
    if not link:
        raise HTTPException(status_code=404, detail="Link not found")

    db.delete(link)
    db.commit()
    return {"message": "Track unlinked from work"}


@router.post("/{work_id}/credits")
def add_work_credit(work_id: int, data: WorkCreditCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    work = db.query(Work).filter(Work.id == work_id).first()
    if not work:
        raise HTTPException(status_code=404, detail="Work not found")
    verify_org_access(current_user, work.organization_id, db)

    creator = db.query(Creator).filter(Creator.id == data.creator_id, Creator.organization_id == work.organization_id).first()
    if not creator:
        raise HTTPException(status_code=404, detail="Creator not found in this organization")

    credit = WorkCredit(
        work_id=work_id,
        creator_id=data.creator_id,
        role=data.role,
        share_percentage=data.share_percentage,
        publisher_name=data.publisher_name,
    )
    db.add(credit)
    db.commit()
    return {"message": "Credit added to work"}


@router.delete("/{work_id}/credits/{credit_id}")
def remove_work_credit(work_id: int, credit_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    work = db.query(Work).filter(Work.id == work_id).first()
    if not work:
        raise HTTPException(status_code=404, detail="Work not found")
    verify_org_access(current_user, work.organization_id, db)

    credit = db.query(WorkCredit).filter(WorkCredit.id == credit_id, WorkCredit.work_id == work_id).first()
    if not credit:
        raise HTTPException(status_code=404, detail="Credit not found")

    db.delete(credit)
    db.commit()
    return {"message": "Credit removed from work"}


@router.get("/org/{org_id}/folders")
def list_folders(org_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    verify_org_access(current_user, org_id, db)
    folders = db.query(WorkFolder).filter(WorkFolder.organization_id == org_id).order_by(WorkFolder.name).all()
    results = []
    for f in folders:
        work_count = db.query(Work).filter(Work.folder_id == f.id).count()
        results.append({
            "id": f.id,
            "name": f.name,
            "parent_folder_id": f.parent_folder_id,
            "work_count": work_count,
            "created_at": f.created_at.isoformat() if f.created_at else None,
        })
    return results


@router.post("/org/{org_id}/folders")
def create_folder(org_id: int, data: FolderCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    verify_org_access(current_user, org_id, db)
    folder = WorkFolder(organization_id=org_id, name=data.name)
    db.add(folder)
    db.commit()
    db.refresh(folder)
    return {"id": folder.id, "name": folder.name, "message": "Folder created successfully"}


@router.put("/folders/{folder_id}")
def rename_folder(folder_id: int, data: FolderUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    folder = db.query(WorkFolder).filter(WorkFolder.id == folder_id).first()
    if not folder:
        raise HTTPException(status_code=404, detail="Folder not found")
    verify_org_access(current_user, folder.organization_id, db)
    folder.name = data.name
    db.commit()
    return {"id": folder.id, "name": folder.name, "message": "Folder renamed successfully"}


@router.delete("/folders/{folder_id}")
def delete_folder(folder_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    folder = db.query(WorkFolder).filter(WorkFolder.id == folder_id).first()
    if not folder:
        raise HTTPException(status_code=404, detail="Folder not found")
    verify_org_access(current_user, folder.organization_id, db)
    db.query(Work).filter(Work.folder_id == folder_id).update({"folder_id": None})
    db.delete(folder)
    db.commit()
    return {"message": "Folder deleted successfully"}


@router.put("/{work_id}/move")
def move_work(work_id: int, data: WorkMove, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    work = db.query(Work).filter(Work.id == work_id).first()
    if not work:
        raise HTTPException(status_code=404, detail="Work not found")
    verify_org_access(current_user, work.organization_id, db)
    if data.folder_id is not None:
        folder = db.query(WorkFolder).filter(WorkFolder.id == data.folder_id).first()
        if not folder:
            raise HTTPException(status_code=404, detail="Folder not found")
    work.folder_id = data.folder_id
    db.commit()
    return {"message": "Work moved successfully"}


def _is_work_admin(db: Session, current_user: User, work: Work) -> bool:
    if getattr(current_user, "is_admin", False) or getattr(current_user, "is_super_admin", False):
        return True

    membership = db.query(OrganizationMember).filter(
        OrganizationMember.user_id == current_user.id,
        OrganizationMember.organization_id == work.organization_id
    ).first()
    if membership and membership.role in ("OWNER", "ADMIN"):
        return True

    user_membership = db.query(OrganizationMember).filter(
        OrganizationMember.user_id == current_user.id
    ).first()
    if user_membership and user_membership.role in ("OWNER", "ADMIN"):
        work_creator_ids = [
            wc.creator_id for wc in
            db.query(WorkCredit).filter(WorkCredit.work_id == work.id).all()
            if wc.creator_id
        ]
        if work_creator_ids:
            shared = db.query(ClientShare).filter(
                ClientShare.creator_id.in_(work_creator_ids),
                ClientShare.recipient_org_id == user_membership.organization_id,
                ClientShare.status == "ACCEPTED"
            ).first()
            if shared:
                return True

    return False


@router.post("/{work_id}/approve")
def approve_work(work_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    work = db.query(Work).filter(Work.id == work_id).first()
    if not work:
        raise HTTPException(status_code=404, detail="Work not found")

    if not _is_work_admin(db, current_user, work):
        raise HTTPException(status_code=403, detail="Only organization admins can approve works")

    if work.status == "APPROVED":
        return {"message": "Work is already approved"}

    work.status = "APPROVED"

    pending_items = db.query(ActionItem).filter(
        ActionItem.work_id == work_id,
        ActionItem.is_auto_generated == True,
        ActionItem.status != "COMPLETED",
    ).all()
    for item in pending_items:
        item.status = "COMPLETED"
        item.completed_at = datetime.utcnow()
        item.completed_by_user_id = current_user.id

    db.commit()
    logger.info(f"Work {work_id} approved by user {current_user.id}")
    return {"message": "Work approved successfully", "id": work.id, "status": "APPROVED"}


@router.post("/{work_id}/reject")
def reject_work(work_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    work = db.query(Work).filter(Work.id == work_id).first()
    if not work:
        raise HTTPException(status_code=404, detail="Work not found")

    if not _is_work_admin(db, current_user, work):
        raise HTTPException(status_code=403, detail="Only organization admins can reject works")

    if work.status == "REJECTED":
        return {"message": "Work is already rejected"}

    work.status = "REJECTED"

    pending_items = db.query(ActionItem).filter(
        ActionItem.work_id == work_id,
        ActionItem.is_auto_generated == True,
        ActionItem.status != "COMPLETED",
    ).all()
    for item in pending_items:
        item.status = "COMPLETED"
        item.completed_at = datetime.utcnow()
        item.completed_by_user_id = current_user.id

    db.commit()
    logger.info(f"Work {work_id} rejected by user {current_user.id}")
    return {"message": "Work rejected", "id": work.id, "status": "REJECTED"}
