"""Phase 3 — Task #170 — uniform statement-ingestion tests.

Covers:
- Confidence-scored column auto-mapper (BMI/ASCAP/MLC/Label fixtures).
- ISRC takes priority over title in the auto-mapper's identifier
  selection.
- Amount normalizer handles ``$1,234.56`` / ``1234.56`` / ``(123.45)``
  / cents-style integer strings.
- Period cadence accessor returns the canonical cadence per source.
- Phase 1 dedup guard (``compute_line_hash``) is stable across
  identical rows and changes when any meaningful field changes.
"""
from __future__ import annotations

import os

import pytest

from backend.config.statement_formats import (
    SOURCE_FORMAT_REGISTRY,
    canonical_source_type,
    get_format_spec,
)
from backend.services.statement_column_mapper import (
    auto_map_columns,
    CANONICAL_FIELDS,
)
from backend.routes.royalties import parse_revenue_to_cents
from backend.services.royalty_processing_engine import compute_line_hash


FIXTURES_DIR = os.path.join(
    os.path.dirname(__file__), "..", "..", "mock_data", "statements"
)


# ---------------------------------------------------------------------------
# Column mapper
# ---------------------------------------------------------------------------

def test_bmi_headers_map_with_high_confidence():
    headers = [
        "BMI Work#", "Work Title", "ISRC", "Affiliated Writer",
        "Source", "Survey Type", "Performance Count",
        "Current Activity Royalty",
    ]
    result = auto_map_columns(headers, "BMI")
    assert result["track_title"] == "Work Title"
    assert result["isrc"] == "ISRC"
    assert result["revenue"] == "Current Activity Royalty"
    assert result["quantity"] == "Performance Count"
    assert result["work_id"] == "BMI Work#"
    assert result["_confident"] is True
    assert result["_confidence"] >= 0.8


def test_ascap_headers_map_with_high_confidence():
    headers = [
        "ASCAP Work ID", "Work Title", "Writer/Publisher",
        "Performance Type", "Credits", "Domestic Amount",
        "Foreign Amount",
    ]
    result = auto_map_columns(headers, "ASCAP")
    assert result["track_title"] == "Work Title"
    assert result["work_id"] == "ASCAP Work ID"
    # Either Domestic or Foreign Amount may win for "revenue" — both
    # are valid registry aliases. Just assert one of them matched.
    assert result["revenue"] in ("Domestic Amount", "Foreign Amount")
    assert result["_confident"] is True


def test_mlc_headers_map_with_high_confidence():
    headers = [
        "ISRC", "HFA Song Code", "Song Title", "Performer",
        "Service", "Streams", "Royalty Amount",
    ]
    result = auto_map_columns(headers, "MLC")
    assert result["isrc"] == "ISRC"
    assert result["track_title"] == "Song Title"
    assert result["revenue"] == "Royalty Amount"
    assert result["quantity"] == "Streams"
    assert result["_confident"] is True


def test_label_headers_map_with_high_confidence():
    headers = [
        "ISRC", "UPC", "Track", "Primary Artist", "Channel",
        "Configuration", "Territory", "Units Sold", "Net Royalty",
    ]
    result = auto_map_columns(headers, "LABEL")
    assert result["isrc"] == "ISRC"
    assert result["upc"] == "UPC"
    assert result["track_title"] == "Track"
    assert result["revenue"] == "Net Royalty"
    assert result["territory"] == "Territory"
    assert result["_confident"] is True


def test_garbage_headers_are_not_confident():
    headers = ["alpha", "beta", "gamma", "delta"]
    result = auto_map_columns(headers, None)
    assert result["_confident"] is False
    # Every header should land in _unmapped because no aliases match.
    assert set(result["_unmapped"]) == set(headers)


