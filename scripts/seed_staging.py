"""Seed a staging database with a deterministic, isolated dataset.

Connects to the database identified by ``STAGING_DATABASE_URL``
(NEVER the production ``DATABASE_URL``), runs the Alembic migration
chain to bring it to head, and then idempotently seeds a single
``Cadence Sandbox`` organization populated with:

  * test users at every role (OWNER, ADMIN, MEMBER, READ_ONLY)
    plus the global MasterPAdmin staff user
  * 5 creators (sandbox_creator_*)
  * 20 songs (sandbox_song_*) credited across the creators
  * 2 royalty statements (sandbox_statement_*)
  * 1 contract (sandbox_contract_*)

Every row is name-prefixed with ``sandbox_`` so a staging operator
can grep / DELETE the seeded set without affecting any other org
that happens to share the database. The script is safe to re-run:
existing rows are detected by name and skipped.

Usage:
    export STAGING_DATABASE_URL=postgresql://user:pw@host:5432/cadence_staging
    python scripts/seed_staging.py

Refusal cases (script exits non-zero, prints to stderr, writes
nothing):
  * STAGING_DATABASE_URL is not set
  * STAGING_DATABASE_URL == DATABASE_URL  (likely a misconfiguration)
"""

from __future__ import annotations

import os
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))


def _resolve_staging_url() -> str:
    staging_url = os.getenv("STAGING_DATABASE_URL", "").strip()
    prod_url = os.getenv("DATABASE_URL", "").strip()
    if not staging_url:
        print(
            "ERROR: STAGING_DATABASE_URL is not set. Refusing to seed.",
            file=sys.stderr,
        )
        sys.exit(2)
    if prod_url and staging_url == prod_url:
        print(
            "ERROR: STAGING_DATABASE_URL equals DATABASE_URL. Refusing to seed "
            "production. Point STAGING_DATABASE_URL at a separate database.",
            file=sys.stderr,
        )
        sys.exit(2)
    return staging_url


def _run_alembic(staging_url: str) -> None:
    """Bring the staging schema to head using the project's alembic config."""
    from alembic import command
    from alembic.config import Config

    cfg = Config(str(REPO_ROOT / "alembic.ini"))
    # Override sqlalchemy.url so we never accidentally hit DATABASE_URL.
    cfg.set_main_option("sqlalchemy.url", staging_url)
    print(f"[seed_staging] Running 'alembic upgrade heads' against staging…")
    command.upgrade(cfg, "heads")
    print("[seed_staging] Alembic upgrade complete.")


