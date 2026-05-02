"""Per-platform rate intelligence — Task #199 Phase 2.

Aggregates BMI line items by ``platform_source`` and computes:

- ``raw_rate_per_stream`` = royalty / count  (publisher's pocket per stream)
- ``effective_rate_per_stream`` = royalty / (count * writer_share_pct/100)
  (the platform's gross publishing rate, normalized for ownership)

The effective rate is what we compare against expected industry bands;
two songs on Spotify with 25% vs 50% writer-share pay the SAME rate at
the platform level — the difference shows up only in the publisher's
take, not in what Spotify is paying out.

Returns a dict per platform with the aggregates plus a band flag
(``LOW`` / ``NORMAL`` / ``HIGH`` / ``NO_BENCHMARK``).
"""
from __future__ import annotations

import logging
from collections import defaultdict
from typing import Dict, List, Optional

from sqlalchemy.orm import Session

from ..models import RoyaltyStatementLine

logger = logging.getLogger(__name__)


# Expected effective publishing rate bands (cents per stream).
# Source: spec, Phase 2; aligned with PUBLISHING_RATE_PREMIUM (~$0.0012)
# in ``backend/config/streaming_rates.py`` but widened for tier variance.
EXPECTED_BANDS_CENTS: Dict[str, tuple[float, float]] = {
    "SPOTIFY": (0.05, 0.20),
    "APPLE": (0.10, 0.40),
    "AMAZON": (0.06, 0.25),
    "YOUTUBE": (0.02, 0.15),
    "PANDORA": (0.02, 0.10),
    "TIDAL": (0.10, 0.50),
    "DEEZER": (0.05, 0.20),
    "SOUNDCLOUD": (0.02, 0.15),
    "AUDIOMACK": (0.02, 0.10),
    "TIKTOK": (0.01, 0.10),
    "PELOTON": (0.05, 0.30),
    "FACEBOOK": (0.01, 0.10),
    "NAPSTER": (0.05, 0.30),
    "SIRIUSXM": (0.02, 0.20),
}


def _platform_root(source: str) -> str:
    """Spotify PREM, Spotify FREE, etc → SPOTIFY."""
    if not source:
        return ""
    s = source.strip().upper()
    if " " in s:
        return s.split(" ", 1)[0]
    return s


def compute_per_platform_rates(
    db: Session,
    org_id: int,
    statement_id: Optional[int] = None,
) -> Dict[str, Dict]:
    """Compute per-platform rate aggregates from BMI statement lines.

    Args:
        org_id: tenant scope.
        statement_id: optional — when given, restricts the aggregate to
            a single statement so the UI can show "rates from this file".

    Returns:
        ``{ "SPOTIFY PREM": { total_streams, total_royalty_cents,
            raw_rate_cents, effective_rate_cents, song_count,
            avg_writer_share, rate_flag } }``
    """
    q = db.query(
        RoyaltyStatementLine.platform_source,
        RoyaltyStatementLine.unit_count,
        RoyaltyStatementLine.net_amount,
        RoyaltyStatementLine.writer_share_pct,
        RoyaltyStatementLine.matched_song_id,
        RoyaltyStatementLine.bmi_work_number,
    ).filter(
        RoyaltyStatementLine.org_id == org_id,
        RoyaltyStatementLine.platform_source.isnot(None),
    )
    if statement_id is not None:
        q = q.filter(RoyaltyStatementLine.statement_id == statement_id)

    grouped: Dict[str, Dict] = defaultdict(lambda: {
        "total_streams": 0,
        "total_royalty_cents": 0,
        "writer_share_weighted": 0.0,
        "songs": set(),
    })

    for source, count, amt, share, song_id, work_no in q:
        if not source:
            continue
        bucket = grouped[source]
        if count and count > 0:
            bucket["total_streams"] += int(count)
            if share and share > 0:
                bucket["writer_share_weighted"] += float(share) * float(count)
        if amt:
            bucket["total_royalty_cents"] += int(round(float(amt) * 100))
        if song_id is not None:
            bucket["songs"].add(("song", song_id))
        elif work_no:
            bucket["songs"].add(("work", work_no))

    results: Dict[str, Dict] = {}
    for source, data in grouped.items():
        streams = data["total_streams"]
        royalty_cents = data["total_royalty_cents"]
        # Cents per stream, raw (publisher's pocket per stream).
        raw_rate_cents = (royalty_cents / streams) if streams > 0 else 0.0
        # Average writer share, stream-weighted.
        avg_share = (
            data["writer_share_weighted"] / streams
            if streams > 0 and data["writer_share_weighted"] > 0
            else 0.0
        )
        # Effective platform rate: gross-up the royalty by ownership %.
        effective_cents = 0.0
        if streams > 0 and avg_share > 0:
            effective_cents = (royalty_cents / streams) / (avg_share / 100.0)
        elif raw_rate_cents > 0:
            effective_cents = raw_rate_cents

        platform = _platform_root(source)
        band = EXPECTED_BANDS_CENTS.get(platform)
        if band:
            lo, hi = band
            # Spec taxonomy: CRITICALLY_LOW (< 50% of band floor), LOW
            # (between 50% and floor), NORMAL (in band), UNUSUALLY_HIGH
            # (> 1.5× band ceiling), HIGH (between ceiling and 1.5×).
            if effective_cents < lo * 0.5:
                flag = "CRITICALLY_LOW"
            elif effective_cents < lo:
                flag = "LOW"
            elif effective_cents > hi * 1.5:
                flag = "UNUSUALLY_HIGH"
            elif effective_cents > hi:
                flag = "HIGH"
            else:
                flag = "NORMAL"
        else:
            flag = "NO_BENCHMARK"

        results[source] = {
            "platform": platform,
            "total_streams": streams,
            "total_royalty_cents": royalty_cents,
            "total_royalty_dollars": round(royalty_cents / 100.0, 2),
            "raw_rate_cents_per_stream": round(raw_rate_cents, 5),
            "effective_rate_cents_per_stream": round(effective_cents, 5),
            "avg_writer_share_pct": round(avg_share, 2),
            "song_count": len(data["songs"]),
            "rate_flag": flag,
            "expected_band_cents": band,
        }

    return results