def test_generic_two_column_file_is_not_confident():
    """Anti-poison guard: ``["work","amount"]`` technically has a
    title-ish header and an amount-ish header, but with no
    identifier / artist / quantity / territory / platform it could
    be any random spreadsheet. Mapper must NOT call this confident."""
    result = auto_map_columns(["work", "amount"], None)
    assert result["_confident"] is False, (
        "two generic single-token columns should never be confident; "
        f"got {result}"
    )


def test_minimal_real_statement_is_confident():
    """Adding a single real signal column (artist, ISRC, territory…)
    is enough to flip a generic title+amount file into 'confident'."""
    result = auto_map_columns(["title", "artist", "amount"], None)
    assert result["_confident"] is True
    assert result["track_title"] == "title"
    assert result["artist"] == "artist"
    assert result["revenue"] == "amount"


def test_isrc_takes_priority_when_both_isrc_and_title_present():
    """When both ISRC and title columns are present and equally
    confident, the mapper must surface ISRC as the primary
    identifier (track_matcher will then prefer it over fuzzy title)."""
    headers = ["ISRC", "Track Title", "Net Amount"]
    result = auto_map_columns(headers, "DSP")
    # Both should be mapped, but ISRC must be present as the
    # canonical identifier so the downstream matcher can use it.
    assert result["isrc"] == "ISRC"
    assert result["track_title"] == "Track Title"
    # Check that ISRC scored at least as well as title.
    scores = result["_field_scores"]
    assert scores.get("isrc", 0.0) >= scores.get("track_title", 0.0)


def test_one_header_cannot_be_claimed_by_two_fields():
    """Greedy assignment — if "title" matches both ``track_title``
    and (loosely) ``revenue_type``, it must only attach to one
    field."""
    headers = ["title", "amount"]
    result = auto_map_columns(headers, None)
    used = [v for k, v in result.items() if v and not k.startswith("_")]
    assert len(used) == len(set(used)), "no header should be claimed twice"


def test_unknown_source_type_falls_back_to_base_aliases():
    headers = ["Track Title", "ISRC", "Amount"]
    result = auto_map_columns(headers, "made-up-source-name")
    assert result["track_title"] == "Track Title"
    assert result["isrc"] == "ISRC"
    assert result["revenue"] == "Amount"
    assert result["_confident"] is True


# ---------------------------------------------------------------------------
# Amount normalizer
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("value, expected_cents", [
    ("$1,234.56", 123456),
    ("1234.56", 123456),
    ("1,234.56", 123456),
    ("$0.00", 0),
    ("0", 0),
    ("(123.45)", -12345),  # parens = negative, common in label statements
    ("-12.50", -1250),
    ("£42.10", 4210),
    ("€100.00", 10000),
    ("", 0),
    ("-", 0),
    (None, 0),
])
def test_parse_revenue_to_cents_handles_varied_formats(value, expected_cents):
    assert parse_revenue_to_cents(value) == expected_cents


def test_normalize_rows_for_amount_format_cents():
    """Direct unit test of the shared cents-format helper used by
    both ``parse_statement`` AND ``upload_statement``."""
    from backend.config import statement_formats as sf
    from backend.services.statement_parser import normalize_rows_for_amount_format

    rows = [
        {"ISRC": "USRC12345001", "Net Cents": "123456"},
        {"ISRC": "USRC12345002", "Net Cents": "7800"},
        {"ISRC": "USRC12345003", "Net Cents": "(2500)"},   # parens = negative
        {"ISRC": "USRC12345004", "Net Cents": ""},         # empty pass-through
    ]
    mapping = {"isrc": "ISRC", "revenue": "Net Cents"}

    original_registry = sf.SOURCE_FORMAT_REGISTRY
    original_aliases = sf._SOURCE_TYPE_ALIASES
    sf.SOURCE_FORMAT_REGISTRY = dict(original_registry)
    sf.SOURCE_FORMAT_REGISTRY["TEST_CENTS_SOURCE"] = {
        "label": "Test Cents Source",
        "default_currency": "USD",
        "period_cadence": "monthly",
        "amount_format": "cents",
        "identifier_fields": ["isrc"],
        "extra_hints": {"revenue": ["net cents"]},
    }
    sf._SOURCE_TYPE_ALIASES = dict(original_aliases)
    sf._SOURCE_TYPE_ALIASES["test_cents_source"] = "TEST_CENTS_SOURCE"
    try:
        out = normalize_rows_for_amount_format(rows, mapping, "TEST_CENTS_SOURCE")
    finally:
        sf.SOURCE_FORMAT_REGISTRY = original_registry
        sf._SOURCE_TYPE_ALIASES = original_aliases

    assert out[0]["Net Cents"] == "1234.56"
    assert out[1]["Net Cents"] == "78.00"
    assert out[2]["Net Cents"] == "-25.00"
    assert out[3]["Net Cents"] == ""  # untouched


