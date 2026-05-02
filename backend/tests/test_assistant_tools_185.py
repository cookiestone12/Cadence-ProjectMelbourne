"""Tests for Task #185 — smarter Cadence assistant.

Covers:
  * read tools are org-scoped and refuse cross-org access
  * write tools return a proposed_action and never mutate
  * confirm flow executes + writes an audit-log row tagged source=assistant
  * confirm respects ownership + expiry
  * cancel drops a stored proposed action
  * page-context block injection into the system prompt
"""

import pytest
from datetime import datetime, timedelta, date
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from backend.models.database import Base
from backend.models.models import (
    User, Organization, OrganizationMember,
    Song, SongCredit, Creator, Placement, ActionItem, Contract, AuditLog,
    RoyaltyStatement, RoyaltyStatementLine,
)
from backend.services import assistant_tools
from backend.routes.assistant import (
    _build_page_context_block, PageContext,
)


SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function")
def db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    s = TestingSessionLocal()
    try:
        yield s
    finally:
        s.close()
    assistant_tools.clear_proposed_actions_for_test()


@pytest.fixture
def two_orgs(db: Session):
    """Two orgs, two members. Returns (org_a, user_a, org_b, user_b)."""
    user_a = User(username="alice", email="a@x.io", hashed_password="x",
                  is_active=True)
    user_b = User(username="bob", email="b@x.io", hashed_password="x",
                  is_active=True)
    db.add_all([user_a, user_b])
    db.flush()

    org_a = Organization(name="OrgA", type="LABEL", account_type="ENTERPRISE")
    org_b = Organization(name="OrgB", type="LABEL", account_type="ENTERPRISE")
    db.add_all([org_a, org_b])
    db.flush()

    db.add_all([
        OrganizationMember(organization_id=org_a.id, user_id=user_a.id, role="OWNER"),
        OrganizationMember(organization_id=org_b.id, user_id=user_b.id, role="OWNER"),
    ])
    db.commit()
    return org_a, user_a, org_b, user_b


@pytest.fixture
def seeded(db: Session, two_orgs):
    org_a, user_a, org_b, user_b = two_orgs
    song_a = Song(organization_id=org_a.id, title="A-Song",
                  primary_artist="A-Artist", isrc="USAAA0000001",
                  status_health_score=80.0)
    song_b = Song(organization_id=org_b.id, title="B-Song",
                  primary_artist="B-Artist", isrc="USBBB0000001")
    db.add_all([song_a, song_b])
    db.flush()
    placement_a = Placement(organization_id=org_a.id, title="P-A",
                            placement_type="SYNC", status="PITCHED")
    db.add(placement_a)
    db.commit()
    return {
        "org_a": org_a, "user_a": user_a,
        "org_b": org_b, "user_b": user_b,
        "song_a": song_a, "song_b": song_b,
        "placement_a": placement_a,
    }


# ---------------------------------------------------------------------------
# Read tools
# ---------------------------------------------------------------------------

class TestReadToolsOrgScoping:

    def test_search_songs_returns_only_own_org(self, db, seeded):
        out = assistant_tools.dispatch_tool(
            "search_songs", {"query": ""},
            db=db, org_id=seeded["org_a"].id, user_id=seeded["user_a"].id,
        )
        assert "results" in out
        ids = [r["id"] for r in out["results"]]
        assert seeded["song_a"].id in ids
        assert seeded["song_b"].id not in ids

    def test_get_song_health_rejects_cross_org(self, db, seeded):
        out = assistant_tools.dispatch_tool(
            "get_song_health", {"song_id": seeded["song_b"].id},
            db=db, org_id=seeded["org_a"].id, user_id=seeded["user_a"].id,
        )
        assert "error" in out

    def test_get_song_health_returns_gaps(self, db, seeded):
        out = assistant_tools.dispatch_tool(
            "get_song_health", {"song_id": seeded["song_a"].id},
            db=db, org_id=seeded["org_a"].id, user_id=seeded["user_a"].id,
        )
        assert out["id"] == seeded["song_a"].id
        # song_a has no ISWC and no contract executed by default → gaps present
        assert isinstance(out["gaps"], list)
        assert any("ISWC" in g for g in out["gaps"])

    def test_search_creators_org_scoped(self, db, seeded):
        creator_a = Creator(organization_id=seeded["org_a"].id,
                            display_name="Alice Writer", legal_name="A. Writer")
        creator_b = Creator(organization_id=seeded["org_b"].id,
                            display_name="Bob Writer", legal_name="B. Writer")
        db.add_all([creator_a, creator_b])
        db.commit()
        out = assistant_tools.dispatch_tool(
            "search_creators", {"query": "Writer"},
            db=db, org_id=seeded["org_a"].id, user_id=seeded["user_a"].id,
        )
        ids = [r["id"] for r in out["results"]]
        assert creator_a.id in ids
        assert creator_b.id not in ids

    def test_dispatch_requires_org(self, db, seeded):
        out = assistant_tools.dispatch_tool(
            "search_songs", {},
            db=db, org_id=None, user_id=seeded["user_a"].id,
        )
        assert "error" in out

    def test_unknown_tool(self, db, seeded):
        out = assistant_tools.dispatch_tool(
            "does_not_exist", {},
            db=db, org_id=seeded["org_a"].id, user_id=seeded["user_a"].id,
        )
        assert "error" in out


