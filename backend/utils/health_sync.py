from sqlalchemy.orm import Session
from sqlalchemy import func
from ..models.models import Song, SongChecklistStatus, ChecklistItem, SongDSPLink, SongCredit

FIELD_TO_CHECKLIST_MAP = {
    "isrc": "MD-01",
    "iswc": "MD-02",
    "has_contract_executed": "AD-02",
    "is_invoiced": "AD-03",
    "is_registered_with_pro": "SY-01",
    "is_paid": "PY-01",
    "mlc_registered": "SY-03",
}

NA_CAPABLE_FIELDS = {"is_paid", "is_invoiced",
                     "has_contract_executed",
                     "is_registered_with_pro",
                     "mlc_registered"}

DSP_PLATFORM_TO_CHECKLIST_MAP = {
    "spotify": "DSP-03",
}

# Tolerance for treating credit-level pub_share totals as "100%". Schedule A
# imports and manual edits round to one or two decimals, so insisting on
# exact equality leaves songs stuck at 99.9% / 100.01% and never trips LG-02.
PUB_SHARE_FULL_TOLERANCE = 0.5


def song_has_finalized_credits(db: Session, song_id: int) -> bool:
    """MD-03: at least one SongCredit on the song has a creator attached."""
    return db.query(SongCredit.id).filter(
        SongCredit.song_id == song_id,
        SongCredit.creator_id.isnot(None),
    ).first() is not None


def song_has_full_pub_splits(db: Session, song_id: int) -> bool:
    """LG-02: credit-level publishing shares for the song sum to ~100%.

    Mirrors the credit-driven rollup used by the Rights & Splits tab —
    once contributors collectively account for 100% of the publishing pie,
    the splits are considered confirmed.
    """
    total = db.query(func.coalesce(func.sum(SongCredit.pub_share), 0.0)).filter(
        SongCredit.song_id == song_id,
        SongCredit.pub_share.isnot(None),
    ).scalar() or 0.0
    return abs(float(total) - 100.0) <= PUB_SHARE_FULL_TOLERANCE

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
            set_checklist_status(db, song.id, checklist_item.id, "NOT_STARTED")
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

    # Task #140 — derive the two checklist items that have no UI checkbox
    # from the data the app already owns:
    #   LG-02 "Publishing splits confirmed" — credit-level pub_share == 100%
    #   MD-03 "Credits finalized"           — at least one SongCredit w/ creator
    # Without these, every song in every org is permanently capped at
    # 75/90 = 83.3% health, even when fully filled out.
    if "LG-02" in checklist_items:
        completed = song_has_full_pub_splits(db, song.id)
        set_checklist_status(
            db, song.id, checklist_items["LG-02"].id,
            "COMPLETED" if completed else "NOT_STARTED",
        )
    if "MD-03" in checklist_items:
        completed = song_has_finalized_credits(db, song.id)
        set_checklist_status(
            db, song.id, checklist_items["MD-03"].id,
            "COMPLETED" if completed else "NOT_STARTED",
        )

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
    if not songs:
        return
    song_ids = [s.id for s in songs]
    existing_song_ids = {r[0] for r in db.query(SongChecklistStatus.song_id).filter(
        SongChecklistStatus.song_id.in_(song_ids)
    ).distinct().all()}
    missing = [s for s in songs if s.id not in existing_song_ids]
    if not missing:
        return
    items = db.query(ChecklistItem).all()
    if not items:
        return
    for song in missing:
        for item in items:
            db.add(SongChecklistStatus(
                song_id=song.id,
                checklist_item_id=item.id,
                status="NOT_STARTED"
            ))
        sync_song_to_checklist(db, song)
    db.flush()
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
