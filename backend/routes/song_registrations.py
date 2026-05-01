"""Per-PRO / per-registry song registration endpoints — Task #173.

Exposes a structured per-registry registration matrix on top of the
new ``song_registrations`` table, with a one-time lazy backfill from
the legacy ``Song.is_registered_with_pro`` / ``soundexchange_registered`` /
``mlc_registered`` columns the first time a song is read.
"""

from datetime import date, datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..models import (
    RegistrationStatus,
    RegistryType,
    Song,
    SongRegistration,
    User,
    get_db,
)
from ..utils.auth import get_current_user
from .audit_log import verify_org_access

router = APIRouter(prefix="/api/songs", tags=["Song Registrations"])

# Default registries every release-eligible song should care about.
DEFAULT_REGISTRIES: List[str] = [
    "BMI", "ASCAP", "MLC", "SOUNDEXCHANGE", "HFA",
]


def _serialize(r: SongRegistration) -> dict:
    return {
        "id": r.id,
        "song_id": r.song_id,
        "registry_type": r.registry_type,
        "registration_status": r.registration_status,
        "registration_id": r.registration_id,
        "registered_date": r.registered_date.isoformat() if r.registered_date else None,
        "registered_by_user_id": r.registered_by_user_id,
        "notes": r.notes,
        "updated_at": r.updated_at.isoformat() if r.updated_at else None,
    }


def _backfill_from_legacy_flags(db: Session, song: Song) -> None:
    """If a song has no SongRegistration rows yet, materialise one row
    per default registry, seeding ``REGISTERED`` from the legacy boolean/
    string flags on Song. Idempotent: a no-op if rows already exist."""
    existing_count = (
        db.query(SongRegistration)
        .filter(SongRegistration.song_id == song.id)
        .count()
    )
    if existing_count > 0:
        return

    def _is_truthy(val) -> bool:
        if isinstance(val, bool):
            return val
        if val is None:
            return False
        s = str(val).strip().lower()
        return s in ("true", "yes", "y", "1", "registered", "complete")

    legacy_pro = _is_truthy(getattr(song, "is_registered_with_pro", False))
    legacy_sx = _is_truthy(getattr(song, "soundexchange_registered", None))
    legacy_mlc = _is_truthy(getattr(song, "mlc_registered", None))

    seed_status = {
        "BMI": "REGISTERED" if legacy_pro else "NOT_STARTED",
        "ASCAP": "NOT_STARTED",  # we can't tell which PRO from one boolean
        "MLC": "REGISTERED" if legacy_mlc else "NOT_STARTED",
        "SOUNDEXCHANGE": "REGISTERED" if legacy_sx else "NOT_STARTED",
        "HFA": "NOT_STARTED",
    }
    for reg in DEFAULT_REGISTRIES:
        db.add(SongRegistration(
            song_id=song.id,
            organization_id=song.organization_id,
            registry_type=reg,
            registration_status=seed_status.get(reg, "NOT_STARTED"),
        ))
    db.commit()


def compute_registration_completeness(
    db: Session, song: Song, applicable_registries: Optional[List[str]] = None
) -> float:
    """Return the fraction of applicable registries marked REGISTERED
    for a song. Used by the scoring engine."""
    _backfill_from_legacy_flags(db, song)
    rows = (
        db.query(SongRegistration)
        .filter(SongRegistration.song_id == song.id)
        .all()
    )
    if not rows:
        return 0.0
    apps = applicable_registries or DEFAULT_REGISTRIES
    applicable = [r for r in rows if r.registry_type in apps
                  and r.registration_status != "NOT_APPLICABLE"]
    if not applicable:
        return 0.0
    registered = [r for r in applicable
                  if r.registration_status == "REGISTERED"]
    return round(len(registered) / len(applicable), 4)


@router.get("/{song_id}/registrations")
def list_song_registrations(
    song_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    song = db.query(Song).filter(Song.id == song_id).first()
    if not song:
        raise HTTPException(status_code=404, detail="Song not found")
    verify_org_access(current_user, song.organization_id, db)
    _backfill_from_legacy_flags(db, song)
    rows = (
        db.query(SongRegistration)
        .filter(SongRegistration.song_id == song_id)
        .order_by(SongRegistration.registry_type)
        .all()
    )
    return {
        "song_id": song.id,
        "completeness": compute_registration_completeness(db, song),
        "registrations": [_serialize(r) for r in rows],
    }


class RegistrationUpdate(BaseModel):
    registration_status: Optional[str] = None
    registration_id: Optional[str] = None
    registered_date: Optional[date] = None
    notes: Optional[str] = None


@router.patch("/{song_id}/registrations/{registry_type}")
def upsert_song_registration(
    song_id: int,
    registry_type: str,
    body: RegistrationUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    song = db.query(Song).filter(Song.id == song_id).first()
    if not song:
        raise HTTPException(status_code=404, detail="Song not found")
    verify_org_access(current_user, song.organization_id, db)

    valid_types = {e.value for e in RegistryType}
    if registry_type not in valid_types:
        raise HTTPException(status_code=400, detail=f"Unknown registry_type {registry_type}")
    if body.registration_status:
        valid_statuses = {e.value for e in RegistrationStatus}
        if body.registration_status not in valid_statuses:
            raise HTTPException(
                status_code=400,
                detail=f"Unknown status {body.registration_status}",
            )

    row = (
        db.query(SongRegistration)
        .filter(
            SongRegistration.song_id == song_id,
            SongRegistration.registry_type == registry_type,
        )
        .first()
    )
    if not row:
        row = SongRegistration(
            song_id=song_id,
            organization_id=song.organization_id,
            registry_type=registry_type,
            registration_status="NOT_STARTED",
        )
        db.add(row)

    if body.registration_status is not None:
        row.registration_status = body.registration_status
        if body.registration_status == "REGISTERED" and not row.registered_date:
            row.registered_date = body.registered_date or date.today()
            row.registered_by_user_id = current_user.id
    if body.registration_id is not None:
        row.registration_id = body.registration_id
    if body.registered_date is not None:
        row.registered_date = body.registered_date
    if body.notes is not None:
        row.notes = body.notes
    row.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(row)
    return _serialize(row)
