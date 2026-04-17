"""Regression tests for Task #57 — BMI artist extraction & matching.

These tests cover the two pieces of fix logic that prevent statement
parsing junk (e.g. ``50.0%`` ending up in ``artist_name_raw``) from
demoting exact title matches into REVIEW_REQUIRED.
"""
import re
from unittest.mock import MagicMock
from difflib import SequenceMatcher


def _clean_artist(val):
    """Mirror of clean_artist() inside parse_statement_to_lines."""
    if val is None:
        return None
    s = str(val).strip()
    if not s:
        return None
    if not re.search(r"[A-Za-z]", s):
        return None
    stripped = s.replace(",", "").replace("$", "").replace("%", "").strip()
    if stripped and re.fullmatch(r"-?\d+(?:\.\d+)?", stripped):
        return None
    return s


def test_clean_artist_rejects_percentage():
    assert _clean_artist("50.0%") is None
    assert _clean_artist("100%") is None
    assert _clean_artist(" 12.5 % ") is None


def test_clean_artist_rejects_digits_currency_dashes():
    assert _clean_artist("1234") is None
    assert _clean_artist("$5,000.00") is None
    assert _clean_artist("--") is None
    assert _clean_artist("") is None
    assert _clean_artist(None) is None


def test_clean_artist_keeps_real_names():
    assert _clean_artist("Smith, John") == "Smith, John"
    assert _clean_artist("blink-182") == "blink-182"
    assert _clean_artist("100 gecs") == "100 gecs"
    assert _clean_artist("M.A.N.") == "M.A.N."


def _fuzzy_score(line_title, raw_artist, song_title, song_artist):
    """Mirror of the fuzzy score branch in auto_match_lines."""
    line_title = (line_title or "").lower().strip()
    raw_artist = (raw_artist or "").strip()
    if raw_artist and re.search(r"[A-Za-z]", raw_artist):
        line_artist = raw_artist.lower()
    else:
        line_artist = ""
    title_ratio = SequenceMatcher(None, line_title, (song_title or "").lower().strip()).ratio()
    if line_artist and song_artist:
        artist_ratio = SequenceMatcher(None, line_artist, song_artist.lower().strip()).ratio()
        return (title_ratio * 0.6) + (artist_ratio * 0.4)
    return title_ratio


def test_exact_title_with_junk_artist_clears_auto_match_threshold():
    # Bug repro: BMI line had artist_name_raw="50.00%" and an exact
    # title match. Old combined score = (1.0*0.6)+(low*0.4) ≈ 0.6 → REVIEW.
    # Fixed score = title-only = 1.0 → AUTO_MATCHED.
    score = _fuzzy_score(
        line_title="Deja Vu",
        raw_artist="50.00%",
        song_title="Deja Vu",
        song_artist="Olivia Rodrigo",
    )
    assert score >= 0.8, f"expected ≥0.8 (AUTO_MATCHED band), got {score}"
    assert score == 1.0


def test_exact_title_with_blank_artist_clears_auto_match_threshold():
    score = _fuzzy_score(
        line_title="Vampire",
        raw_artist=None,
        song_title="Vampire",
        song_artist="Olivia Rodrigo",
    )
    assert score >= 0.8


def test_real_artist_still_combined():
    score = _fuzzy_score(
        line_title="Deja Vu",
        raw_artist="Olivia Rodrigo",
        song_title="Deja Vu",
        song_artist="Olivia Rodrigo",
    )
    assert score == 1.0


def test_column_mapping_does_not_steal_writer_share_for_artist():
    from backend.routes.royalties import suggest_column_mapping
    headers = ["Work Title", "Writer", "Writer Share %", "Royalty Amount"]
    mapping = suggest_column_mapping(headers, source_type="BMI Statement")
    assert mapping["artist"] == "Writer", mapping
    # Writer Share % must NOT end up as the artist column.
    assert mapping["artist"] != "Writer Share %"
    # And revenue must not steal the share % column either.
    assert mapping["revenue"] != "Writer Share %"
