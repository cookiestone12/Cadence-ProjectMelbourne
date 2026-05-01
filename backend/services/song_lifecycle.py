"""Lazy song lifecycle helpers.

The catalog should "manage itself": a song whose ``release_date`` has already
passed should automatically appear as Released the next time anyone reads the
catalog, without requiring a cron job, a manual click, or a background worker.
This module implements that lazy auto-release behaviour and is invoked at the
top of every catalog/song listing endpoint.

Related models live in ``backend/models/catalog.py``. The relevant fields on
``Song`` are:

* ``release_date`` — the user-declared release date (may be in the future).
* ``is_released`` — boolean flag exposed throughout the API and UI.
* ``release_status`` — string flag used by the Released/Unreleased filters
  (values: ``"released"`` / ``"unreleased"``).
"""

from __future__ import annotations

from datetime import date
import logging
from typing import Optional

from sqlalchemy import and_
from sqlalchemy.orm import Session

from ..models import Song

logger = logging.getLogger("cadence")


def auto_release_songs(
    db: Session,
    organization_id: Optional[int] = None,
    today: Optional[date] = None,
) -> int:
    """Flip songs whose release_date has passed to Released.

    Selects every ``Song`` in the requested scope where
    ``release_date <= today AND is_released = False`` and updates both
    ``is_released`` and ``release_status`` in one bulk statement.
    A song with ``release_date = tomorrow`` is left untouched.
    A song with ``release_date IS NULL`` is left untouched.

    Args:
        db: Active SQLAlchemy session. The function commits its own work so
            the flip is durable across the request boundary — the calling
            GET handler is read-only and would otherwise leave the session
            with no commit, rolling the update back on close.
        organization_id: When provided, scope the flip to one org (this is the
            normal call from per-org listing endpoints and uses the
            ``ix_songs_organization_id`` index). When ``None``, the function
            operates across every org — only used by tests and admin scripts.
        today: Override for testing; defaults to ``date.today()``.

    Returns:
        Number of songs updated. Zero on the steady-state hot path.
    """
    target_date = today or date.today()

    query = db.query(Song).filter(
        and_(
            Song.release_date.isnot(None),
            Song.release_date <= target_date,
            Song.is_released.is_(False),
        )
    )
    if organization_id is not None:
        query = query.filter(Song.organization_id == organization_id)

    updated = query.update(
        {
            Song.is_released: True,
            Song.release_status: "released",
        },
        synchronize_session=False,
    )

    if updated:
        logger.info(
            "auto_release_songs flipped %s song(s) to released "
            "(organization_id=%s, today=%s)",
            updated,
            organization_id,
            target_date.isoformat(),
        )
        # Commit immediately so the flip is durable. The GET handlers that
        # call this helper never commit themselves, and SQLAlchemy will roll
        # the update back when the request session closes if we leave the
        # transaction open. We swallow commit-time errors and rollback so a
        # transient failure here can never break the underlying read.
        try:
            db.commit()
        except Exception:
            logger.exception("auto_release_songs commit failed; rolling back")
            db.rollback()
            return 0

    return int(updated)