def test_normalize_rows_for_amount_format_dollars_passthrough():
    """Dollar-format sources (every entry in the registry today) must
    be returned unchanged so existing ingestion is never disturbed."""
    from backend.services.statement_parser import normalize_rows_for_amount_format

    rows = [
        {"ISRC": "USRC12345001", "Net Amount": "$1,234.56"},
        {"ISRC": "USRC12345002", "Net Amount": "78.00"},
    ]
    mapping = {"isrc": "ISRC", "revenue": "Net Amount"}

    out = normalize_rows_for_amount_format(rows, mapping, "BMI")  # BMI = dollars
    assert out is rows  # same object: no copy when no-op


def test_cents_amount_format_persists_correct_total_revenue(tmp_path):
    """End-to-end persistence test: register a cents-format source,
    run ``parse_statement`` with a SQLite session, and assert the
    ``RoyaltyStatement.total_revenue_cents`` written to the DB matches
    the expected sum of the integer cents values in the file.

    Without the cents pre-division this would be off by 100x — the
    dollar-style parser would interpret ``"123456"`` as $123,456.00.
    """
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from backend.config import statement_formats as sf
    from backend.models.database import Base
    from backend.models.models import (
        Organization, User, RoyaltyStatement,
    )
    from backend.services.statement_parser import parse_statement

    csv_path = tmp_path / "cents_source.csv"
    csv_path.write_text(
        "ISRC,Track Title,Artist,Net Cents\n"
        "USRC12345001,Midnight Dreams,Luna Rivers,123456\n"
        "USRC12345002,Electric Pulse,Luna Rivers,7800\n",
        encoding="utf-8",
    )

    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    db = Session()

    # Minimal fixtures so the FK constraints are satisfied.
    org = Organization(name="Cents Test Org")
    db.add(org)
    db.flush()
    user = User(
        username="cents_test", email="cents@test.local",
        hashed_password="x",
    )
    db.add(user)
    db.flush()

    original_registry = sf.SOURCE_FORMAT_REGISTRY
    original_aliases = sf._SOURCE_TYPE_ALIASES
    sf.SOURCE_FORMAT_REGISTRY = dict(original_registry)
    sf.SOURCE_FORMAT_REGISTRY["TEST_CENTS_SOURCE"] = {
        "label": "Test Cents Source",
        "default_currency": "USD",
        "period_cadence": "monthly",
        "amount_format": "cents",
        "identifier_fields": ["isrc"],
        "extra_hints": {"revenue": ["net cents"]},
    }
    sf._SOURCE_TYPE_ALIASES = dict(original_aliases)
    sf._SOURCE_TYPE_ALIASES["test_cents_source"] = "TEST_CENTS_SOURCE"
    try:
        result = parse_statement(
            file_path=str(csv_path),
            source_type="TEST_CENTS_SOURCE",
            org_id=org.id,
            db_session=db,
            uploaded_by_user_id=user.id,
            auto_match=False,
        )
    finally:
        sf.SOURCE_FORMAT_REGISTRY = original_registry
        sf._SOURCE_TYPE_ALIASES = original_aliases

    assert result["statement_id"] is not None, f"expected persisted statement; got {result}"
    assert result["total_lines"] == 2
    # 123456 cents + 7800 cents = 131256 cents = $1,312.56
    expected_total_cents = 123456 + 7800
    assert result["total_revenue_cents"] == expected_total_cents, (
        f"expected {expected_total_cents}; got {result['total_revenue_cents']}"
    )
    stmt = db.query(RoyaltyStatement).filter_by(id=result["statement_id"]).one()
    assert stmt.total_revenue_cents == expected_total_cents
    db.close()


