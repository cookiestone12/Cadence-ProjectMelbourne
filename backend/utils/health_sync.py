from sqlalchemy.orm import Session
from sqlalchemy import func
from ..models.models import Song, SongChecklistStatus, ChecklistItem, SongDSPLink

FIELD_TO_CHECKLIST_MAP = {
    "isrc": "MD-01",
    "iswc": "MD-02",
    "has_contract_sent": "AD-01",
    "has_contract_executed": "AD-02",
    "is_invoiced": "AD-03",
    "is_registered_with_pro": "SY-01",
    "is_registered_with_dsp": "DSP-01",
    "is_paid": "PY-01",
}

DSP_PLATFORM_TO_CHECKLIST_MAP = {
    "spotify": "DSP-03",
    "apple_music": "DSP-02",
}

def get_checklist_item_by_code(db: Session, code: str) -> ChecklistItem:
    return db.query(ChecklistItem).filter(ChecklistItem.code == code).first()

def set_checklist_status(db: Session, song_id: int, checklist_item_id: int, completed: bool):
    status_value = "COMPLETED" if completed else "NOT_STARTED"
    
    existing = db.query(SongChecklistStatus).filter(
        SongChecklistStatus.song_id == song_id,
        SongChecklistStatus.checklist_item_id == checklist_item_id
    ).first()
    
    if existing:
        existing.status = status_value
    else:
        new_status = SongChecklistStatus(
            song_id=song_id,
            checklist_item_id=checklist_item_id,
            status=status_value
        )
        db.add(new_status)

def recalculate_health_score(db: Session, song: Song):
    total_weight = db.query(func.sum(ChecklistItem.weight)).scalar() or 1
    
    completed_weight = db.query(func.sum(ChecklistItem.weight)).join(
        SongChecklistStatus,
        ChecklistItem.id == SongChecklistStatus.checklist_item_id
    ).filter(
        SongChecklistStatus.song_id == song.id,
        SongChecklistStatus.status == "COMPLETED"
    ).scalar() or 0
    
    health_score = (completed_weight / total_weight) * 100
    song.status_health_score = round(health_score, 2)

def sync_song_to_checklist(db: Session, song: Song):
    checklist_items = {item.code: item for item in db.query(ChecklistItem).all()}
    
    for field, code in FIELD_TO_CHECKLIST_MAP.items():
        if code not in checklist_items:
            continue
            
        checklist_item = checklist_items[code]
        value = getattr(song, field, None)
        
        if field in ("isrc", "iswc"):
            completed = bool(value and str(value).strip())
        else:
            completed = bool(value)
        
        set_checklist_status(db, song.id, checklist_item.id, completed)
    
    dsp_links = db.query(SongDSPLink).filter(SongDSPLink.song_id == song.id).all()
    platforms_linked = {link.platform.lower() for link in dsp_links}
    
    for platform, code in DSP_PLATFORM_TO_CHECKLIST_MAP.items():
        if code not in checklist_items:
            continue
        checklist_item = checklist_items[code]
        completed = platform in platforms_linked
        set_checklist_status(db, song.id, checklist_item.id, completed)
    
    recalculate_health_score(db, song)

def sync_organization_songs(db: Session, organization_id: int):
    songs = db.query(Song).filter(Song.organization_id == organization_id).all()
    synced_count = 0
    
    for song in songs:
        sync_song_to_checklist(db, song)
        synced_count += 1
    
    db.commit()
    return synced_count

def sync_all_songs(db: Session):
    songs = db.query(Song).all()
    synced_count = 0
    
    for song in songs:
        sync_song_to_checklist(db, song)
        synced_count += 1
    
    db.commit()
    return synced_count
