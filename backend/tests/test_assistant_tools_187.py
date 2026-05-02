"""Tests for Task #187 — extra assistant write tools.

Covers the new write tools added in Task #187:
  * mark_song_released
  * update_song_metadata (title / isrc / iswc only)
  * assign_action_item
  * add_song_credit
  * record_payment

For each tool we verify:
  * org-scope checks block cross-org references
  * the tool only proposes — no DB mutation until confirm
  * confirming the proposal performs the mutation AND writes an
    AuditLog row tagged ``details.source = "assistant"``
  * CLIENT users are refused (these aren't in CLIENT_ALLOWED_WRITE_TOOLS)
"""

from datetime import date

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from backend.models.database import Base
from backend.models.models import (
    User, Organization, OrganizationMember,
    Song, SongCredit, Creator, ActionItem, Contract, Payment, AuditLog,
)
from backend.services import assistant_tools


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
def world(db: Session):
    """Two orgs, members, songs, creators, an action item, a contract."""
    user_a = User(username="alice", email="a@x.io", hashed_password="x",
                  is_active=True)
    user_b = User(username="bob", email="b@x.io", hashed_password="x",
                  is_active=True)
    user_c = User(username="carol", email="c@x.io", hashed_password="x",
                  is_active=True)
    db.add_all([user_a, user_b, user_c])
    db.flush()

    org_a = Organization(name="OrgA", type="LABEL", account_type="ENTERPRISE")
    org_b = Organization(name="OrgB", type="LABEL", account_type="ENTERPRISE")
    db.add_all([org_a, org_b])
    db.flush()

    db.add_all([
        OrganizationMember(organization_id=org_a.id, user_id=user_a.id,
                           role="OWNER"),
        OrganizationMember(organization_id=org_a.id, user_id=user_c.id,
                           role="MEMBER"),
        OrganizationMember(organization_id=org_b.id, user_id=user_b.id,
                           role="OWNER"),
    ])

    song_a = Song(organization_id=org_a.id, title="A-Song",
                  primary_artist="A-Artist", isrc="USAAA0000001")
    song_b = Song(organization_id=org_b.id, title="B-Song",
                  primary_artist="B-Artist", isrc="USBBB0000001")
    db.add_all([song_a, song_b])
    db.flush()

    creator_a = Creator(organization_id=org_a.id, display_name="A. Writer",
                        legal_name="A Writer")
    creator_b = Creator(organization_id=org_b.id, display_name="B. Writer",
                        legal_name="B Writer")
    db.add_all([creator_a, creator_b])
    db.flush()

    action_a = ActionItem(
        organization_id=org_a.id,
        action_type="REVIEW",
        title="Review splits",
        status="PENDING",
    )
    db.add(action_a)

    contract_a = Contract(organization_id=org_a.id, title="A-Contract",
                          contract_type="PUBLISHING", status="DRAFT")
    db.add(contract_a)

    db.commit()
    return {
        "user_a": user_a, "user_b": user_b, "user_c": user_c,
        "org_a": org_a, "org_b": org_b,
        "song_a": song_a, "song_b": song_b,
        "creator_a": creator_a, "creator_b": creator_b,
        "action_a": action_a,
        "contract_a": contract_a,
    }


def _dispatch(name: str, args: dict, *, world, db: Session) -> dict:
    return assistant_tools.dispatch_tool(
        name, args,
        db=db, org_id=world["org_a"].id, user_id=world["user_a"].id,
    )


def _confirm(out: dict, *, world, db: Session) -> dict:
    action_id = out["proposed_action"]["id"]
    return assistant_tools.execute_proposed_action(
        action_id, db=db, user=world["user_a"],
    )


# ---------------------------------------------------------------------------
# mark_song_released
# ---------------------------------------------------------------------------