# ---------------------------------------------------------------------------
# Format registry / period cadence
# ---------------------------------------------------------------------------

def test_format_spec_returns_period_cadence_per_source():
    assert get_format_spec("BMI")["period_cadence"] == "quarterly"
    assert get_format_spec("MLC")["period_cadence"] == "monthly"
    assert get_format_spec("LABEL")["period_cadence"] == "semi-annual"
    assert get_format_spec("DSP")["period_cadence"] == "monthly"


def test_format_spec_declares_amount_format_and_identifiers():
    """Phase 3 added ``amount_format`` and ``identifier_fields`` to
    every registry entry. Regression-guard: nothing was missed."""
    for source_type, spec in SOURCE_FORMAT_REGISTRY.items():
        assert "amount_format" in spec, f"{source_type} missing amount_format"
        assert spec["amount_format"] in ("dollars", "cents")
        assert "identifier_fields" in spec, f"{source_type} missing identifier_fields"
        assert isinstance(spec["identifier_fields"], list)
        assert len(spec["identifier_fields"]) >= 1


def test_canonical_source_type_aliases():
    assert canonical_source_type("bmi") == "BMI"
    assert canonical_source_type("Harry Fox") == "HARRY_FOX"
    assert canonical_source_type("the mlc") == "MLC"
    assert canonical_source_type("Sound Exchange") == "SOUNDEXCHANGE"
    assert canonical_source_type("") is None
    assert canonical_source_type("totally made up") is None


# ---------------------------------------------------------------------------
# Phase 1 dedup guard — line hash stability
# ---------------------------------------------------------------------------

def test_compute_line_hash_is_stable_for_identical_rows():
    row = {
        "isrc": "USRC12345001",
        "track_title": "Midnight Dreams",
        "artist": "Luna Rivers",
        "revenue": "412.55",
        "territory": "US",
        "store": "Spotify",
        "revenue_type": "Streaming",
        "quantity": "184201",
        "row_index": "0",
    }
    assert compute_line_hash(row) == compute_line_hash(dict(row))


def test_compute_line_hash_differs_when_any_field_changes():
    base = {
        "isrc": "USRC12345001",
        "track_title": "Midnight Dreams",
        "artist": "Luna Rivers",
        "revenue": "412.55",
        "territory": "US",
        "store": "Spotify",
        "revenue_type": "Streaming",
        "quantity": "184201",
        "row_index": "0",
    }
    base_hash = compute_line_hash(base)
    for field in ("isrc", "track_title", "revenue", "territory", "store", "row_index"):
        mutated = dict(base)
        mutated[field] = (mutated[field] or "") + "_X"
        assert compute_line_hash(mutated) != base_hash, (
            f"hash should change when {field} changes"
        )


def test_compute_line_hash_normalizes_case_and_whitespace():
    row_a = {
        "isrc": "usrc12345001",
        "track_title": "  Midnight DREAMS  ",
        "artist": "luna rivers",
        "revenue": "412.55",
        "territory": "us",
        "store": "spotify",
        "revenue_type": "streaming",
        "quantity": "184201",
        "row_index": "0",
    }
    row_b = {
        "isrc": "USRC12345001",
        "track_title": "Midnight Dreams",
        "artist": "Luna Rivers",
        "revenue": "412.55",
        "territory": "US",
        "store": "Spotify",
        "revenue_type": "Streaming",
        "quantity": "184201",
        "row_index": "0",
    }
    assert compute_line_hash(row_a) == compute_line_hash(row_b)