# ---------------------------------------------------------------------------
# Write tools — proposed action flow
# ---------------------------------------------------------------------------

class TestWriteToolsAreProposalsOnly:

    def test_create_song_does_not_mutate(self, db, seeded):
        before = db.query(Song).filter(
            Song.organization_id == seeded["org_a"].id
        ).count()
        out = assistant_tools.dispatch_tool(
            "create_song", {"title": "New One", "primary_artist": "X"},
            db=db, org_id=seeded["org_a"].id, user_id=seeded["user_a"].id,
        )
        assert "proposed_action" in out
        assert out["proposed_action"]["kind"] == "create_song"
        after = db.query(Song).filter(
            Song.organization_id == seeded["org_a"].id
        ).count()
        assert before == after

    def test_create_placement_validates_song_org(self, db, seeded):
        # song_b belongs to org_b — must be refused for org_a's user
        out = assistant_tools.dispatch_tool(
            "create_placement",
            {"title": "Sneaky", "song_id": seeded["song_b"].id},
            db=db, org_id=seeded["org_a"].id, user_id=seeded["user_a"].id,
        )
        assert "error" in out

    def test_update_placement_status_validates_status(self, db, seeded):
        out = assistant_tools.dispatch_tool(
            "update_placement_status",
            {"placement_id": seeded["placement_a"].id, "new_status": "BOGUS"},
            db=db, org_id=seeded["org_a"].id, user_id=seeded["user_a"].id,
        )
        assert "error" in out

    def test_create_action_item_validates_creator_org(self, db, seeded):
        creator_b = Creator(organization_id=seeded["org_b"].id,
                            display_name="Other", legal_name="Other")
        db.add(creator_b)
        db.commit()
        out = assistant_tools.dispatch_tool(
            "create_action_item",
            {"title": "do thing", "creator_id": creator_b.id},
            db=db, org_id=seeded["org_a"].id, user_id=seeded["user_a"].id,
        )
        assert "error" in out


# ---------------------------------------------------------------------------
# Confirm flow
# ---------------------------------------------------------------------------

