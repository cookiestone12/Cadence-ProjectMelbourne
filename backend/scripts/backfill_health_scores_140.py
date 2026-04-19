"""
Backfill script for Task #140.

Re-derives `status_health_score` for every song in every organization by
re-running `sync_song_to_checklist`. This picks up the new LG-02 /
MD-03 evaluations introduced in Task #140 (publishing splits sum to
100% and credits finalized) so existing songs don't have to be touched
manually before their scores reflect reality.

Usage:
    python -m backend.scripts.backfill_health_scores_140 [--dry-run] [--org-id N]
"""
import argparse
import sys

from backend.models.database import SessionLocal
from backend.models import Song, Organization, SongChecklistStatus, ChecklistItem
from backend.utils.health_sync import sync_song_to_checklist


def backfill(dry_run: bool = False, only_org_id: int = None) -> dict:
    db = SessionLocal()
    stats = {
        "orgs_scanned": 0,
        "songs_scanned": 0,
        "songs_updated": 0,
        "scores_unchanged": 0,
        "avg_score_before": 0.0,
        "avg_score_after": 0.0,
    }
    try:
        org_q = db.query(Organization)
        if only_org_id:
            org_q = org_q.filter(Organization.id == only_org_id)
        orgs = org_q.all()

        sum_before = 0.0
        sum_after = 0.0
        scored_count = 0

        for org in orgs:
            stats["orgs_scanned"] += 1

            songs = db.query(Song).filter(Song.organization_id == org.id).all()

            # Make sure every song has the full checklist seeded; otherwise
            # sync_song_to_checklist would silently no-op on freshly imported
            # songs that never got a SongChecklistStatus row.
            song_ids = [s.id for s in songs]
            if song_ids:
                existing = {
                    r[0] for r in db.query(SongChecklistStatus.song_id)
                    .filter(SongChecklistStatus.song_id.in_(song_ids))
                    .distinct().all()
                }
                missing = [s for s in songs if s.id not in existing]
                if missing:
                    items = db.query(ChecklistItem).all()
                    if items:
                        for s in missing:
                            for item in items:
                                db.add(SongChecklistStatus(
                                    song_id=s.id,
                                    checklist_item_id=item.id,
                                    status="NOT_STARTED",
                                ))
                        db.flush()

            for song in songs:
                stats["songs_scanned"] += 1
                before = float(song.status_health_score or 0.0)
                sync_song_to_checklist(db, song)
                after = float(song.status_health_score or 0.0)
                sum_before += before
                sum_after += after
                scored_count += 1
                if abs(after - before) > 0.01:
                    stats["songs_updated"] += 1
                else:
                    stats["scores_unchanged"] += 1

            if not dry_run:
                db.commit()
            else:
                db.rollback()

        if scored_count:
            stats["avg_score_before"] = round(sum_before / scored_count, 2)
            stats["avg_score_after"] = round(sum_after / scored_count, 2)
    finally:
        db.close()
    return stats


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--org-id", type=int, default=None)
    args = parser.parse_args()
    stats = backfill(dry_run=args.dry_run, only_org_id=args.org_id)
    print("Health score backfill (Task #140):")
    for k, v in stats.items():
        print(f"  {k}: {v}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
