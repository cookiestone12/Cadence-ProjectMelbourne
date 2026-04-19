"""
Backfill script for Task #120.

Finds songs that have publishing_percentage or master_percentage set but
no corresponding RightsSplit rows materialized through the SPLIT_SHEET
contract. For each such song's existing SongCredit(s), it calls
`sync_credit_to_splits` so the splits become first-class data — surviving
the contract-rollup mechanism that would otherwise zero out song-level
fields.

Usage:
    python -m backend.scripts.backfill_schedule_a_splits_120 [--dry-run] [--org-id N]

By default, runs against all organizations.
"""
import argparse
import sys

from backend.models.database import SessionLocal
from backend.models import (
    Song,
    SongCredit,
    Contract,
    ContractAsset,
    RightsSplit,
    Organization,
    OrganizationMember,
)
from backend.routes.contracts_mgmt import sync_credit_to_splits


def _pick_acting_user_id(db, org_id: int):
    member = (
        db.query(OrganizationMember)
        .filter(
            OrganizationMember.organization_id == org_id,
            OrganizationMember.role.in_(("OWNER", "ADMIN")),
        )
        .order_by(OrganizationMember.id.asc())
        .first()
    )
    if not member:
        member = (
            db.query(OrganizationMember)
            .filter(OrganizationMember.organization_id == org_id)
            .order_by(OrganizationMember.id.asc())
            .first()
        )
    return member.user_id if member else None


def _song_has_split_sheet_splits(db, song_id: int) -> bool:
    """True only if the song already has SPLIT_SHEET-backed RightsSplit rows.

    We intentionally ignore RightsSplit rows from other contract types
    (e.g. PUBLISHING_DEAL) because Task #120 is specifically about making
    Schedule-A imports materialize their own SPLIT_SHEET contract.
    """
    return (
        db.query(RightsSplit.id)
        .join(ContractAsset, ContractAsset.id == RightsSplit.contract_asset_id)
        .join(Contract, Contract.id == ContractAsset.contract_id)
        .filter(
            ContractAsset.asset_type == "SONG",
            ContractAsset.asset_id == song_id,
            Contract.contract_type == "SPLIT_SHEET",
        )
        .first()
        is not None
    )


def _song_has_any_other_contract(db, song_id: int) -> bool:
    """True if the song already participates in ANY non-SPLIT_SHEET contract.

    We refuse to touch such songs because their splits should be authored
    through that other contract (publishing deal, admin deal, etc.), not
    inferred from the bare song-level percentages.
    """
    return (
        db.query(ContractAsset.id)
        .join(Contract, Contract.id == ContractAsset.contract_id)
        .filter(
            ContractAsset.asset_type == "SONG",
            ContractAsset.asset_id == song_id,
            Contract.contract_type != "SPLIT_SHEET",
        )
        .first()
        is not None
    )


def backfill(dry_run: bool = False, only_org_id: int = None) -> dict:
    db = SessionLocal()
    stats = {
        "orgs_scanned": 0,
        "songs_scanned": 0,
        "songs_backfilled": 0,
        "credits_synced": 0,
        "skipped_no_user": 0,
        "skipped_other_contract": 0,
        "skipped_multi_credit": 0,
        "skipped_no_credit": 0,
    }
    try:
        org_q = db.query(Organization)
        if only_org_id:
            org_q = org_q.filter(Organization.id == only_org_id)
        orgs = org_q.all()

        for org in orgs:
            stats["orgs_scanned"] += 1
            user_id = _pick_acting_user_id(db, org.id)
            if user_id is None:
                stats["skipped_no_user"] += 1
                continue

            songs = (
                db.query(Song)
                .filter(
                    Song.organization_id == org.id,
                    (Song.publishing_percentage.isnot(None))
                    | (Song.master_percentage.isnot(None)),
                )
                .all()
            )

            for song in songs:
                stats["songs_scanned"] += 1
                if _song_has_split_sheet_splits(db, song.id):
                    continue
                if _song_has_any_other_contract(db, song.id):
                    stats["skipped_other_contract"] += 1
                    continue

                credits = (
                    db.query(SongCredit)
                    .filter(SongCredit.song_id == song.id, SongCredit.creator_id.isnot(None))
                    .all()
                )
                if not credits:
                    stats["skipped_no_credit"] += 1
                    continue

                # Multi-credit songs are unsafe to backfill from song-level
                # percentages — applying the same Pub/Master % to every
                # credit would over-allocate. These need manual review.
                distinct_creators = {c.creator_id for c in credits}
                if len(distinct_creators) > 1:
                    stats["skipped_multi_credit"] += 1
                    continue

                credit = credits[0]
                pub_share = credit.pub_share if credit.pub_share is not None else song.publishing_percentage
                master_share = credit.master_share if credit.master_share is not None else song.master_percentage
                if pub_share is None and master_share is None:
                    continue
                if dry_run:
                    stats["credits_synced"] += 1
                    stats["songs_backfilled"] += 1
                    continue
                sync_credit_to_splits(
                    db, song, credit.creator_id, pub_share, master_share, credit.role or "Producer", user_id
                )
                if credit.pub_share is None and pub_share is not None:
                    credit.pub_share = pub_share
                if credit.master_share is None and master_share is not None:
                    credit.master_share = master_share
                stats["credits_synced"] += 1
                stats["songs_backfilled"] += 1

            if not dry_run:
                db.commit()
    finally:
        db.close()
    return stats


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--org-id", type=int, default=None)
    args = parser.parse_args()
    stats = backfill(dry_run=args.dry_run, only_org_id=args.org_id)
    print("Schedule A splits backfill (Task #120):")
    for k, v in stats.items():
        print(f"  {k}: {v}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