class TestConfirmFlow:

    def test_confirm_creates_song_and_audits(self, db, seeded):
        out = assistant_tools.dispatch_tool(
            "create_song", {"title": "Confirmed Song", "primary_artist": "X"},
            db=db, org_id=seeded["org_a"].id, user_id=seeded["user_a"].id,
        )
        action_id = out["proposed_action"]["id"]
        result = assistant_tools.execute_proposed_action(
            action_id, db=db, user=seeded["user_a"],
        )
        assert result["entity_type"] == "SONG"
        song = db.query(Song).filter(Song.id == result["entity_id"]).first()
        assert song is not None
        assert song.title == "Confirmed Song"
        assert song.organization_id == seeded["org_a"].id

        audit = db.query(AuditLog).filter(
            AuditLog.entity_type == "SONG",
            AuditLog.entity_id == song.id,
        ).first()
        assert audit is not None
        assert audit.action == "ASSISTANT_CREATE_SONG"
        assert audit.details and audit.details.get("source") == "assistant"

        # Action is consumed
        assert assistant_tools.get_proposed_action(action_id) is None

    def test_confirm_rejects_other_user(self, db, seeded):
        out = assistant_tools.dispatch_tool(
            "create_song", {"title": "Mine"},
            db=db, org_id=seeded["org_a"].id, user_id=seeded["user_a"].id,
        )
        action_id = out["proposed_action"]["id"]
        with pytest.raises(PermissionError):
            assistant_tools.execute_proposed_action(
                action_id, db=db, user=seeded["user_b"],
            )

    def test_confirm_rejects_expired(self, db, seeded):
        out = assistant_tools.dispatch_tool(
            "create_song", {"title": "Stale"},
            db=db, org_id=seeded["org_a"].id, user_id=seeded["user_a"].id,
        )
        action_id = out["proposed_action"]["id"]
        pa = assistant_tools.get_proposed_action(action_id)
        pa.expires_at = datetime.utcnow() - timedelta(seconds=1)
        with pytest.raises(LookupError):
            assistant_tools.execute_proposed_action(
                action_id, db=db, user=seeded["user_a"],
            )

    def test_confirm_unknown(self, db, seeded):
        with pytest.raises(LookupError):
            assistant_tools.execute_proposed_action(
                "nope", db=db, user=seeded["user_a"],
            )

    def test_cancel_removes(self, db, seeded):
        out = assistant_tools.dispatch_tool(
            "create_song", {"title": "Cancel Me"},
            db=db, org_id=seeded["org_a"].id, user_id=seeded["user_a"].id,
        )
        action_id = out["proposed_action"]["id"]
        assert assistant_tools.get_proposed_action(action_id) is not None
        assistant_tools.remove_proposed_action(action_id)
        assert assistant_tools.get_proposed_action(action_id) is None

    def test_double_confirm_is_idempotent(self, db, seeded):
        """Two concurrent confirms must execute the action exactly once."""
        out = assistant_tools.dispatch_tool(
            "create_song", {"title": "Race"},
            db=db, org_id=seeded["org_a"].id, user_id=seeded["user_a"].id,
        )
        action_id = out["proposed_action"]["id"]

        before = db.query(Song).filter(
            Song.organization_id == seeded["org_a"].id,
            Song.title == "Race",
        ).count()
        assert before == 0

        # First confirm — should succeed
        result = assistant_tools.execute_proposed_action(
            action_id, db=db, user=seeded["user_a"],
        )
        assert result["entity_type"] == "SONG"

        # Second confirm — must raise, not double-create
        with pytest.raises(LookupError):
            assistant_tools.execute_proposed_action(
                action_id, db=db, user=seeded["user_a"],
            )

        after = db.query(Song).filter(
            Song.organization_id == seeded["org_a"].id,
            Song.title == "Race",
        ).count()
        assert after == 1

    def test_update_placement_status_executes(self, db, seeded):
        out = assistant_tools.dispatch_tool(
            "update_placement_status",
            {"placement_id": seeded["placement_a"].id, "new_status": "IN_REVIEW"},
            db=db, org_id=seeded["org_a"].id, user_id=seeded["user_a"].id,
        )
        action_id = out["proposed_action"]["id"]
        assistant_tools.execute_proposed_action(
            action_id, db=db, user=seeded["user_a"],
        )
        db.refresh(seeded["placement_a"])
        assert seeded["placement_a"].status == "IN_REVIEW"


# ---------------------------------------------------------------------------
# CLIENT role enforcement
# ---------------------------------------------------------------------------