def compute_statement_validation(
    db: Session,
    org_id: int,
    statement_id: int,
) -> Dict:
    """Stated-vs-computed reconciliation card for a single statement.

    Pulls the stored ``parse_quality`` off any one line (they're all
    identical for a given statement) plus the statement's stored grand
    total vs the SUM of line ``net_amount``.
    """
    from ..models import RoyaltyStatement
    from sqlalchemy import func as _f

    stmt = db.query(RoyaltyStatement).filter(
        RoyaltyStatement.id == statement_id,
        RoyaltyStatement.organization_id == org_id,
    ).first()
    if not stmt:
        return {}

    summed_cents = (
        db.query(_f.coalesce(_f.sum(RoyaltyStatementLine.net_amount), 0.0))
        .filter(
            RoyaltyStatementLine.org_id == org_id,
            RoyaltyStatementLine.statement_id == statement_id,
        )
        .scalar()
    )
    summed_cents = int(round(float(summed_cents or 0.0) * 100))

    quality = (
        db.query(RoyaltyStatementLine.parse_quality)
        .filter(
            RoyaltyStatementLine.org_id == org_id,
            RoyaltyStatementLine.statement_id == statement_id,
            RoyaltyStatementLine.parse_quality.isnot(None),
        )
        .first()
    )

    stated = stmt.total_revenue_cents or 0
    delta = summed_cents - stated

    # Task #199 — pull the per-section subtotals, parse warnings, and
    # unparsed-line count out of reconciliation_details where the
    # BMI v2 ingestion path stores them.
    bmi_meta = {}
    recon = stmt.reconciliation_details or {}
    if isinstance(recon, dict):
        bmi_meta = recon.get("bmi_parser") or {}

    section_totals_dollars = bmi_meta.get("section_totals") or {}
    section_totals_cents = {
        str(k): int(round(float(v) * 100))
        for k, v in section_totals_dollars.items()
    }

    return {
        "statement_id": statement_id,
        "stated_total_cents": stated,
        "computed_total_cents": summed_cents,
        "delta_cents": delta,
        "delta_pct": (
            abs(delta) / stated if stated else 0.0
        ),
        "parse_quality": float(quality[0]) if quality and quality[0] is not None else None,
        "parser": bmi_meta.get("parser"),
        "section_totals_cents": section_totals_cents,
        "parse_warnings": bmi_meta.get("parse_warnings") or [],
        "unparsed_lines_count": int(bmi_meta.get("unparsed_lines_count") or 0),
        "us_total_cents": (
            int(round(float(bmi_meta["us_total"]) * 100))
            if bmi_meta.get("us_total") is not None else None
        ),
        "admin_total_cents": (
            int(round(float(bmi_meta["admin_total"]) * 100))
            if bmi_meta.get("admin_total") is not None else None
        ),
        "intl_total_cents": (
            int(round(float(bmi_meta["intl_total"]) * 100))
            if bmi_meta.get("intl_total") is not None else None
        ),
    }
