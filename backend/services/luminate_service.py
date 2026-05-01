"""Luminate (MRC Data) integration — Task #173 (A+ Phase 6).

Luminate publishes the most authoritative cross-platform stream counts in
the music industry. We model the integration as a class so the rest of
the app can depend on a single ``LuminateService`` interface regardless of
whether the live API is wired up or we're operating from a CSV export.

For now the live ``fetch`` path is a stub (no public API key today); the
``import_csv`` path is real and is the workflow most labels use anyway —
they download a Luminate report, hand it off to ops, and ops uploads it
into Cadence so the audit engine can cross-reference.
"""

from __future__ import annotations

import csv
import io
import json
import logging
import os
from datetime import date, datetime
from typing import Any, Dict, Iterable, List, Optional

from sqlalchemy.orm import Session

from ..models import Song, SongStreamingMetrics

log = logging.getLogger(__name__)

LUMINATE_API_KEY = os.getenv("LUMINATE_API_KEY")
LUMINATE_DATA_SOURCE = "luminate"

# Headers the importer recognises (case-insensitive). We accept a
# handful of common Luminate export variants so ops doesn't have to
# rename columns by hand.
_HEADER_ALIASES = {
    "isrc": {"isrc", "track_isrc"},
    "title": {"title", "track", "track_title", "song"},
    "artist": {"artist", "performer", "primary_artist"},
    "total_streams": {
        "total_streams", "streams", "tea", "on_demand_streams",
        "total_on_demand_streams", "total_audio_on_demand_streams",
    },
    "audio_streams": {"audio_streams", "audio_on_demand_streams"},
    "video_streams": {"video_streams", "video_on_demand_streams"},
    "premium_streams": {"premium_streams", "subscription_streams"},
    "ad_supported_streams": {"ad_supported_streams", "ad_supported"},
    "period_start": {"period_start", "start_date", "week_start"},
    "period_end": {"period_end", "end_date", "week_end"},
}


def _normalise_header(h: str) -> Optional[str]:
    h_low = (h or "").strip().lower().replace(" ", "_").replace("-", "_")
    for canonical, aliases in _HEADER_ALIASES.items():
        if h_low in aliases:
            return canonical
    return None


def _parse_int(v: Any) -> int:
    if v is None or v == "":
        return 0
    try:
        return int(float(str(v).replace(",", "").strip()))
    except (TypeError, ValueError):
        return 0


def _parse_date(v: Any) -> Optional[date]:
    if not v:
        return None
    s = str(v).strip()
    for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%Y/%m/%d", "%d-%m-%Y"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return None


def _get_mock_payload() -> Dict[str, Any]:
    """Load a static mock payload (kept from the legacy stub) for any
    code that still calls the legacy free function."""
    mock_path = os.path.join(
        os.path.dirname(__file__), "../../mock_data/luminate_response.json"
    )
    if os.path.exists(mock_path):
        with open(mock_path) as f:
            return json.load(f)
    return {"streams": 0, "source": "mock", "tracks": []}