class TestMarkSongReleased:

    def test_cross_org_song_rejected(self, db, world):
        out = _dispatch(
            "mark_song_released", {"song_id": world["song_b"].id},
            world=world, db=db,
        )
        assert "error" in out

    def test_propose_only_no_mutation(self, db, world):
        assert world["song_a"].is_released is False
        out = _dispatch(
            "mark_song_released", {"song_id": world["song_a"].id},
            world=world, db=db,
        )
        assert "proposed_action" in out
        assert out["proposed_action"]["kind"] == "mark_song_released"
        db.refresh(world["song_a"])
        assert world["song_a"].is_released is False

    def test_bad_release_date_rejected(self, db, world):
        out = _dispatch(
            "mark_song_released",
            {"song_id": world["song_a"].id, "release_date": "not-a-date"},
            world=world, db=db,
        )
        assert "error" in out

    def test_confirm_releases_song_and_audits(self, db, world):
        out = _dispatch(
            "mark_song_released",
            {"song_id": world["song_a"].id,
             "release_date": "2026-04-01"},
            world=world, db=db,
        )
        result = _confirm(out, world=world, db=db)
        assert result["entity_type"] == "SONG"

        db.refresh(world["song_a"])
        assert world["song_a"].is_released is True
        assert world["song_a"].release_status == "released"
        assert world["song_a"].release_date == date(2026, 4, 1)

        audit = db.query(AuditLog).filter(
            AuditLog.action == "ASSISTANT_MARK_SONG_RELEASED",
            AuditLog.entity_id == world["song_a"].id,
        ).first()
        assert audit is not None
        assert audit.details and audit.details.get("source") == "assistant"


# ---------------------------------------------------------------------------
# update_song_metadata
# ---------------------------------------------------------------------------

class TestUpdateSongMetadata:

    def test_cross_org_song_rejected(self, db, world):
        out = _dispatch(
            "update_song_metadata",
            {"song_id": world["song_b"].id, "title": "Hijack"},
            world=world, db=db,
        )
        assert "error" in out

    def test_blank_title_rejected(self, db, world):
        out = _dispatch(
            "update_song_metadata",
            {"song_id": world["song_a"].id, "title": "   "},
            world=world, db=db,
        )
        assert "error" in out

    def test_no_changes_rejected(self, db, world):
        out = _dispatch(
            "update_song_metadata",
            {"song_id": world["song_a"].id, "title": world["song_a"].title},
            world=world, db=db,
        )
        assert "error" in out

    def test_propose_only_no_mutation(self, db, world):
        original_title = world["song_a"].title
        out = _dispatch(
            "update_song_metadata",
            {"song_id": world["song_a"].id, "title": "Renamed"},
            world=world, db=db,
        )
        assert "proposed_action" in out
        db.refresh(world["song_a"])
        assert world["song_a"].title == original_title

    def test_confirm_applies_only_provided_fields(self, db, world):
        out = _dispatch(
            "update_song_metadata",
            {"song_id": world["song_a"].id,
             "title": "Renamed Song",
             "iswc": "T-345.246.800-1"},
            world=world, db=db,
        )
        _confirm(out, world=world, db=db)

        db.refresh(world["song_a"])
        assert world["song_a"].title == "Renamed Song"
        assert world["song_a"].iswc == "T-345.246.800-1"
        # ISRC was not in the proposal — left intact
        assert world["song_a"].isrc == "USAAA0000001"

        audit = db.query(AuditLog).filter(
            AuditLog.action == "ASSISTANT_UPDATE_SONG_METADATA",
            AuditLog.entity_id == world["song_a"].id,
        ).first()
        assert audit is not None
        assert audit.details and audit.details.get("source") == "assistant"


# ---------------------------------------------------------------------------
# assign_action_item
# ---------------------------------------------------------------------------

