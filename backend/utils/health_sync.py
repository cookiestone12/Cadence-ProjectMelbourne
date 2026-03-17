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
    "soundexchange_registered": "SY-02",
    "mlc_registered": "SY-03",
}

NA_CAPABLE_FIELDS = {"is_paid", "is_invoiced", "is_registered_with_dsp",
                     "has_contract_sent", "has_contract_executed",
                     "is_registered_with_pro", "soundexchange_registered",
                     "mlc_registered"}

DSP_PLATFORM_TO_CHECKLIST_MAP = {
    "spotify": "DSP-03",
    "apple_music": "DSP-02",
}

def get_checklist_item_by_code(db: Session, code: str) -> ChecklistItem:
    return db.query(ChecklistItem).filter(ChecklistItem.code == code).first()

def set_checklist_status(db: Session, song_id: int, checklist_item_id: int, status_value: str):
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
    all_items = db.query(ChecklistItem).all()
    total_weight = sum(item.weight for item in all_items) or 1
    
    acknowledged_weight = db.query(func.sum(ChecklistItem.weight)).join(
        SongChecklistStatus,
        ChecklistItem.id == SongChecklistStatus.checklist_item_id
    ).filter(
        SongChecklistStatus.song_id == song.id,
        SongChecklistStatus.status.in_(["COMPLETED", "NOT_APPLICABLE"])
    ).scalar() or 0
    
    health_score = (acknowledged_weight / total_weight) * 100
    song.status_health_score = round(min(health_score, 100.0), 2)

def sync_song_to_checklist(db: Session, song: Song):
    checklist_items = {item.code: item for item in db.query(ChecklistItem).all()}
    
    for field, code in FIELD_TO_CHECKLIST_MAP.items():
        if code not in checklist_items:
            continue
            
        checklist_item = checklist_items[code]
        value = getattr(song, field, None)

        if value is None and field in NA_CAPABLE_FIELDS:
            set_checklist_status(db, song.id, checklist_item.id, "NOT_APPLICABLE")
            continue

        if isinstance(value, bool):
            set_checklist_status(db, song.id, checklist_item.id, "COMPLETED" if value else "NOT_STARTED")
            continue

        str_val = str(value).strip() if value else ""
        upper_val = str_val.upper()

        if upper_val in ("N/A", "NA", "NOT_APPLICABLE"):
            set_checklist_status(db, song.id, checklist_item.id, "NOT_APPLICABLE")
        elif field in ("isrc", "iswc"):
            completed = bool(value and str_val)
            set_checklist_status(db, song.id, checklist_item.id, "COMPLETED" if completed else "NOT_STARTED")
        elif upper_val in ("YES", "TRUE", "1"):
            set_checklist_status(db, song.id, checklist_item.id, "COMPLETED")
        elif str_val and upper_val not in ("NO", "FALSE", "0", ""):
            try:
                float(str_val)
                set_checklist_status(db, song.id, checklist_item.id, "COMPLETED")
            except ValueError:
                set_checklist_status(db, song.id, checklist_item.id, "NOT_STARTED")
        else:
            set_checklist_status(db, song.id, checklist_item.id, "NOT_STARTED")
    
    dsp_links = db.query(SongDSPLink).filter(SongDSPLink.song_id == song.id).all()
    platforms_linked = {link.platform.lower() for link in dsp_links}
    
    for platform, code in DSP_PLATFORM_TO_CHECKLIST_MAP.items():
        if code not in checklist_items:
            continue
        checklist_item = checklist_items[code]
        completed = platform in platforms_linked
        set_checklist_status(db, song.id, checklist_item.id, "COMPLETED" if completed else "NOT_STARTED")
    
    recalculate_health_score(db, song)

def ensure_song_health(db: Session, song: Song):
    if song.status_health_score and song.status_health_score > 0:
        return
    has_status = db.query(SongChecklistStatus).filter(
        SongChecklistStatus.song_id == song.id
    ).first()
    if not has_status:
        items = db.query(ChecklistItem).all()
        if not items:
            return
        for item in items:
            db.add(SongChecklistStatus(
                song_id=song.id,
                checklist_item_id=item.id,
                status="NOT_STARTED"
            ))
        db.flush()
    sync_song_to_checklist(db, song)


def ensure_songs_health(db: Session, songs: list):
    stale = [s for s in songs if not s.status_health_score or s.status_health_score == 0]
    if not stale:
        return
    stale_ids = [s.id for s in stale]
    existing_song_ids = {r[0] for r in db.query(SongChecklistStatus.song_id).filter(
        SongChecklistStatus.song_id.in_(stale_ids)
    ).distinct().all()}
    items = db.query(ChecklistItem).all()
    if not items:
        return
    for song in stale:
        if song.id not in existing_song_ids:
            for item in items:
                db.add(SongChecklistStatus(
                    song_id=song.id,
                    checklist_item_id=item.id,
                    status="NOT_STARTED"
                ))
            db.flush()
        sync_song_to_checklist(db, song)
    db.commit()


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