# ---------------------------------------------------------------------------
# Mock fixtures sanity check — auto_map_columns against the real CSVs
# ---------------------------------------------------------------------------

def _read_headers(filename: str) -> list[str]:
    import csv
    path = os.path.join(FIXTURES_DIR, filename)
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        return next(reader)


@pytest.mark.parametrize("filename, source_type", [
    ("bmi_q4_2025.csv", "BMI"),
    ("ascap_q4_2025.csv", "ASCAP"),
    ("mlc_dec_2025.csv", "MLC"),
    ("label_h2_2025.csv", "LABEL"),
])
def test_phase3_fixture_headers_map_confidently(filename, source_type):
    headers = _read_headers(filename)
    result = auto_map_columns(headers, source_type)
    assert result["_confident"] is True, (
        f"{filename}: mapper should be confident ({result['_confidence']:.2f}); "
        f"got mapping={ {k: v for k, v in result.items() if v and not k.startswith('_')} }"
    )
    # Either ISRC or title plus a revenue field must be present for
    # downstream parse_statement_to_lines to extract any revenue.
    assert result.get("revenue") is not None
    assert result.get("isrc") or result.get("track_title")


# ---------------------------------------------------------------------------
# parse_statement summary metrics without persistence (db_session=None)
# ---------------------------------------------------------------------------

def test_parse_statement_returns_summary_without_db_session(tmp_path):
    """Without a session, ``parse_statement`` still computes a real
    parse summary — total_lines, total_revenue_cents, unmatched —
    by walking the parsed rows. This is the contract dry-run
    callers (validators, the wizard preview step) rely on.
    """
    from backend.services.statement_parser import parse_statement

    csv_path = tmp_path / "preview.csv"
    csv_path.write_text(
        "ISRC,Title,Artist,Net Revenue\n"
        "USRC12345001,Midnight Dreams,Luna Rivers,1234.56\n"
        "USRC12345002,Electric Pulse,Luna Rivers,78.00\n"
        "USRC12345003,Foreign Track,Other,(25.00)\n",
        encoding="utf-8",
    )

    result = parse_statement(
        file_path=str(csv_path),
        source_type="DSP",
        org_id=None,
        db_session=None,
    )

    assert result["statement_id"] is None
    assert result["total_lines"] == 3
    # 1234.56 + 78.00 + (-25.00) = 1287.56 -> 128756 cents
    assert result["total_revenue_cents"] == 128756, (
        f"expected 128756 cents; got {result['total_revenue_cents']}"
    )
    # Without a session there's no catalog to match against, so every
    # row is reported as unmatched.
    assert result["matched"] == 0
    assert result["unmatched"] == 3
    assert result["confident"] is True
    assert result["column_mapping"].get("isrc")
    assert result["column_mapping"].get("revenue")