@pytest.fixture
def client_seed(db: Session, seeded):
    """Add a CLIENT user in org_a linked to a creator who owns song_a."""
    creator_mine = Creator(
        organization_id=seeded["org_a"].id,
        display_name="Mine",
    )
    creator_other = Creator(
        organization_id=seeded["org_a"].id,
        display_name="Other",
    )
    db.add_all([creator_mine, creator_other])
    db.flush()

    other_song = Song(organization_id=seeded["org_a"].id, title="A-Other",
                      primary_artist="Other-Artist")
    db.add(other_song)
    db.flush()
    db.add_all([
        SongCredit(song_id=seeded["song_a"].id, creator_id=creator_mine.id,
                   role="WRITER"),
        SongCredit(song_id=other_song.id, creator_id=creator_other.id,
                   role="WRITER"),
    ])

    client_user = User(username="client", email="c@x.io", hashed_password="x",
                       is_active=True)
    db.add(client_user)
    db.flush()
    db.add(OrganizationMember(
        organization_id=seeded["org_a"].id,
        user_id=client_user.id,
        role="CLIENT",
        linked_creator_id=creator_mine.id,
    ))
    db.commit()
    return {
        "client_user": client_user,
        "creator_mine": creator_mine,
        "creator_other": creator_other,
        "other_song": other_song,
    }


class TestClientRoleEnforcement:

    def test_client_search_songs_only_returns_own_catalog(
        self, db, seeded, client_seed,
    ):
        out = assistant_tools.dispatch_tool(
            "search_songs", {"query": ""},
            db=db, org_id=seeded["org_a"].id,
            user_id=client_seed["client_user"].id,
            user_role="CLIENT",
            linked_creator_id=client_seed["creator_mine"].id,
        )
        ids = [r["id"] for r in out["results"]]
        assert seeded["song_a"].id in ids
        assert client_seed["other_song"].id not in ids

    def test_client_cannot_view_other_creator_summary(
        self, db, seeded, client_seed,
    ):
        out = assistant_tools.dispatch_tool(
            "get_creator_summary",
            {"creator_id": client_seed["creator_other"].id},
            db=db, org_id=seeded["org_a"].id,
            user_id=client_seed["client_user"].id,
            user_role="CLIENT",
            linked_creator_id=client_seed["creator_mine"].id,
        )
        assert "error" in out

    def test_client_cannot_get_other_song_health(
        self, db, seeded, client_seed,
    ):
        out = assistant_tools.dispatch_tool(
            "get_song_health",
            {"song_id": client_seed["other_song"].id},
            db=db, org_id=seeded["org_a"].id,
            user_id=client_seed["client_user"].id,
            user_role="CLIENT",
            linked_creator_id=client_seed["creator_mine"].id,
        )
        assert "error" in out

    def test_client_blocked_from_create_song(self, db, seeded, client_seed):
        out = assistant_tools.dispatch_tool(
            "create_song", {"title": "Forbidden"},
            db=db, org_id=seeded["org_a"].id,
            user_id=client_seed["client_user"].id,
            user_role="CLIENT",
            linked_creator_id=client_seed["creator_mine"].id,
        )
        assert "error" in out
        assert db.query(Song).filter(
            Song.organization_id == seeded["org_a"].id,
            Song.title == "Forbidden",
        ).count() == 0

    def test_client_can_create_action_item_for_self(
        self, db, seeded, client_seed,
    ):
        out = assistant_tools.dispatch_tool(
            "create_action_item",
            {"title": "Self-task", "creator_id": client_seed["creator_mine"].id},
            db=db, org_id=seeded["org_a"].id,
            user_id=client_seed["client_user"].id,
            user_role="CLIENT",
            linked_creator_id=client_seed["creator_mine"].id,
        )
        assert "proposed_action" in out

    def test_client_action_item_for_other_creator_rejected(
        self, db, seeded, client_seed,
    ):
        out = assistant_tools.dispatch_tool(
            "create_action_item",
            {"title": "Steal",
             "creator_id": client_seed["creator_other"].id},
            db=db, org_id=seeded["org_a"].id,
            user_id=client_seed["client_user"].id,
            user_role="CLIENT",
            linked_creator_id=client_seed["creator_mine"].id,
        )
        assert "error" in out

    def test_client_list_action_items_excludes_other_creators(
        self, db, seeded, client_seed,
    ):
        # Three action items in OrgA:
        #   - assigned to nobody, tied to "creator_other"  -> MUST be hidden
        #   - assigned to nobody, tied to "creator_mine"   -> visible (own creator)
        #   - assigned directly to the client user         -> visible (own assignment)
        leak = ActionItem(
            organization_id=seeded["org_a"].id,
            creator_id=client_seed["creator_other"].id,
            action_type="REVIEW", title="Other creator task",
            status="PENDING",
        )
        own_creator = ActionItem(
            organization_id=seeded["org_a"].id,
            creator_id=client_seed["creator_mine"].id,
            action_type="REVIEW", title="My creator task",
            status="PENDING",
        )
        direct = ActionItem(
            organization_id=seeded["org_a"].id,
            assigned_to_user_id=client_seed["client_user"].id,
            action_type="REVIEW", title="Assigned to me",
            status="PENDING",
        )
        db.add_all([leak, own_creator, direct])
        db.commit()

        out = assistant_tools.dispatch_tool(
            "list_action_items_for_user", {},
            db=db, org_id=seeded["org_a"].id,
            user_id=client_seed["client_user"].id,
            user_role="CLIENT",
            linked_creator_id=client_seed["creator_mine"].id,
        )
        titles = {r.get("title") for r in out["results"]}
        assert "Other creator task" not in titles
        assert "My creator task" in titles
        assert "Assigned to me" in titles


