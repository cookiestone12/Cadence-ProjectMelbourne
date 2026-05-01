"""Royalty Audit Engine — Task #173 (A+ Phase 6).

Four discrepancy/anomaly checks that scan a tenant's royalty data and
persist findings into ``royalty_audits`` so the Audit page can list
them, sort by severity, and let an analyst resolve each one.

Checks
------
1. ``CROSS_STATEMENT`` — same (song, period) appears on multiple
   statements with mismatched net amounts. Flags potential duplicate
   billing or partial reports.
2. ``RATE_CHECK`` — per-stream payout from a statement line falls
   meaningfully below the platform's expected master/publishing rate
   from ``backend/config/streaming_rates.py``.
3. ``MISSING_PERIOD`` — a song that historically reported every
   quarter has skipped one or more recent quarters.
4. ``DECAY_ANOMALY`` — observed net for the latest period diverges
   meaningfully from the exponential-decay fit produced by
   ``decay_analytics_engine.fit_exponential_decay``.

The engine is idempotent at the (audit_type, song_id, period_start,
period_end) granularity: re-running a scan updates an existing open
finding rather than duplicating it.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from datetime import date, datetime, timedelta
from typing import Dict, List, Optional, Tuple

from sqlalchemy.orm import Session

from ..config.streaming_rates import (
    MASTER_RATES,
    PUBLISHING_RATE_PREMIUM,
)
from ..models import (
    RoyaltyAudit,
    RoyaltyStatement,
    RoyaltyStatementLine,
    Song,
)
from . import decay_analytics_engine

log = logging.getLogger(__name__)


# ----- Severity helpers ----------------------------------------------------

def _severity_from_pct(pct: float) -> str:
    """Map an absolute % delta into a severity bucket."""
    if pct >= 50:
        return "CRITICAL"
    if pct >= 25:
        return "HIGH"
    if pct >= 10:
        return "MEDIUM"
    return "LOW"


def _upsert_audit(
    db: Session,
    org_id: int,
    audit_type: str,
    severity: str,
    description: str,
    *,
    song_id: Optional[int] = None,
    statement_id: Optional[int] = None,
    expected_cents: Optional[int] = None,
    actual_cents: Optional[int] = None,
    discrepancy_cents: Optional[int] = None,
    period_start: Optional[date] = None,
    period_end: Optional[date] = None,
    details: Optional[dict] = None,
    dedup_key: Optional[str] = None,
) -> RoyaltyAudit:
    """Insert-or-update an unresolved finding for the same logical key.

    `dedup_key` is an optional discriminator stored under
    ``details['dedup_key']`` so that checks emitting multiple distinct
    findings for the same (song, period) pair (e.g. RATE_CHECK with
    different (store, usage_type) combos) don't collapse onto each other.
    """
    if dedup_key is not None:
        details = {**(details or {}), "dedup_key": dedup_key}

    q = db.query(RoyaltyAudit).filter(
        RoyaltyAudit.organization_id == org_id,
        RoyaltyAudit.audit_type == audit_type,
        RoyaltyAudit.resolved.is_(False),
    )
    if song_id is not None:
        q = q.filter(RoyaltyAudit.song_id == song_id)
    else:
        q = q.filter(RoyaltyAudit.song_id.is_(None))
    if period_start is not None:
        q = q.filter(RoyaltyAudit.period_start == period_start)
    if period_end is not None:
        q = q.filter(RoyaltyAudit.period_end == period_end)
    candidates = q.all()
    if dedup_key is not None:
        existing = next(
            (c for c in candidates if (c.details or {}).get("dedup_key") == dedup_key),
            None,
        )
    else:
        existing = candidates[0] if candidates else None

    if existing:
        existing.severity = severity
        existing.description = description
        existing.expected_cents = expected_cents
        existing.actual_cents = actual_cents
        existing.discrepancy_cents = discrepancy_cents
        existing.statement_id = statement_id
        existing.details = details
        existing.updated_at = datetime.utcnow()
        return existing

    audit = RoyaltyAudit(
        organization_id=org_id,
        song_id=song_id,
        statement_id=statement_id,
        audit_type=audit_type,
        severity=severity,
        expected_cents=expected_cents,
        actual_cents=actual_cents,
        discrepancy_cents=discrepancy_cents,
        period_start=period_start,
        period_end=period_end,
        description=description,
        details=details or {},
    )
    db.add(audit)
    return audit


# ----- Check 1: Cross-statement reconciliation -----------------------------

def check_cross_statement(db: Session, org_id: int) -> List[RoyaltyAudit]:
    """Flag the same (song, period) appearing on two+ statements with
    mismatched net totals. Tolerance: 5% or $5, whichever is greater."""
    findings: List[RoyaltyAudit] = []

    rows = (
        db.query(
            RoyaltyStatementLine.matched_song_id,
            RoyaltyStatementLine.activity_period_start,
            RoyaltyStatementLine.activity_period_end,
            RoyaltyStatementLine.statement_id,
            RoyaltyStatementLine.net_amount,
        )
        .filter(
            RoyaltyStatementLine.org_id == org_id,
            RoyaltyStatementLine.matched_song_id.isnot(None),
            RoyaltyStatementLine.activity_period_start.isnot(None),
            RoyaltyStatementLine.activity_period_end.isnot(None),
            RoyaltyStatementLine.net_amount.isnot(None),
        )
        .all()
    )

    grouped: Dict[Tuple[int, date, date], Dict[int, float]] = defaultdict(
        lambda: defaultdict(float)
    )
    for r in rows:
        key = (r.matched_song_id, r.activity_period_start, r.activity_period_end)
        grouped[key][r.statement_id] += float(r.net_amount or 0)

    for (song_id, ps, pe), per_stmt in grouped.items():
        if len(per_stmt) < 2:
            continue
        amounts = list(per_stmt.values())
        hi, lo = max(amounts), min(amounts)
        delta = hi - lo
        tolerance = max(5.0, hi * 0.05)
        if delta <= tolerance:
            continue
        pct = (delta / hi * 100) if hi else 0
        severity = _severity_from_pct(pct)
        finding = _upsert_audit(
            db, org_id,
            audit_type="CROSS_STATEMENT",
            severity=severity,
            description=(
                f"Song {song_id} reports ${lo:.2f}–${hi:.2f} on "
                f"{len(per_stmt)} statements for {ps} → {pe} "
                f"(delta ${delta:.2f}, {pct:.1f}%)"
            ),
            song_id=song_id,
            period_start=ps,
            period_end=pe,
            expected_cents=int(round(hi * 100)),
            actual_cents=int(round(lo * 100)),
            discrepancy_cents=int(round(delta * 100)),
            details={
                "statements": {str(k): round(v, 2) for k, v in per_stmt.items()},
            },
        )
        findings.append(finding)
    return findings


# ----- Check 2: Rate-check vs published rate cards -------------------------

def _expected_rate_for(store: Optional[str], usage_type: Optional[str]) -> Optional[float]:
    """Return an expected per-unit rate from the streaming-rates config."""
    if not store:
        return None
    key = store.lower().replace(" ", "_").replace("-", "_")
    aliases = {
        "spotify": "spotify",
        "apple": "apple_music",
        "apple_music": "apple_music",
        "itunes": "apple_music",
        "youtube": "youtube_music",
        "youtube_music": "youtube_music",
        "amazon": "amazon_music",
        "amazon_music": "amazon_music",
        "tidal": "tidal",
    }
    platform = aliases.get(key)
    if not platform:
        return None
    tier = "ad_supported" if (usage_type and "ad" in usage_type.lower()) else "premium"
    rate = MASTER_RATES.get(platform, {}).get(tier)
    return rate


def check_rate(db: Session, org_id: int) -> List[RoyaltyAudit]:
    """Aggregate by (song, store, usage_type) and compare per-unit rate
    against the platform's expected rate. Flag anything <60% of expected.
    """
    findings: List[RoyaltyAudit] = []

    rows = (
        db.query(
            RoyaltyStatementLine.matched_song_id,
            RoyaltyStatementLine.store,
            RoyaltyStatementLine.usage_type,
            RoyaltyStatementLine.unit_count,
            RoyaltyStatementLine.net_amount,
            RoyaltyStatementLine.statement_id,
            RoyaltyStatementLine.activity_period_start,
            RoyaltyStatementLine.activity_period_end,
        )
        .filter(
            RoyaltyStatementLine.org_id == org_id,
            RoyaltyStatementLine.matched_song_id.isnot(None),
            RoyaltyStatementLine.unit_count.isnot(None),
            RoyaltyStatementLine.net_amount.isnot(None),
        )
        .all()
    )

    grouped: Dict[Tuple[int, str, str], Dict[str, float]] = defaultdict(
        lambda: {"units": 0.0, "net": 0.0, "stmt": None, "ps": None, "pe": None}
    )
    for r in rows:
        if not r.store or (r.unit_count or 0) <= 0:
            continue
        key = (r.matched_song_id, r.store or "", r.usage_type or "")
        bucket = grouped[key]
        bucket["units"] += float(r.unit_count or 0)
        bucket["net"] += float(r.net_amount or 0)
        bucket["stmt"] = r.statement_id
        bucket["ps"] = r.activity_period_start
        bucket["pe"] = r.activity_period_end

    for (song_id, store, usage_type), b in grouped.items():
        if b["units"] < 1000:
            continue  # avoid noise on tiny samples
        expected = _expected_rate_for(store, usage_type)
        if not expected:
            continue
        actual_rate = b["net"] / b["units"] if b["units"] else 0
        if actual_rate >= expected * 0.6:
            continue
        shortfall_per_unit = expected - actual_rate
        shortfall_total = shortfall_per_unit * b["units"]
        pct = (shortfall_per_unit / expected) * 100 if expected else 0
        severity = _severity_from_pct(pct)
        finding = _upsert_audit(
            db, org_id,
            audit_type="RATE_CHECK",
            severity=severity,
            description=(
                f"Song {song_id} on {store} ({usage_type or 'n/a'}): "
                f"actual ${actual_rate:.5f}/stream vs expected "
                f"${expected:.5f} (~${shortfall_total:.2f} short across "
                f"{int(b['units']):,} units)"
            ),
            song_id=song_id,
            statement_id=b["stmt"],
            period_start=b["ps"],
            period_end=b["pe"],
            expected_cents=int(round(expected * b["units"] * 100)),
            actual_cents=int(round(b["net"] * 100)),
            discrepancy_cents=int(round(shortfall_total * 100)),
            details={
                "store": store,
                "usage_type": usage_type,
                "units": int(b["units"]),
                "expected_rate": expected,
                "actual_rate": round(actual_rate, 6),
            },
            dedup_key=f"{store}|{usage_type or ''}",
        )
        findings.append(finding)
    return findings


# ----- Check 3: Missing period --------------------------------------------

def check_missing_period(db: Session, org_id: int) -> List[RoyaltyAudit]:
    """For each song with ≥3 reported quarters, flag any quarter
    between first-seen and 90 days ago that has zero lines."""
    findings: List[RoyaltyAudit] = []

    series = (
        db.query(
            RoyaltyStatementLine.matched_song_id,
            RoyaltyStatementLine.activity_period_end,
        )
        .filter(
            RoyaltyStatementLine.org_id == org_id,
            RoyaltyStatementLine.matched_song_id.isnot(None),
            RoyaltyStatementLine.activity_period_end.isnot(None),
        )
        .all()
    )

    by_song: Dict[int, set] = defaultdict(set)
    for r in series:
        d = r.activity_period_end
        qk = (d.year, (d.month - 1) // 3 + 1)
        by_song[r.matched_song_id].add(qk)

    today = date.today()
    cur_q = (today.year, (today.month - 1) // 3 + 1)
    cutoff_q = cur_q  # exclude in-progress quarter

    for song_id, quarters in by_song.items():
        if len(quarters) < 3:
            continue
        sorted_q = sorted(quarters)
        first_y, first_q = sorted_q[0]
        # build expected list from first to cutoff (exclusive)
        expected_quarters = []
        y, q = first_y, first_q
        while (y, q) < cutoff_q:
            expected_quarters.append((y, q))
            q += 1
            if q > 4:
                q = 1
                y += 1
        missing = [eq for eq in expected_quarters if eq not in quarters]
        if not missing:
            continue
        # only flag if recent (within last year)
        recent_missing = [
            (y, q) for (y, q) in missing
            if y >= today.year - 1
        ]
        if not recent_missing:
            continue
        sample_y, sample_q = recent_missing[-1]
        ps = date(sample_y, (sample_q - 1) * 3 + 1, 1)
        pe_month = sample_q * 3
        # last day of quarter
        if pe_month == 12:
            pe = date(sample_y, 12, 31)
        else:
            pe = date(sample_y, pe_month + 1, 1) - timedelta(days=1)
        sev = "HIGH" if len(recent_missing) >= 2 else "MEDIUM"
        finding = _upsert_audit(
            db, org_id,
            audit_type="MISSING_PERIOD",
            severity=sev,
            description=(
                f"Song {song_id} is missing {len(recent_missing)} recent "
                f"quarter(s); latest gap: Q{sample_q} {sample_y}"
            ),
            song_id=song_id,
            period_start=ps,
            period_end=pe,
            details={
                "missing_quarters": [f"Q{q} {y}" for (y, q) in recent_missing],
                "reported_quarters": len(quarters),
            },
        )
        findings.append(finding)
    return findings


# ----- Check 4: Decay anomaly ---------------------------------------------

def check_decay_anomaly(db: Session, org_id: int) -> List[RoyaltyAudit]:
    """For each song with enough history to fit an exponential decay,
    flag the latest period if observed deviates ≥40% from fitted."""
    findings: List[RoyaltyAudit] = []

    distinct_songs = (
        db.query(RoyaltyStatementLine.matched_song_id)
        .filter(
            RoyaltyStatementLine.org_id == org_id,
            RoyaltyStatementLine.matched_song_id.isnot(None),
        )
        .distinct()
        .all()
    )

    for (song_id,) in distinct_songs:
        if not song_id:
            continue
        try:
            series = decay_analytics_engine.build_time_series(
                db, org_id, song_id=song_id, granularity="quarter"
            )
        except Exception as e:
            log.debug(f"build_time_series failed for song {song_id}: {e}")
            continue
        if len(series) < 4:
            continue
        fit = decay_analytics_engine.fit_exponential_decay(series)
        if not fit or fit.get("decay_quality") == "poor":
            continue
        observed_fitted = fit.get("observed_vs_fitted") or []
        if not observed_fitted:
            continue
        last = observed_fitted[-1]
        observed = last.get("observed") or 0
        fitted = last.get("fitted")
        if not fitted or fitted <= 0:
            continue
        delta = observed - fitted
        pct = abs(delta) / fitted * 100
        if pct < 40:
            continue
        severity = _severity_from_pct(pct)
        direction = "below" if delta < 0 else "above"
        # Task #173 — derive concrete period_start/period_end from the
        # quarter key (e.g. "2024Q3") so this finding is uniquely keyed
        # at (audit_type, song_id, period_start, period_end). Without
        # this, repeated runs across different periods overwrite each
        # other in the persisted royalty_audits table.
        period_str = last.get("period") or ""
        decay_ps: Optional[date] = None
        decay_pe: Optional[date] = None
        try:
            if len(period_str) >= 6 and period_str[4] == "Q":
                _y = int(period_str[:4])
                _q = int(period_str[5])
                if 1 <= _q <= 4:
                    _start_month = (_q - 1) * 3 + 1
                    decay_ps = date(_y, _start_month, 1)
                    if _q < 4:
                        decay_pe = date(_y, _start_month + 3, 1) - timedelta(days=1)
                    else:
                        decay_pe = date(_y, 12, 31)
        except (ValueError, TypeError):
            decay_ps = None
            decay_pe = None
        finding = _upsert_audit(
            db, org_id,
            audit_type="DECAY_ANOMALY",
            severity=severity,
            description=(
                f"Song {song_id} {last.get('period')}: observed "
                f"${observed:.2f} is {pct:.0f}% {direction} fitted decay "
                f"${fitted:.2f} (R²={fit.get('r2_log')})"
            ),
            song_id=song_id,
            period_start=decay_ps,
            period_end=decay_pe,
            expected_cents=int(round(fitted * 100)),
            actual_cents=int(round(observed * 100)),
            discrepancy_cents=int(round(delta * 100)),
            details={
                "period": last.get("period"),
                "half_life_periods": fit.get("half_life_periods"),
                "r2_log": fit.get("r2_log"),
                "decay_quality": fit.get("decay_quality"),
            },
        )
        findings.append(finding)
    return findings


# ----- Orchestrator --------------------------------------------------------

def run_full_scan(db: Session, org_id: int) -> Dict[str, int]:
    """Run all four checks and commit findings.

    Returns a dict of audit_type → count of findings produced.
    """
    counts = {
        "CROSS_STATEMENT": 0,
        "RATE_CHECK": 0,
        "MISSING_PERIOD": 0,
        "DECAY_ANOMALY": 0,
    }
    try:
        counts["CROSS_STATEMENT"] = len(check_cross_statement(db, org_id))
    except Exception as e:
        log.error(f"cross_statement check failed: {e}")
    try:
        counts["RATE_CHECK"] = len(check_rate(db, org_id))
    except Exception as e:
        log.error(f"rate check failed: {e}")
    try:
        counts["MISSING_PERIOD"] = len(check_missing_period(db, org_id))
    except Exception as e:
        log.error(f"missing_period check failed: {e}")
    try:
        counts["DECAY_ANOMALY"] = len(check_decay_anomaly(db, org_id))
    except Exception as e:
        log.error(f"decay_anomaly check failed: {e}")
    db.commit()
    return counts