class LuminateService:
    """Thin facade over the Luminate data source.

    Methods
    -------
    fetch(isrc) → dict
        Fetch one track's latest stream counts (stubbed unless a live API
        key is wired in).
    sync(db, org_id) → dict
        Refresh Luminate data for every track in the org. Stubbed until
        a live key is available — returns a structured no-op response.
    import_csv(file_or_path, org_id, db) → dict
        Parse a Luminate CSV export and upsert ``SongStreamingMetrics``
        rows tagged ``data_source='luminate'``. Matches by ISRC.
    """

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or LUMINATE_API_KEY

    # --- live API (stubbed) -------------------------------------------

    def fetch(self, isrc: str) -> Dict[str, Any]:
        if not self.api_key:
            return {
                "isrc": isrc,
                "available": False,
                "reason": "no_api_key",
                "mock": _get_mock_payload(),
            }
        # TODO: replace with real Luminate SDK call once available.
        return {
            "isrc": isrc,
            "available": False,
            "reason": "live_api_not_implemented",
        }

    def sync(self, db: Session, org_id: int) -> Dict[str, Any]:
        if not self.api_key:
            return {
                "synced": 0,
                "skipped_reason": "no_api_key",
                "hint": "Use import_csv with a Luminate export instead.",
            }
        # TODO: live sync once a key is provisioned.
        return {"synced": 0, "skipped_reason": "live_api_not_implemented"}

    # --- CSV import (real) --------------------------------------------

    def import_csv(
        self,
        file_or_path: Any,
        org_id: int,
        db: Session,
        *,
        period_date: Optional[date] = None,
    ) -> Dict[str, Any]:
        """Parse a Luminate CSV and upsert one ``SongStreamingMetrics``
        row per (song, period_start, period_end).

        ``file_or_path`` may be a path string or a file-like object
        opened in text or binary mode.
        """
        if hasattr(file_or_path, "read"):
            raw = file_or_path.read()
            if isinstance(raw, bytes):
                raw = raw.decode("utf-8", errors="replace")
            reader = csv.DictReader(io.StringIO(raw))
        else:
            reader = csv.DictReader(open(file_or_path, "r", encoding="utf-8"))

        # Build header → canonical key map
        if reader.fieldnames is None:
            return {"imported": 0, "matched": 0, "unmatched": 0, "errors": ["no_headers"]}
        header_map = {
            h: _normalise_header(h) for h in reader.fieldnames
        }

        # Index songs by ISRC for fast match
        org_songs: Dict[str, Song] = {}
        for s in db.query(Song).filter(Song.organization_id == org_id).all():
            if s.isrc:
                org_songs[s.isrc.strip().upper()] = s

        imported = 0
        matched = 0
        unmatched = 0
        errors: List[str] = []
        now = datetime.utcnow()

        for row in reader:
            try:
                canon: Dict[str, Any] = {}
                for raw_h, val in row.items():
                    key = header_map.get(raw_h)
                    if key:
                        canon[key] = val

                isrc = (canon.get("isrc") or "").strip().upper()
                if not isrc:
                    unmatched += 1
                    continue
                song = org_songs.get(isrc)
                if not song:
                    unmatched += 1
                    continue

                ps = _parse_date(canon.get("period_start"))
                pe = _parse_date(canon.get("period_end"))
                p_date = period_date or pe or ps or date.today()
                total = _parse_int(canon.get("total_streams"))

                # Upsert by (song_id, period_date, data_source)
                existing = (
                    db.query(SongStreamingMetrics)
                    .filter(
                        SongStreamingMetrics.song_id == song.id,
                        SongStreamingMetrics.period_date == p_date,
                        SongStreamingMetrics.data_source == LUMINATE_DATA_SOURCE,
                    )
                    .first()
                )
                row_obj = existing or SongStreamingMetrics(
                    song_id=song.id,
                    organization_id=org_id,
                    period_date=p_date,
                )
                row_obj.luminate_total_streams = total
                row_obj.total_streams = total
                row_obj.audio_streams = _parse_int(canon.get("audio_streams"))
                row_obj.video_streams = _parse_int(canon.get("video_streams"))
                row_obj.premium_streams = _parse_int(canon.get("premium_streams"))
                row_obj.ad_supported_streams = _parse_int(
                    canon.get("ad_supported_streams")
                )
                row_obj.period_start = ps
                row_obj.period_end = pe
                row_obj.last_synced = now
                row_obj.data_source = LUMINATE_DATA_SOURCE
                if not existing:
                    db.add(row_obj)
                imported += 1
                matched += 1
            except Exception as e:
                errors.append(str(e)[:200])

        db.commit()
        return {
            "imported": imported,
            "matched": matched,
            "unmatched": unmatched,
            "errors": errors[:25],
        }


# --- Legacy free-function shim (kept for backwards compatibility) ----------

def get_track_data(track_name: str, artist_name: str) -> Dict[str, Any]:
    """Legacy stub: returns mock payload until the live API is wired up."""
    if not LUMINATE_API_KEY:
        return _get_mock_payload()
    return _get_mock_payload()


def get_mock_data() -> Dict[str, Any]:
    """Legacy alias kept for any imports of the old name."""
    return _get_mock_payload()