def test_parse_statement_no_session_with_cents_format_normalizes_revenue(tmp_path):
    """Same dry-run path, but for a cents-format source: the summary
    must still divide by 100 before reporting total_revenue_cents.
    """
    from backend.config import statement_formats as sf
    from backend.services.statement_parser import parse_statement

    csv_path = tmp_path / "cents_preview.csv"
    csv_path.write_text(
        "ISRC,Track Title,Artist,Net Cents\n"
        "USRC12345001,Midnight Dreams,Luna Rivers,123456\n"
        "USRC12345002,Electric Pulse,Luna Rivers,7800\n",
        encoding="utf-8",
    )

    original_registry = sf.SOURCE_FORMAT_REGISTRY
    original_aliases = sf._SOURCE_TYPE_ALIASES
    sf.SOURCE_FORMAT_REGISTRY = dict(original_registry)
    sf.SOURCE_FORMAT_REGISTRY["TEST_CENTS_DRY_RUN"] = {
        "label": "Test Cents Dry-Run",
        "default_currency": "USD",
        "period_cadence": "monthly",
        "amount_format": "cents",
        "identifier_fields": ["isrc"],
        "extra_hints": {"revenue": ["net cents"]},
    }
    sf._SOURCE_TYPE_ALIASES = dict(original_aliases)
    sf._SOURCE_TYPE_ALIASES["test_cents_dry_run"] = "TEST_CENTS_DRY_RUN"
    try:
        result = parse_statement(
            file_path=str(csv_path),
            source_type="TEST_CENTS_DRY_RUN",
            db_session=None,
        )
    finally:
        sf.SOURCE_FORMAT_REGISTRY = original_registry
        sf._SOURCE_TYPE_ALIASES = original_aliases

    assert result["total_lines"] == 2
    assert result["total_revenue_cents"] == 123456 + 7800


# ---------------------------------------------------------------------------
# Period extraction from filename (monthly / quarterly / semi-annual / annual)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("filename,expected_start,expected_end,expected_cadence", [
    # Quarterly variants
    ("bmi_q4_2025.csv",          "2025-10-01", "2025-12-31", "quarterly"),
    ("ascap_2024_q1.csv",        "2024-01-01", "2024-03-31", "quarterly"),
    ("ascap-q2-2025.xlsx",       "2025-04-01", "2025-06-30", "quarterly"),
    # Monthly variants
    ("mlc_dec_2025.csv",         "2025-12-01", "2025-12-31", "monthly"),
    ("dsp_2024_03.csv",          "2024-03-01", "2024-03-31", "monthly"),
    ("platform_2025-07_payout.csv", "2025-07-01", "2025-07-31", "monthly"),
    ("statement_jul_2024.csv",   "2024-07-01", "2024-07-31", "monthly"),
    # Semi-annual
    ("label_h2_2025.csv",        "2025-07-01", "2025-12-31", "semi-annual"),
    ("warner_h1_2024.csv",       "2024-01-01", "2024-06-30", "semi-annual"),
])
def test_infer_period_from_filename_extracts_real_periods(
    filename, expected_start, expected_end, expected_cadence,
):
    from datetime import date
    from backend.services.statement_parser import infer_period_from_filename

    result = infer_period_from_filename(filename)
    assert result is not None, f"{filename}: expected a period"
    assert result["period_start"] == date.fromisoformat(expected_start)
    assert result["period_end"] == date.fromisoformat(expected_end)
    assert result["cadence"] == expected_cadence


def test_infer_period_from_filename_falls_back_to_registry_cadence_for_bare_year():
    from datetime import date
    from backend.services.statement_parser import infer_period_from_filename

    # SOUNDEXCHANGE registry cadence is "quarterly", so even when the
    # filename only carries a year, the helper still returns the
    # right cadence per source.
    result = infer_period_from_filename("soundexchange_2024.csv", "SOUNDEXCHANGE")
    assert result is not None
    assert result["period_start"] == date(2024, 1, 1)
    assert result["period_end"] == date(2024, 12, 31)
    assert result["cadence"] in ("quarterly", "annual")


def test_infer_period_from_filename_returns_none_when_no_year():
    from backend.services.statement_parser import infer_period_from_filename
    assert infer_period_from_filename("just_some_random_file.csv") is None
    assert infer_period_from_filename("") is None


# ---------------------------------------------------------------------------
# Identifier-priority matching: ISWC beats fuzzy title
# ---------------------------------------------------------------------------