class TestAssignActionItem:

    def test_cross_org_action_item_rejected(self, db, world):
        other_action = ActionItem(
            organization_id=world["org_b"].id,
            action_type="REVIEW", title="Other org task", status="PENDING",
        )
        db.add(other_action)
        db.commit()
        out = _dispatch(
            "assign_action_item",
            {"action_item_id": other_action.id,
             "assignee_user_id": world["user_a"].id},
            world=world, db=db,
        )
        assert "error" in out

    def test_assignee_must_be_org_member(self, db, world):
        # user_b is in org_b, not org_a — must be refused
        out = _dispatch(
            "assign_action_item",
            {"action_item_id": world["action_a"].id,
             "assignee_user_id": world["user_b"].id},
            world=world, db=db,
        )
        assert "error" in out

    def test_propose_only_no_mutation(self, db, world):
        assert world["action_a"].assigned_to_user_id is None
        out = _dispatch(
            "assign_action_item",
            {"action_item_id": world["action_a"].id,
             "assignee_user_id": world["user_c"].id},
            world=world, db=db,
        )
        assert "proposed_action" in out
        db.refresh(world["action_a"])
        assert world["action_a"].assigned_to_user_id is None

    def test_confirm_assigns_and_audits(self, db, world):
        out = _dispatch(
            "assign_action_item",
            {"action_item_id": world["action_a"].id,
             "assignee_user_id": world["user_c"].id},
            world=world, db=db,
        )
        _confirm(out, world=world, db=db)
        db.refresh(world["action_a"])
        assert world["action_a"].assigned_to_user_id == world["user_c"].id

        audit = db.query(AuditLog).filter(
            AuditLog.action == "ASSISTANT_ASSIGN_ACTION_ITEM",
            AuditLog.entity_id == world["action_a"].id,
        ).first()
        assert audit is not None
        assert audit.details and audit.details.get("source") == "assistant"

    def test_confirm_unassigns_with_null(self, db, world):
        # Pre-assign so we can verify the unassign path.
        world["action_a"].assigned_to_user_id = world["user_a"].id
        db.commit()
        out = _dispatch(
            "assign_action_item",
            {"action_item_id": world["action_a"].id,
             "assignee_user_id": None},
            world=world, db=db,
        )
        _confirm(out, world=world, db=db)
        db.refresh(world["action_a"])
        assert world["action_a"].assigned_to_user_id is None


# ---------------------------------------------------------------------------
# add_song_credit
# ---------------------------------------------------------------------------

class TestAddSongCredit:

    def test_cross_org_song_rejected(self, db, world):
        out = _dispatch(
            "add_song_credit",
            {"song_id": world["song_b"].id,
             "creator_id": world["creator_a"].id,
             "role": "WRITER"},
            world=world, db=db,
        )
        assert "error" in out

    def test_cross_org_creator_rejected(self, db, world):
        out = _dispatch(
            "add_song_credit",
            {"song_id": world["song_a"].id,
             "creator_id": world["creator_b"].id,
             "role": "WRITER"},
            world=world, db=db,
        )
        assert "error" in out

    def test_invalid_share_rejected(self, db, world):
        out = _dispatch(
            "add_song_credit",
            {"song_id": world["song_a"].id,
             "creator_id": world["creator_a"].id,
             "role": "WRITER",
             "pub_share": 150},
            world=world, db=db,
        )
        assert "error" in out

    def test_blank_role_rejected(self, db, world):
        out = _dispatch(
            "add_song_credit",
            {"song_id": world["song_a"].id,
             "creator_id": world["creator_a"].id,
             "role": "  "},
            world=world, db=db,
        )
        assert "error" in out

    def test_propose_only_no_mutation(self, db, world):
        before = db.query(SongCredit).filter(
            SongCredit.song_id == world["song_a"].id,
        ).count()
        out = _dispatch(
            "add_song_credit",
            {"song_id": world["song_a"].id,
             "creator_id": world["creator_a"].id,
             "role": "WRITER", "pub_share": 50, "master_share": 25},
            world=world, db=db,
        )
        assert "proposed_action" in out
        after = db.query(SongCredit).filter(
            SongCredit.song_id == world["song_a"].id,
        ).count()
        assert before == after

    def test_confirm_adds_credit_and_audits(self, db, world):
        out = _dispatch(
            "add_song_credit",
            {"song_id": world["song_a"].id,
             "creator_id": world["creator_a"].id,
             "role": "WRITER", "pub_share": 50, "master_share": 25},
            world=world, db=db,
        )
        result = _confirm(out, world=world, db=db)
        assert result["entity_type"] == "SONG_CREDIT"

        credit = db.query(SongCredit).filter(
            SongCredit.id == result["entity_id"]
        ).first()
        assert credit is not None
        assert credit.song_id == world["song_a"].id
        assert credit.creator_id == world["creator_a"].id
        assert credit.role == "WRITER"
        assert credit.pub_share == 50.0
        assert credit.master_share == 25.0

        audit = db.query(AuditLog).filter(
            AuditLog.action == "ASSISTANT_ADD_SONG_CREDIT",
            AuditLog.entity_id == credit.id,
        ).first()
        assert audit is not None
        assert audit.details and audit.details.get("source") == "assistant"


# ---------------------------------------------------------------------------
# record_payment
# ---------------------------------------------------------------------------