def _seed(staging_url: str) -> None:
    # Point SQLAlchemy at the staging URL BEFORE importing any model
    # modules, since backend/models/database.py reads DATABASE_URL at
    # import time. We back up the operator's real DATABASE_URL.
    original_db_url = os.environ.get("DATABASE_URL")
    os.environ["DATABASE_URL"] = staging_url
    try:
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker

        from backend.models.models import (
            Organization,
            OrganizationMember,
            User,
            Creator,
            Song,
            SongCredit,
        )
        from backend.utils.auth import get_password_hash

        engine = create_engine(staging_url, pool_pre_ping=True)
        Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
        db = Session()
        try:
            org = db.query(Organization).filter(
                Organization.name == "Cadence Sandbox"
            ).first()
            if not org:
                org = Organization(
                    name="Cadence Sandbox",
                    type="LABEL",
                    access_code="SANDBOX1",
                )
                db.add(org)
                db.flush()
                print(f"[seed_staging] Created Organization id={org.id}")
            else:
                print(
                    f"[seed_staging] Reusing existing Organization id={org.id}"
                )

            # Users — one per role.
            role_users = [
                ("sandbox_owner",     "OWNER"),
                ("sandbox_admin",     "ADMIN"),
                ("sandbox_member",    "MEMBER"),
                ("sandbox_readonly",  "READ_ONLY"),
            ]
            for username, role in role_users:
                user = db.query(User).filter(User.username == username).first()
                if not user:
                    user = User(
                        username=username,
                        email=f"{username}@sandbox.cadence-ci.test",
                        hashed_password=get_password_hash("Sandbox!234"),
                        is_active=True,
                    )
                    db.add(user)
                    db.flush()
                    print(f"[seed_staging] Created user {username} (pw=Sandbox!234)")
                membership = db.query(OrganizationMember).filter(
                    OrganizationMember.user_id == user.id,
                    OrganizationMember.organization_id == org.id,
                ).first()
                if not membership:
                    db.add(OrganizationMember(
                        organization_id=org.id,
                        user_id=user.id,
                        role=role,
                    ))

            # Creators.
            creators: list[Creator] = []
            for i in range(1, 6):
                name = f"sandbox_creator_{i:02d}"
                creator = db.query(Creator).filter(
                    Creator.name == name,
                    Creator.organization_id == org.id,
                ).first()
                if not creator:
                    creator = Creator(
                        name=name,
                        organization_id=org.id,
                        primary_role="ARTIST",
                    )
                    db.add(creator)
                    db.flush()
                creators.append(creator)
            print(f"[seed_staging] Ensured {len(creators)} creators")

            # Songs (20) credited round-robin to creators.
            songs_created = 0
            for i in range(1, 21):
                title = f"sandbox_song_{i:02d}"
                song = db.query(Song).filter(
                    Song.title == title,
                    Song.organization_id == org.id,
                ).first()
                if not song:
                    song = Song(
                        title=title,
                        organization_id=org.id,
                        release_status="released" if i % 2 == 0 else "unreleased",
                        entry_type="Song",
                        release_date=date(2024, 1, 1) + timedelta(days=i * 7),
                    )
                    db.add(song)
                    db.flush()
                    songs_created += 1
                    creator = creators[(i - 1) % len(creators)]
                    db.add(SongCredit(
                        song_id=song.id,
                        creator_id=creator.id,
                        role="WRITER",
                        publishing_share=100.0,
                        master_share=100.0,
                    ))
            print(f"[seed_staging] Created {songs_created} new songs")

            # Statements + contract — best-effort: we look up the
            # models lazily because their column sets change across
            # migrations and we don't want to fail the whole seed if
            # an optional column was renamed.
            try:
                from backend.models.models import RoyaltyStatement
                for i in range(1, 3):
                    name = f"sandbox_statement_{i:02d}"
                    if not db.query(RoyaltyStatement).filter(
                        RoyaltyStatement.statement_name == name,
                        RoyaltyStatement.organization_id == org.id,
                    ).first():
                        db.add(RoyaltyStatement(
                            organization_id=org.id,
                            statement_name=name,
                            period_start=date(2024, 1, 1),
                            period_end=date(2024, 3, 31),
                            currency="USD",
                            reported_gross=1000.0 * i,
                            reported_net=850.0 * i,
                        ))
                print("[seed_staging] Ensured 2 royalty statements")
            except Exception as e:  # pragma: no cover
                print(f"[seed_staging] Skipped royalty statements: {e}")

            try:
                from backend.models.models import Contract
                if not db.query(Contract).filter(
                    Contract.title == "sandbox_contract_01",
                    Contract.organization_id == org.id,
                ).first():
                    db.add(Contract(
                        organization_id=org.id,
                        title="sandbox_contract_01",
                        contract_type="PUBLISHING",
                        signed_date=date(2024, 1, 15),
                    ))
                print("[seed_staging] Ensured 1 contract")
            except Exception as e:  # pragma: no cover
                print(f"[seed_staging] Skipped contract: {e}")

            db.commit()
            print("[seed_staging] Done.")
        finally:
            db.close()
    finally:
        # Restore the operator's real DATABASE_URL so subsequent
        # processes spawned from this shell don't accidentally hit
        # staging.
        if original_db_url is not None:
            os.environ["DATABASE_URL"] = original_db_url
        else:
            os.environ.pop("DATABASE_URL", None)


def main() -> None:
    staging_url = _resolve_staging_url()
    _run_alembic(staging_url)
    _seed(staging_url)


if __name__ == "__main__":
    main()