def test_iswc_takes_priority_over_fuzzy_title_in_auto_match(tmp_path):
    """When a statement line carries an ISWC, ``auto_match_lines``
    must resolve via the song-level ISWC index BEFORE falling back to
    fuzzy title matching, even when the title is a near-perfect match
    for a different song in the catalog.
    """
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from backend.models.database import Base
    from backend.models.models import (
        Organization, RoyaltyStatement, RoyaltyStatementLine, Song,
    )
    from backend.services.royalty_processing_engine import auto_match_lines

    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    db = Session()

    org = Organization(name="ISWC Priority Org")
    db.add(org); db.flush()

    # Song A: matches the line by ISWC, but its title is very different.
    song_iswc = Song(
        organization_id=org.id, title="Completely Different Title",
        primary_artist="Artist A",
        iswc="T-123.456.789-0",
    )
    # Song B: matches the line by title fuzzy >0.95, but no ISWC.
    song_fuzzy = Song(
        organization_id=org.id, title="Midnight Dreamz",  # near-match for "Midnight Dreams"
        primary_artist="Artist B",
    )
    db.add_all([song_iswc, song_fuzzy]); db.flush()

    stmt = RoyaltyStatement(
        organization_id=org.id, source_name="MLC", source_type="MLC",
        currency="USD", file_name="mlc_dec_2025.csv", status="PROCESSING",
    )
    db.add(stmt); db.flush()

    # Punctuation in the line ISWC differs from the song's stored
    # ISWC ("T1234567890" vs "T-123.456.789-0") — the matcher must
    # normalize both sides before lookup.
    line = RoyaltyStatementLine(
        org_id=org.id, statement_id=stmt.id,
        track_title_raw="Midnight Dreams",
        iswc="T1234567890",
        net_amount=10.0, net_amount_statement_currency=10.0,
        currency="USD", match_status="UNMATCHED",
    )
    db.add(line); db.flush()

    stats = auto_match_lines(db, stmt.id, org.id)
    db.refresh(line)

    assert stats["auto_matched"] == 1
    assert line.match_method == "ISWC"
    assert line.matched_song_id == song_iswc.id, (
        f"expected ISWC match to win over fuzzy; got song_id={line.matched_song_id} "
        f"(ISWC song={song_iswc.id}, fuzzy song={song_fuzzy.id})"
    )
    assert line.match_confidence == 100.0
    db.close()


def test_iswc_work_level_match_resolves_to_first_recorded_song(tmp_path):
    """When the ISWC is registered on a Work (composition) rather
    than directly on a Song (recording), the matcher resolves via the
    WorkTrack link and surfaces the work_id alongside the resolved
    song_id under match_method ``ISWC_WORK``.
    """
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from backend.models.database import Base
    from backend.models.models import (
        Organization, RoyaltyStatement, RoyaltyStatementLine, Song,
        Work, WorkTrack,
    )
    from backend.services.royalty_processing_engine import auto_match_lines

    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    db = Session()

    org = Organization(name="Work ISWC Org")
    db.add(org); db.flush()

    song = Song(organization_id=org.id, title="Some Recording", primary_artist="Some Artist")
    db.add(song); db.flush()

    work = Work(organization_id=org.id, title="The Underlying Composition", iswc="T-987.654.321-0")
    db.add(work); db.flush()

    db.add(WorkTrack(work_id=work.id, song_id=song.id)); db.flush()

    stmt = RoyaltyStatement(
        organization_id=org.id, source_name="HARRY_FOX", source_type="HARRY_FOX",
        currency="USD", file_name="hfa_2025.csv", status="PROCESSING",
    )
    db.add(stmt); db.flush()

    line = RoyaltyStatementLine(
        org_id=org.id, statement_id=stmt.id,
        track_title_raw="something else entirely",
        iswc="T9876543210",
        net_amount=5.0, net_amount_statement_currency=5.0,
        currency="USD", match_status="UNMATCHED",
    )
    db.add(line); db.flush()

    stats = auto_match_lines(db, stmt.id, org.id)
    db.refresh(line)

    assert stats["auto_matched"] == 1
    assert line.match_method == "ISWC_WORK"
    assert line.matched_work_id == work.id
    assert line.matched_song_id == song.id
    db.close()