class TestRecordPayment:

    def test_cross_org_payee_rejected(self, db, world):
        out = _dispatch(
            "record_payment",
            {"payee_id": world["creator_b"].id, "amount_cents": 5000},
            world=world, db=db,
        )
        assert "error" in out

    def test_cross_org_contract_rejected(self, db, world):
        other_contract = Contract(organization_id=world["org_b"].id,
                                  title="X", contract_type="OTHER",
                                  status="DRAFT")
        db.add(other_contract)
        db.commit()
        out = _dispatch(
            "record_payment",
            {"payee_id": world["creator_a"].id,
             "amount_cents": 5000,
             "contract_id": other_contract.id},
            world=world, db=db,
        )
        assert "error" in out

    def test_zero_or_negative_amount_rejected(self, db, world):
        for bad_amount in (0, -10):
            out = _dispatch(
                "record_payment",
                {"payee_id": world["creator_a"].id,
                 "amount_cents": bad_amount},
                world=world, db=db,
            )
            assert "error" in out

    def test_propose_only_no_mutation(self, db, world):
        before = db.query(Payment).filter(
            Payment.organization_id == world["org_a"].id
        ).count()
        out = _dispatch(
            "record_payment",
            {"payee_id": world["creator_a"].id, "amount_cents": 12345,
             "payment_method": "WIRE", "payment_reference": "INV-001"},
            world=world, db=db,
        )
        assert "proposed_action" in out
        after = db.query(Payment).filter(
            Payment.organization_id == world["org_a"].id
        ).count()
        assert before == after

    def test_confirm_creates_payment_and_audits(self, db, world):
        out = _dispatch(
            "record_payment",
            {"payee_id": world["creator_a"].id, "amount_cents": 12345,
             "currency": "USD",
             "contract_id": world["contract_a"].id,
             "payment_method": "WIRE",
             "payment_reference": "INV-001",
             "notes": "Q1 royalty disbursement"},
            world=world, db=db,
        )
        result = _confirm(out, world=world, db=db)
        assert result["entity_type"] == "PAYMENT"

        payment = db.query(Payment).filter(
            Payment.id == result["entity_id"]
        ).first()
        assert payment is not None
        assert payment.organization_id == world["org_a"].id
        assert payment.payee_id == world["creator_a"].id
        assert payment.amount_cents == 12345
        assert payment.status == "PENDING"
        assert payment.payment_method == "WIRE"
        assert payment.payment_reference == "INV-001"
        assert payment.notes == "Q1 royalty disbursement"
        assert payment.contract_id == world["contract_a"].id
        assert payment.created_by_user_id == world["user_a"].id

        audit = db.query(AuditLog).filter(
            AuditLog.action == "ASSISTANT_RECORD_PAYMENT",
            AuditLog.entity_id == payment.id,
        ).first()
        assert audit is not None
        assert audit.details and audit.details.get("source") == "assistant"


# ---------------------------------------------------------------------------
# CLIENT role gating — none of the new tools should be usable by clients.
# ---------------------------------------------------------------------------

class TestClientRoleBlocksNewWriteTools:

    @pytest.fixture
    def client_world(self, db, world):
        client = User(username="client", email="cl@x.io",
                      hashed_password="x", is_active=True)
        db.add(client)
        db.flush()
        db.add(OrganizationMember(
            organization_id=world["org_a"].id,
            user_id=client.id,
            role="CLIENT",
            linked_creator_id=world["creator_a"].id,
        ))
        db.commit()
        return client

    @pytest.mark.parametrize("tool,args", [
        ("mark_song_released", {"song_id": 1}),
        ("update_song_metadata", {"song_id": 1, "title": "X"}),
        ("assign_action_item", {"action_item_id": 1, "assignee_user_id": 1}),
        ("add_song_credit", {"song_id": 1, "creator_id": 1, "role": "WRITER"}),
        ("record_payment", {"payee_id": 1, "amount_cents": 100}),
    ])
    def test_client_blocked(self, db, world, client_world, tool, args):
        out = assistant_tools.dispatch_tool(
            tool, args,
            db=db, org_id=world["org_a"].id,
            user_id=client_world.id,
            user_role="CLIENT",
            linked_creator_id=world["creator_a"].id,
        )
        assert "error" in out
