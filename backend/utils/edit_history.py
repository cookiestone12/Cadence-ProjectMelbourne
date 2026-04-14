import logging
from sqlalchemy.orm import Session

logger = logging.getLogger("cadence")


def record_edit(
    db: Session,
    song_id: int,
    organization_id: int,
    user_id: int,
    field_name: str,
    old_value,
    new_value,
    change_type: str = "update",
    notes: str = None,
):
    from ..models.models import SongEditHistory
    from datetime import date, datetime
    try:
        def serialize(v):
            if v is None:
                return None
            if isinstance(v, (int, float, bool, str)):
                return v
            if isinstance(v, (dict, list)):
                return v
            if isinstance(v, (date, datetime)):
                return v.isoformat()
            return str(v)

        entry = SongEditHistory(
            song_id=song_id,
            organization_id=organization_id,
            user_id=user_id,
            field_name=field_name,
            old_value=serialize(old_value),
            new_value=serialize(new_value),
            change_type=change_type,
            notes=notes,
        )
        db.add(entry)
    except Exception as e:
        logger.error(f"Failed to record edit history: {e}")


def record_song_create(db: Session, song, user_id: int, notes: str = None):
    record_edit(
        db, song.id, song.organization_id, user_id,
        "song", None, song.title,
        change_type="create", notes=notes,
    )


def record_song_update(db: Session, song, user_id: int, field_name: str, old_value, new_value, notes: str = None):
    if old_value == new_value:
        return
    record_edit(
        db, song.id, song.organization_id, user_id,
        field_name, old_value, new_value,
        change_type="update", notes=notes,
    )


def record_contributor_add(db: Session, song_id: int, org_id: int, user_id: int, creator_name: str, role: str = None, notes: str = None):
    record_edit(
        db, song_id, org_id, user_id,
        "contributor", None, {"name": creator_name, "role": role},
        change_type="add_contributor", notes=notes,
    )


def record_contributor_remove(db: Session, song_id: int, org_id: int, user_id: int, creator_name: str, role: str = None, notes: str = None):
    record_edit(
        db, song_id, org_id, user_id,
        "contributor", {"name": creator_name, "role": role}, None,
        change_type="remove_contributor", notes=notes,
    )


def record_contributor_edit(db: Session, song_id: int, org_id: int, user_id: int, creator_name: str, field: str, old_val, new_val, notes: str = None):
    record_edit(
        db, song_id, org_id, user_id,
        f"contributor.{field}", {"name": creator_name, "value": old_val}, {"name": creator_name, "value": new_val},
        change_type="update", notes=notes,
    )


def record_split_change(db: Session, song_id: int, org_id: int, user_id: int, holder_name: str, rights_type: str, old_pct, new_pct, notes: str = None):
    record_edit(
        db, song_id, org_id, user_id,
        f"split.{rights_type.lower()}",
        {"holder": holder_name, "percentage": old_pct},
        {"holder": holder_name, "percentage": new_pct},
        change_type="split_change", notes=notes,
    )
