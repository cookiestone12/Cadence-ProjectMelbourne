"""Seed a staging database with a deterministic, isolated dataset.

Connects to the database identified by ``STAGING_DATABASE_URL``
(NEVER the production ``DATABASE_URL``), runs the Alembic migration
chain to bring it to head, and then idempotently seeds:

  * MasterPAdmin staff user (global)
  * a single ``Cadence Sandbox`` organization
  * one user per OrganizationMemberRole (OWNER, ADMIN, MEMBER, CLIENT)
  * 5 creators (sandbox_creator_*)
  * 20 songs (sandbox_song_*) credited across the creators
  * 2 royalty statements (sandbox_statement_*)
  * 1 contract (sandbox_contract_*)

Every row is name-prefixed with ``sandbox_`` so a staging operator
can grep / DELETE the seeded set without affecting any other org
that happens to share the database. The script is safe to re-run:
existing rows are detected by name and skipped.

After seeding the script asserts post-seed counts and exits non-zero
if any required entity is missing — failures are NOT silently
swallowed.

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
from datetime import date, timedelta
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))


SANDBOX_ORG_NAME = "Cadence Sandbox"
SANDBOX_PASSWORD = "Sandbox!234"
ROLE_USERS = [
    ("sandbox_owner",  "OWNER"),
    ("sandbox_admin",  "ADMIN"),
    ("sandbox_member", "MEMBER"),
    ("sandbox_client", "CLIENT"),
]
NUM_CREATORS = 5
NUM_SONGS = 20
NUM_STATEMENTS = 2
NUM_CONTRACTS = 1


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


def _sanitize_db_url(url: str) -> str:
    """Strip credentials so we can safely log the resolved target."""
    try:
        from urllib.parse import urlparse, urlunparse
        p = urlparse(url)
        netloc = p.hostname or ""
        if p.port:
            netloc += f":{p.port}"
        if p.username:
            netloc = f"***@{netloc}"
        return urlunparse((p.scheme, netloc, p.path, "", "", ""))
    except Exception:
        return "<unparseable>"


def _run_alembic(staging_url: str) -> None:
    """Bring the staging schema to head against STAGING_DATABASE_URL.

    ``alembic/env.py`` in this repo imports ``DATABASE_URL`` from
    ``backend.models.database`` at import time and ignores the
    ``sqlalchemy.url`` set on the Alembic Config. We therefore MUST
    overwrite ``os.environ["DATABASE_URL"]`` before invoking Alembic
    to guarantee migrations land on staging, not whatever URL the
    operator's shell happens to have set.
    """
    from alembic import command
    from alembic.config import Config

    print(f"[seed_staging] Alembic target: {_sanitize_db_url(staging_url)}")
    original = os.environ.get("DATABASE_URL")
    os.environ["DATABASE_URL"] = staging_url
    try:
        cfg = Config(str(REPO_ROOT / "alembic.ini"))
        cfg.set_main_option("sqlalchemy.url", staging_url)
        print("[seed_staging] Running 'alembic upgrade heads' against staging…")
        command.upgrade(cfg, "heads")
        print("[seed_staging] Alembic upgrade complete.")
    finally:
        if original is not None:
            os.environ["DATABASE_URL"] = original
        else:
            os.environ.pop("DATABASE_URL", None)


def _seed(staging_url: str) -> None:
    # Point SQLAlchemy at the staging URL BEFORE importing any model
    # modules, since backend/models/database.py reads DATABASE_URL at
    # import time. We back up the operator's real DATABASE_URL.
    original_db_url = os.environ.get("DATABASE_URL")
    os.environ["DATABASE_URL"] = staging_url
    try:
        from sqlalchemy import create_engine, func
        from sqlalchemy.orm import sessionmaker

        from backend.models.models import (
            Organization,
            OrganizationMember,
            User,
            Creator,
            Song,
            SongCredit,
            RoyaltyStatement,
            Contract,
        )
        # Hash directly with bcrypt rather than importing
        # backend.utils.auth, which requires SESSION_SECRET at import
        # time. The seed script must run with only STAGING_DATABASE_URL.
        import bcrypt

        def get_password_hash(pw: str) -> str:
            return bcrypt.hashpw(pw.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

        engine = create_engine(staging_url, pool_pre_ping=True)
        Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
        db = Session()
        try:
            # ----- MasterPAdmin (global staff user) -----
            master = db.query(User).filter(
                func.lower(User.username) == "masterpadmin"
            ).first()
            if not master:
                master = User(
                    username="MasterPAdmin",
                    email="masterpadmin@sandbox.cadence-ci.test",
                    hashed_password=get_password_hash(SANDBOX_PASSWORD),
                    is_active=True,
                    is_cadence_staff=True,
                )
                db.add(master)
                db.flush()
                print(f"[seed_staging] Created MasterPAdmin staff user id={master.id}")
            else:
                # Ensure existing record has staff bit set; do not touch password.
                if not master.is_cadence_staff:
                    master.is_cadence_staff = True
                print(f"[seed_staging] Reusing existing MasterPAdmin id={master.id}")

            # ----- Cadence Sandbox org -----
            org = db.query(Organization).filter(
                Organization.name == SANDBOX_ORG_NAME
            ).first()
            if not org:
                org = Organization(
                    name=SANDBOX_ORG_NAME,
                    type="LABEL",
                    access_code="SANDBOX1",
                )
                db.add(org)
                db.flush()
                print(f"[seed_staging] Created Organization id={org.id}")
            else:
                print(f"[seed_staging] Reusing existing Organization id={org.id}")

            # ----- Users at every membership role -----
            for username, role in ROLE_USERS:
                user = db.query(User).filter(User.username == username).first()
                if not user:
                    user = User(
                        username=username,
                        email=f"{username}@sandbox.cadence-ci.test",
                        hashed_password=get_password_hash(SANDBOX_PASSWORD),
                        is_active=True,
                    )
                    db.add(user)
                    db.flush()
                    print(f"[seed_staging] Created user {username}")
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

            # ----- Creators -----
            creators: list[Creator] = []
            for i in range(1, NUM_CREATORS + 1):
                name = f"sandbox_creator_{i:02d}"
                creator = db.query(Creator).filter(
                    Creator.display_name == name,
                    Creator.organization_id == org.id,
                ).first()
                if not creator:
                    creator = Creator(
                        organization_id=org.id,
                        display_name=name,
                        legal_name=name.replace("_", " ").title(),
                        roles=["ARTIST"],
                    )
                    db.add(creator)
                    db.flush()
                creators.append(creator)
            print(f"[seed_staging] Ensured {len(creators)} creators")

            # ----- Songs (20) credited round-robin to creators -----
            songs_created = 0
            for i in range(1, NUM_SONGS + 1):
                title = f"sandbox_song_{i:02d}"
                creator = creators[(i - 1) % len(creators)]
                song = db.query(Song).filter(
                    Song.title == title,
                    Song.organization_id == org.id,
                ).first()
                if not song:
                    song = Song(
                        organization_id=org.id,
                        title=title,
                        primary_artist=creator.display_name,
                        asset_type="TRACK",
                        release_status="released" if i % 2 == 0 else "unreleased",
                        entry_type="Song",
                        release_date=date(2024, 1, 1) + timedelta(days=i * 7),
                    )
                    db.add(song)
                    db.flush()
                    songs_created += 1
                    db.add(SongCredit(
                        song_id=song.id,
                        creator_id=creator.id,
                        role="SONGWRITER",
                        pub_share=100.0,
                        master_share=100.0,
                    ))
            print(f"[seed_staging] Created {songs_created} new songs (target {NUM_SONGS})")

            # ----- Royalty statements -----
            for i in range(1, NUM_STATEMENTS + 1):
                source_name = f"sandbox_statement_{i:02d}"
                stmt = db.query(RoyaltyStatement).filter(
                    RoyaltyStatement.source_name == source_name,
                    RoyaltyStatement.organization_id == org.id,
                ).first()
                if not stmt:
                    db.add(RoyaltyStatement(
                        organization_id=org.id,
                        source_name=source_name,
                        source_type="SANDBOX",
                        period_start=date(2024, 1, 1),
                        period_end=date(2024, 3, 31),
                        currency="USD",
                        status="PENDING",
                        reported_gross=1000.0 * i,
                        reported_net=850.0 * i,
                    ))
            print(f"[seed_staging] Ensured {NUM_STATEMENTS} royalty statements")

            # ----- Contract -----
            for i in range(1, NUM_CONTRACTS + 1):
                title = f"sandbox_contract_{i:02d}"
                ctr = db.query(Contract).filter(
                    Contract.title == title,
                    Contract.organization_id == org.id,
                ).first()
                if not ctr:
                    db.add(Contract(
                        organization_id=org.id,
                        title=title,
                        contract_type="PUBLISHING",
                        status="ACTIVE",
                        start_date=date(2024, 1, 15),
                        end_date=date(2027, 1, 14),
                        creator_id=creators[0].id,
                    ))
            print(f"[seed_staging] Ensured {NUM_CONTRACTS} contract")

            db.commit()

            # ----- Post-seed assertions: fail loudly if anything is missing -----
            org_id = org.id
            counts = {
                "organization":    db.query(Organization).filter(Organization.id == org_id).count(),
                "memberships":     db.query(OrganizationMember).filter(OrganizationMember.organization_id == org_id).count(),
                "creators":        db.query(Creator).filter(Creator.organization_id == org_id).count(),
                "songs":           db.query(Song).filter(Song.organization_id == org_id).count(),
                "statements":      db.query(RoyaltyStatement).filter(RoyaltyStatement.organization_id == org_id).count(),
                "contracts":       db.query(Contract).filter(Contract.organization_id == org_id).count(),
            }
            print(f"[seed_staging] Post-seed counts: {counts}")
            problems = []
            if counts["organization"] != 1:
                problems.append("Cadence Sandbox org missing")
            if counts["memberships"] < len(ROLE_USERS):
                problems.append(
                    f"expected ≥{len(ROLE_USERS)} memberships, got {counts['memberships']}"
                )
            if counts["creators"] < NUM_CREATORS:
                problems.append(f"expected ≥{NUM_CREATORS} creators, got {counts['creators']}")
            if counts["songs"] < NUM_SONGS:
                problems.append(f"expected ≥{NUM_SONGS} songs, got {counts['songs']}")
            if counts["statements"] < NUM_STATEMENTS:
                problems.append(
                    f"expected ≥{NUM_STATEMENTS} statements, got {counts['statements']}"
                )
            if counts["contracts"] < NUM_CONTRACTS:
                problems.append(
                    f"expected ≥{NUM_CONTRACTS} contracts, got {counts['contracts']}"
                )
            if problems:
                print(
                    "ERROR: post-seed validation failed: " + "; ".join(problems),
                    file=sys.stderr,
                )
                sys.exit(3)
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