# ---------------------------------------------------------------------------
# Royalty period filter
# ---------------------------------------------------------------------------

class TestRoyaltyPeriodFilter:

    def test_period_filter_clamps_to_window(self, db, seeded):
        # Two statements: one in Q1 of last year, one in current quarter.
        today = date.today()
        last_year = today.year - 1
        stmt_old = RoyaltyStatement(
            organization_id=seeded["org_a"].id,
            source_name="DSP-Old", source_type="DSP",
            period_start=date(last_year, 1, 1),
            period_end=date(last_year, 3, 31),
            total_revenue_cents=10000,
        )
        stmt_new = RoyaltyStatement(
            organization_id=seeded["org_a"].id,
            source_name="DSP-New", source_type="DSP",
            period_start=date(today.year, today.month, 1),
            period_end=today,
            total_revenue_cents=20000,
        )
        db.add_all([stmt_old, stmt_new])
        db.flush()
        db.add_all([
            RoyaltyStatementLine(
                org_id=seeded["org_a"].id, statement_id=stmt_old.id,
                matched_song_id=seeded["song_a"].id, net_amount=100.0,
            ),
            RoyaltyStatementLine(
                org_id=seeded["org_a"].id, statement_id=stmt_new.id,
                matched_song_id=seeded["song_a"].id, net_amount=50.0,
            ),
        ])
        db.commit()

        # All-time
        out = assistant_tools.dispatch_tool(
            "get_royalty_summary_for_song",
            {"song_id": seeded["song_a"].id},
            db=db, org_id=seeded["org_a"].id, user_id=seeded["user_a"].id,
        )
        assert out["matched_statement_lines"] == 2
        assert round(out["net_royalties"], 2) == 150.0

        # last_year — only the older statement
        out = assistant_tools.dispatch_tool(
            "get_royalty_summary_for_song",
            {"song_id": seeded["song_a"].id, "period": "last_year"},
            db=db, org_id=seeded["org_a"].id, user_id=seeded["user_a"].id,
        )
        assert out["matched_statement_lines"] == 1
        assert round(out["net_royalties"], 2) == 100.0
        assert str(last_year) in out["period"]

        # Explicit window covering only the current statement
        out = assistant_tools.dispatch_tool(
            "get_royalty_summary_for_song",
            {"song_id": seeded["song_a"].id,
             "period_start": date(today.year, 1, 1).isoformat(),
             "period_end": today.isoformat()},
            db=db, org_id=seeded["org_a"].id, user_id=seeded["user_a"].id,
        )
        assert out["matched_statement_lines"] == 1
        assert round(out["net_royalties"], 2) == 50.0


# ---------------------------------------------------------------------------
# Page-context block
# ---------------------------------------------------------------------------

class TestPageContextBlock:

    def test_no_context_returns_empty(self):
        assert _build_page_context_block(None) == ""
        assert _build_page_context_block(PageContext()) == ""

    def test_renders_known_fields(self):
        block = _build_page_context_block(PageContext(
            page="catalog", path="/catalog", song_id=123,
        ))
        assert "page=catalog" in block
        assert "song_id=123" in block
        assert "path=/catalog" in block

    def test_ignores_unknowns(self):
        block = _build_page_context_block(PageContext(creator_id=7))
        assert "creator_id=7" in block
        assert "song_id" not in block
