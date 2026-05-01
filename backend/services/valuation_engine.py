"""Catalog valuation engine.

Two surfaces live here:

1. ``calculate_valuation(...)`` — the legacy Spotify-stream-driven
   per-song formula. Still consumed by ``backend/seed_data.py`` and
   ``backend/routes/catalog.py`` and intentionally preserved
   verbatim so existing callers and stored data shapes do not break.

2. ``compute_source_typed_valuation(...)`` — the source-typed engine
   shipped in Task #162. Pulls annualized revenue from matched
   royalty statement lines, buckets it by canonical right category
   (performance / mechanical / sync / streaming / other), applies an
   industry-standard multiplier per bucket, and splits the resulting
   catalog value into artist (MASTER) vs publisher (PUBLISHING)
   shares from the song's ``RightsSplit`` rows. Persists per-song
   ``ValuationCalculation`` rows with ``valuation_method='SOURCE_TYPED'``.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime
from typing import Any, Dict, Iterable, List, Optional, Tuple

from sqlalchemy.orm import Session

import math

from ..config.statement_formats import get_format_spec
from ..models.models import (
    ContractAsset,
    RightsSplit,
    RoyaltyStatement,
    RoyaltyStatementLine,
    Song,
    SongCredit,
    SongStreamingMetrics,
    ValuationCalculation,
)

# Decay-fit helper lives in the underwriting engine; re-export here so
# the Phase 5 market & DCF engines can use it without forcing callers to
# touch underwriting_engine directly. Both modules ship together — if
# this import ever fails it's a real bug and we want it surfaced loudly,
# not swallowed by a stub that silently degrades the valuation math.
from .underwriting_engine import compute_decay_params  # noqa: F401


# ---------------------------------------------------------------------------
# Source-typed engine constants
# ---------------------------------------------------------------------------

# Mapping from raw ``canonical_right_category`` values written by the
# classification engine onto our four valuation buckets. Anything not
# listed here goes into ``other`` and gets no multiplier (excluded from
# the catalog value, but tracked for reporting).
_CATEGORY_BUCKET: Dict[str, str] = {
    # Performance income (PROs, neighboring rights)
    "performance": "performance",
    "neighboring_rights": "performance",
    "neighbouring_rights": "performance",
    "public_performance": "performance",
    # Mechanical (MLC, HFA, mechanical royalties)
    "mechanical": "mechanical",
    # Sync (master/sync licensing fees)
    "sync": "sync",
    "synchronization": "sync",
    "sync_licensing": "sync",
    "sync_fee": "sync",
    # Streaming (DSP/digital interactive)
    "streaming": "streaming",
    "digital": "streaming",
    "interactive_streaming": "streaming",
    "on_demand": "streaming",
    "audio_streaming": "streaming",
    "video_streaming": "streaming",
    "download": "streaming",
}

# Mid-points of the industry multiplier ranges from the spec:
#   performance 8-12×, mechanical 8-10×, sync 6-8×, streaming 10-15×.
_BUCKET_MULTIPLIERS: Dict[str, float] = {
    "performance": 10.0,
    "mechanical": 9.0,
    "sync": 7.0,
    "streaming": 12.5,
    # 'other' has no multiplier — it's reported but excluded from value.
}

# Fallback bucket inferred from the parent statement's ``source_type``
# when ``canonical_right_category`` is missing or 'other'. Lets the
# engine produce meaningful numbers on legacy / pre-classifier data
# (PRO statements typically pay performance income; MLC/HFA pay
# mechanicals; SoundExchange pays performance on digital; DSP pays
# streaming). Operators can fix per-line classifications later via
# the classification engine without invalidating these aggregates.
_SOURCE_TYPE_FALLBACK_BUCKET: Dict[str, str] = {
    "BMI": "performance",
    "ASCAP": "performance",
    "SESAC": "performance",
    "SOCAN": "performance",
    "PRS": "performance",
    "OTHER_PRO": "performance",
    "SOUNDEXCHANGE": "performance",
    "MLC": "mechanical",
    "HARRY_FOX": "mechanical",
    "DSP": "streaming",
    # LABEL covers a mix (master / streaming / mechanical); fall back
    # to streaming since it's the dominant present-day income line.
    "LABEL": "streaming",
}


# Period-cadence -> annualization factor. Reads from the statement
# format registry so adding a new source type only requires a registry
# entry, not a code edit here.
_CADENCE_FACTOR: Dict[str, float] = {
    "monthly": 12.0,
    "quarterly": 4.0,
    "semi-annual": 2.0,
    "semiannual": 2.0,
    "annual": 1.0,
    "yearly": 1.0,
    # "varies" / unknown / missing -> period-of-record as-is (1.0).
}


def _annualization_factor(statement: RoyaltyStatement) -> float:
    """Return the annualization multiplier for a statement based on
    the format registry's declared cadence. Falls back to 1.0 (treat
    the line as already annualized / period-of-record) when the
    cadence is unknown.
    """
    spec = get_format_spec(statement.source_type) if statement else None
    cadence = (spec or {}).get("period_cadence") if spec else None
    if not cadence:
        return 1.0
    return _CADENCE_FACTOR.get(str(cadence).lower(), 1.0)


def _bucket_for(
    category: Optional[str],
    source_type: Optional[str] = None,
) -> str:
    """Resolve bucket from ``canonical_right_category``, falling back
    to the parent statement's ``source_type`` when the category is
    missing or 'other' / 'unclassified'. Returns 'other' only when
    neither signal yields a known bucket.
    """
    if category:
        cat_norm = category.strip().lower()
        if cat_norm not in ("", "other", "unclassified"):
            mapped = _CATEGORY_BUCKET.get(cat_norm)
            if mapped:
                return mapped

    if source_type:
        st = source_type.strip().upper()
        if st in _SOURCE_TYPE_FALLBACK_BUCKET:
            return _SOURCE_TYPE_FALLBACK_BUCKET[st]

    return "other"


def _resolve_song_ids(
    db: Session,
    org_id: int,
    scope_creator_id: Optional[int] = None,
    scope_song_ids: Optional[Iterable[int]] = None,
) -> List[int]:
    """Resolve the set of song IDs the engine should value.

    Precedence: explicit ``scope_song_ids`` > ``scope_creator_id`` >
    org-wide. All paths are filtered to ``org_id`` so a stray creator
    or song id from another tenant cannot bleed in.
    """
    base_q = db.query(Song.id).filter(Song.organization_id == org_id)

    if scope_song_ids is not None:
        ids = [int(s) for s in scope_song_ids]
        if not ids:
            return []
        return [
            sid for (sid,) in base_q.filter(Song.id.in_(ids)).all()
        ]

    if scope_creator_id is not None:
        credited = db.query(SongCredit.song_id).filter(
            SongCredit.creator_id == scope_creator_id
        ).distinct().subquery()
        return [
            sid for (sid,) in base_q.filter(Song.id.in_(credited)).all()
        ]

    return [sid for (sid,) in base_q.all()]


def _splits_for_song(db: Session, song_id: int) -> Tuple[float, float]:
    """Derive (artist_pct, publisher_pct) from RightsSplit rows on
    the song's contract assets.

    - ``artist_pct`` = sum(share_percentage WHERE rights_type='MASTER')
    - ``publisher_pct`` = sum(share_percentage WHERE rights_type='PUBLISHING')

    If a song has no contract assets / rights splits, defaults to a
    50/50 master vs publishing split so the artist/publisher view is
    never empty.
    """
    rows = (
        db.query(RightsSplit.rights_type, RightsSplit.share_percentage)
        .join(ContractAsset, RightsSplit.contract_asset_id == ContractAsset.id)
        .filter(
            ContractAsset.asset_type == "SONG",
            ContractAsset.asset_id == song_id,
        )
        .all()
    )

    if not rows:
        return (50.0, 50.0)

    artist = 0.0
    publisher = 0.0
    for rt, pct in rows:
        v = float(pct or 0.0)
        rt_norm = (rt or "").strip().upper()
        if rt_norm == "MASTER":
            artist += v
        elif rt_norm == "PUBLISHING":
            publisher += v

    # If only one side has data, treat the other side as the complement
    # only when the present side is well-formed (<= 100). If both are
    # zero (e.g. exotic rights_type values), fall back to 50/50 so the
    # downstream UI still shows a split rather than $0/$0.
    if artist == 0.0 and publisher == 0.0:
        return (50.0, 50.0)
    if artist == 0.0 and 0.0 < publisher <= 100.0:
        artist = max(0.0, 100.0 - publisher)
    if publisher == 0.0 and 0.0 < artist <= 100.0:
        publisher = max(0.0, 100.0 - artist)

    return (artist, publisher)


def _compute_song_breakdown(
    db: Session,
    song_id: int,
) -> Dict[str, Any]:
    """Compute one song's source-typed annualized revenue + valuation.

    Returns a dict with bucket revenues (cents), bucket multipliers,
    artist/publisher split %, artist/publisher dollar values, total
    valuation cents, and the line / statement counts that fed it.
    """
    lines = (
        db.query(
            RoyaltyStatementLine.canonical_right_category,
            RoyaltyStatementLine.net_amount_statement_currency,
            RoyaltyStatementLine.net_amount,
            RoyaltyStatement.id.label("stmt_id"),
            RoyaltyStatement.source_type,
        )
        .join(
            RoyaltyStatement,
            RoyaltyStatement.id == RoyaltyStatementLine.statement_id,
        )
        .filter(RoyaltyStatementLine.matched_song_id == song_id)
        .all()
    )

    # Cache annualization factor per statement so we don't re-resolve
    # the registry per line.
    factor_by_stmt: Dict[int, float] = {}
    bucket_revenue_dollars: Dict[str, float] = defaultdict(float)
    statements_seen: set = set()

    for row in lines:
        stmt_id = row.stmt_id
        if stmt_id not in factor_by_stmt:
            # Build a tiny shim with only the source_type attribute
            # _annualization_factor needs.
            class _Shim:
                pass
            shim = _Shim()
            shim.source_type = row.source_type
            factor_by_stmt[stmt_id] = _annualization_factor(shim)
        statements_seen.add(stmt_id)
        factor = factor_by_stmt[stmt_id]
        amount = row.net_amount_statement_currency
        if amount is None:
            amount = row.net_amount or 0.0
        try:
            amount = float(amount)
        except (TypeError, ValueError):
            amount = 0.0
        bucket = _bucket_for(row.canonical_right_category, row.source_type)
        bucket_revenue_dollars[bucket] += amount * factor

    # Convert dollars -> cents, ensure all buckets present (zero if
    # missing), apply multipliers (excluding 'other').
    bucket_revenue_cents: Dict[str, int] = {}
    for b in ("performance", "mechanical", "sync", "streaming", "other"):
        bucket_revenue_cents[b] = int(round(bucket_revenue_dollars.get(b, 0.0) * 100))

    bucket_value_cents: Dict[str, int] = {}
    for b, mult in _BUCKET_MULTIPLIERS.items():
        bucket_value_cents[b] = int(round(bucket_revenue_cents[b] * mult))

    total_value_cents = sum(bucket_value_cents.values())
    total_annual_revenue_cents = sum(bucket_revenue_cents.values())

    artist_pct, publisher_pct = _splits_for_song(db, song_id)
    pct_total = artist_pct + publisher_pct
    if pct_total > 0:
        artist_share = artist_pct / pct_total
        publisher_share = publisher_pct / pct_total
    else:
        artist_share = 0.5
        publisher_share = 0.5

    artist_value_cents = int(round(total_value_cents * artist_share))
    publisher_value_cents = total_value_cents - artist_value_cents

    return {
        "song_id": song_id,
        "bucket_revenue_cents": bucket_revenue_cents,
        "bucket_value_cents": bucket_value_cents,
        "bucket_multipliers": dict(_BUCKET_MULTIPLIERS),
        "total_value_cents": total_value_cents,
        "total_annual_revenue_cents": total_annual_revenue_cents,
        "artist_share_pct": artist_pct,
        "publisher_share_pct": publisher_pct,
        "artist_value_cents": artist_value_cents,
        "publisher_value_cents": publisher_value_cents,
        "line_count": len(lines),
        "statement_count": len(statements_seen),
    }


def compute_source_typed_valuation(
    db: Session,
    org_id: int,
    scope_creator_id: Optional[int] = None,
    scope_song_ids: Optional[Iterable[int]] = None,
    persist: bool = True,
) -> Dict[str, Any]:
    """Run the source-typed valuation engine for an org (optionally
    scoped to a creator or a specific list of songs) and persist a
    new ``ValuationCalculation`` row per song.

    Returns an aggregated summary suitable for direct serialization
    to the API:

    .. code-block:: python

        {
          "org_id": 1,
          "scope": {"creator_id": None, "song_ids": None},
          "computed_at": "2026-04-30T00:00:00",
          "song_count": 12,
          "songs_with_revenue": 9,
          "by_bucket": {
              "performance": {"revenue_cents": 1234, "multiplier": 10.0, "value_cents": 12340},
              ...
          },
          "total_annual_revenue_cents": 9876,
          "total_value_cents": 12345600,
          "artist_total_value_cents": 6172800,
          "publisher_total_value_cents": 6172800,
          "songs": [ ...per-song breakdown rows... ],
        }
    """
    song_ids = _resolve_song_ids(
        db,
        org_id=org_id,
        scope_creator_id=scope_creator_id,
        scope_song_ids=scope_song_ids,
    )

    aggregate_revenue: Dict[str, int] = defaultdict(int)
    aggregate_value: Dict[str, int] = defaultdict(int)
    artist_total = 0
    publisher_total = 0
    total_value = 0
    total_revenue = 0
    songs_with_revenue = 0
    per_song: List[Dict[str, Any]] = []

    now = datetime.utcnow()

    for sid in song_ids:
        breakdown = _compute_song_breakdown(db, sid)
        for b, cents in breakdown["bucket_revenue_cents"].items():
            aggregate_revenue[b] += cents
        for b, cents in breakdown["bucket_value_cents"].items():
            aggregate_value[b] += cents
        artist_total += breakdown["artist_value_cents"]
        publisher_total += breakdown["publisher_value_cents"]
        total_value += breakdown["total_value_cents"]
        total_revenue += breakdown["total_annual_revenue_cents"]
        if breakdown["total_annual_revenue_cents"] > 0:
            songs_with_revenue += 1
        per_song.append(breakdown)

        # Persist a SOURCE_TYPED row for EVERY scoped song — including
        # zero-revenue songs — so that the summary endpoint, which
        # re-aggregates from persisted rows, sees the full scope and
        # reports a faithful song_count. songs_with_revenue stays a
        # computed count of rows where annual_revenue_cents > 0.
        if persist:
            row = ValuationCalculation(
                song_id=sid,
                organization_id=org_id,
                calculation_date=now,
                # Backfill the legacy summary fields so existing
                # dashboards keep working.
                final_valuation_cents=breakdown["total_value_cents"],
                annual_revenue_cents=breakdown["total_annual_revenue_cents"],
                ninety_day_revenue_cents=int(round(breakdown["total_annual_revenue_cents"] / 4)),
                thirty_day_revenue_cents=int(round(breakdown["total_annual_revenue_cents"] / 12)),
                valuation_methodology="SOURCE_TYPED",
                valuation_method="SOURCE_TYPED",
                # Source-typed columns
                revenue_performance_cents=breakdown["bucket_revenue_cents"]["performance"],
                revenue_mechanical_cents=breakdown["bucket_revenue_cents"]["mechanical"],
                revenue_sync_cents=breakdown["bucket_revenue_cents"]["sync"],
                revenue_streaming_cents=breakdown["bucket_revenue_cents"]["streaming"],
                revenue_other_cents=breakdown["bucket_revenue_cents"]["other"],
                multiplier_performance=_BUCKET_MULTIPLIERS["performance"],
                multiplier_mechanical=_BUCKET_MULTIPLIERS["mechanical"],
                multiplier_sync=_BUCKET_MULTIPLIERS["sync"],
                multiplier_streaming=_BUCKET_MULTIPLIERS["streaming"],
                artist_share_pct=breakdown["artist_share_pct"],
                publisher_share_pct=breakdown["publisher_share_pct"],
                artist_valuation_cents=breakdown["artist_value_cents"],
                publisher_valuation_cents=breakdown["publisher_value_cents"],
                calc_metadata={
                    "engine": "source_typed_v1",
                    "line_count": breakdown["line_count"],
                    "statement_count": breakdown["statement_count"],
                },
            )
            db.add(row)

    by_bucket: Dict[str, Dict[str, Any]] = {}
    for b in ("performance", "mechanical", "sync", "streaming", "other"):
        by_bucket[b] = {
            "revenue_cents": int(aggregate_revenue.get(b, 0)),
            "multiplier": _BUCKET_MULTIPLIERS.get(b),  # None for 'other'
            "value_cents": int(aggregate_value.get(b, 0)),
        }

    return {
        "org_id": org_id,
        "scope": {
            "creator_id": scope_creator_id,
            "song_ids": list(scope_song_ids) if scope_song_ids is not None else None,
        },
        "computed_at": now.isoformat(),
        "song_count": len(song_ids),
        "songs_with_revenue": songs_with_revenue,
        "by_bucket": by_bucket,
        "total_annual_revenue_cents": total_revenue,
        "total_value_cents": total_value,
        "artist_total_value_cents": artist_total,
        "publisher_total_value_cents": publisher_total,
        "songs": per_song,
    }


# ---------------------------------------------------------------------------
# Phase 5 — Market-Comparable + DCF + Blended ("Valuation That Sells")
# ---------------------------------------------------------------------------

# Market-comparable per-stream rate bands (USD per stream, all-rights blended).
# These are catalog-tier rates derived from the Citrin Cooperman / industry
# transaction comp ranges:
#   * indie / long-tail   : $0.020 – $0.050  (mid $0.035)
#   * mid-tier            : $0.050 – $0.100  (mid $0.075)
#   * premium / front-line: $0.100 – $0.200  (mid $0.150)
from ..config.streaming_rates import MARKET_COMPARABLE_TIER_BANDS as _TIER_BANDS  # noqa: E402

# Catalog multiplier applied to annualized streaming revenue when treating
# the song as a comparable transaction asset. 10× is the consensus median
# across recent ($25M–$300M) catalog deals.
_MARKET_CATALOG_MULTIPLE: float = 10.0

# DCF defaults
_DCF_DISCOUNT_RATE: float = 0.10
_DCF_PROJECTION_YEARS: int = 10
_DCF_TERMINAL_GROWTH: float = 0.02

# Blended weights per spec — Income (source-typed) 40%, Market 30%, DCF 30%.
_BLEND_WEIGHTS: Dict[str, float] = {
    "income": 0.40,
    "market_comparable": 0.30,
    "dcf": 0.30,
}


def _song_age_years(song: Optional[Song]) -> float:
    """Compute the song's release-age in years. Returns 1.0 when the
    song has no release date so callers don't divide by zero.
    """
    if not song or not song.release_date:
        return 1.0
    today = date.today()
    days = max(1, (today - song.release_date).days)
    return max(1.0, days / 365.25)


def _latest_streaming_metric(
    db: Session, song_id: int
) -> Optional[SongStreamingMetrics]:
    return (
        db.query(SongStreamingMetrics)
        .filter(SongStreamingMetrics.song_id == song_id)
        .order_by(SongStreamingMetrics.period_date.desc().nullslast())
        .first()
    )


def _pick_tier(annual_streams: float) -> str:
    """Tier band selection rule:
      * < 100k annual streams  -> indie
      * 100k – 1M annual       -> mid
      * > 1M annual            -> premium
    """
    if annual_streams < 100_000:
        return "indie"
    if annual_streams < 1_000_000:
        return "mid"
    return "premium"


def _annual_history_from_statements(
    db: Session, song_id: int
) -> List[Tuple[int, float]]:
    """Return ``[(year, annual_net_dollars), ...]`` ascending.

    Aggregates matched ``RoyaltyStatementLine`` rows by the parent
    statement's ``period_end`` year and applies the per-statement
    annualization factor (so a Q1 line worth $100 contributes $400 to
    that year's annualized run-rate). This mirrors the Income engine
    so the DCF stays consistent with the source-typed view.
    """
    rows = (
        db.query(
            RoyaltyStatement.period_end,
            RoyaltyStatement.id,
            RoyaltyStatement.source_type,
            RoyaltyStatementLine.net_amount_statement_currency,
            RoyaltyStatementLine.net_amount,
        )
        .join(
            RoyaltyStatementLine,
            RoyaltyStatementLine.statement_id == RoyaltyStatement.id,
        )
        .filter(RoyaltyStatementLine.matched_song_id == song_id)
        .all()
    )

    if not rows:
        return []

    by_year: Dict[int, float] = defaultdict(float)
    factor_cache: Dict[int, float] = {}

    for period_end, stmt_id, source_type, amt_local, amt_native in rows:
        if not period_end:
            continue
        if stmt_id not in factor_cache:
            class _Shim:
                pass
            shim = _Shim()
            shim.source_type = source_type
            factor_cache[stmt_id] = _annualization_factor(shim)
        factor = factor_cache[stmt_id]
        amt = amt_local
        if amt is None:
            amt = amt_native or 0.0
        try:
            amt = float(amt)
        except (TypeError, ValueError):
            amt = 0.0
        by_year[period_end.year] += amt * factor

    return sorted(by_year.items())


def market_comparable_valuation(
    db: Session, song_id: int
) -> Dict[str, Any]:
    """Per-song market-comparable valuation.

    Steps:
      1. Pull the latest ``SongStreamingMetrics`` row.
      2. Annualize ``total_streams`` over the song's release age
         (cap age at 1.0 yr to avoid divide-by-zero on brand-new
         releases).
      3. Pick a tier band (indie / mid / premium) from annual streams.
      4. Compute annualized revenue = streams × per-stream rate ×
         (ownership_percentage / 100).
      5. Apply the 10× catalog multiplier.
      6. Adjust ±10/15% based on the decay / growth signal:
          * fitted decay (k > 0.05 with R² ≥ 0.5)  -> -15%
          * net growth   (CAGR > 0.05)             -> +10%
          * otherwise neutral

    Returns ``{value_low, value_base, value_high, annual_streams,
    tier, rate_band, ownership_pct, adjustment_factor, has_data,
    reason?}`` with all monetary values in **dollars**.
    """
    metric = _latest_streaming_metric(db, song_id)
    if not metric or not (metric.total_streams or 0):
        return {
            "value_low": 0.0,
            "value_base": 0.0,
            "value_high": 0.0,
            "annual_streams": 0.0,
            "tier": None,
            "rate_band": None,
            "ownership_pct": 0.0,
            "adjustment_factor": 0.0,
            "has_data": False,
            "reason": "No SongStreamingMetrics rows for this song.",
        }

    song = db.query(Song).filter(Song.id == song_id).first()
    age_yrs = _song_age_years(song)
    total_streams = float(metric.total_streams or 0)
    annual_streams = total_streams / age_yrs

    tier = _pick_tier(annual_streams)
    low_rate, mid_rate, high_rate = _TIER_BANDS[tier]

    # Ownership handling: only fall back to 100% when the column is
    # *missing* (None). An explicit 0 means the org owns nothing of this
    # song and the market valuation must reflect that — defaulting it to
    # 100% would materially overvalue assets the org doesn't control.
    raw_ownership = metric.ownership_percentage
    if raw_ownership is None:
        ownership = 1.0
    else:
        try:
            ownership = max(0.0, float(raw_ownership)) / 100.0
        except (TypeError, ValueError):
            ownership = 1.0

    annual_revenue_low = annual_streams * low_rate * ownership
    annual_revenue_mid = annual_streams * mid_rate * ownership
    annual_revenue_high = annual_streams * high_rate * ownership

    # Decay / growth adjustment from the historical annual series.
    history = _annual_history_from_statements(db, song_id)
    adjustment = 0.0
    series_vals = [v for _, v in history if v > 0]
    if len(series_vals) >= 3:
        decay = compute_decay_params(series_vals)  # type: ignore[name-defined]
        if decay and (decay.get("k") or 0.0) > 0.05 and (decay.get("r2") or 0.0) >= 0.5:
            adjustment = -0.15
    if adjustment == 0.0 and len(history) >= 2:
        first_year_val = history[0][1]
        last_year_val = history[-1][1]
        n_years = max(1, history[-1][0] - history[0][0])
        if first_year_val > 0:
            cagr = (last_year_val / first_year_val) ** (1.0 / n_years) - 1.0
            if cagr > 0.05:
                adjustment = 0.10

    factor = 1.0 + adjustment
    base_value = annual_revenue_mid * _MARKET_CATALOG_MULTIPLE * factor
    low_value = annual_revenue_low * _MARKET_CATALOG_MULTIPLE * factor
    high_value = annual_revenue_high * _MARKET_CATALOG_MULTIPLE * factor

    return {
        "value_low": round(low_value, 2),
        "value_base": round(base_value, 2),
        "value_high": round(high_value, 2),
        "annual_streams": round(annual_streams, 2),
        "tier": tier,
        "rate_band": {"low": low_rate, "mid": mid_rate, "high": high_rate},
        "ownership_pct": round(ownership * 100.0, 4),
        "adjustment_factor": adjustment,
        "annual_revenue_base": round(annual_revenue_mid, 2),
        "catalog_multiple": _MARKET_CATALOG_MULTIPLE,
        "has_data": True,
    }


def dcf_valuation(
    db: Session,
    song_id: int,
    discount_rate: float = _DCF_DISCOUNT_RATE,
    projection_years: int = _DCF_PROJECTION_YEARS,
    terminal_growth_rate: float = _DCF_TERMINAL_GROWTH,
) -> Dict[str, Any]:
    """Per-song discounted-cash-flow valuation.

    Strategy:
      * Build ``[(year, annual_net)...]`` from matched statement lines
        (annualized to remove sub-period bias).
      * Use the most recent year's annual_net as the projection
        starting point (``year_0_revenue``).
      * Estimate the per-year growth rate:
          - If ≥ 3 yrs of history fits an exponential decay
            (k > 0.05, R² ≥ 0.5) ⇒ growth = ``-k`` (i.e. contraction).
          - Else if ≥ 2 yrs ⇒ growth = CAGR over the observed window,
            clamped to ``[-0.20, +0.20]``.
          - Otherwise default to ``terminal_growth_rate``.
      * Project forward ``projection_years`` and discount each year at
        ``discount_rate``.
      * Add Gordon-growth terminal value
        ``= terminal_year_revenue * (1 + g_term) / (r - g_term)``
        discounted by ``(1+r)^projection_years``.

    Returns ``{value_low, value_base, value_high, year_0_revenue,
    growth_rate, projections: [...], pv_cash_flows, terminal_value,
    pv_terminal, total_dcf, has_data, reason?}`` with monetary values
    in **dollars** and three scenario bands (±20%).
    """
    history = _annual_history_from_statements(db, song_id)
    if not history:
        return {
            "value_low": 0.0,
            "value_base": 0.0,
            "value_high": 0.0,
            "year_0_revenue": 0.0,
            "growth_rate": 0.0,
            "discount_rate": discount_rate,
            "projection_years": projection_years,
            "terminal_growth_rate": terminal_growth_rate,
            "projections": [],
            "pv_cash_flows": 0.0,
            "terminal_value": 0.0,
            "pv_terminal": 0.0,
            "total_dcf": 0.0,
            "has_data": False,
            "reason": "No matched royalty statement lines for DCF history.",
        }

    year_0 = history[-1][1]
    series_vals = [v for _, v in history if v > 0]
    growth = terminal_growth_rate

    if len(series_vals) >= 3:
        decay = compute_decay_params(series_vals)  # type: ignore[name-defined]
        if decay and (decay.get("k") or 0.0) > 0.05 and (decay.get("r2") or 0.0) >= 0.5:
            growth = -float(decay["k"])

    if len(history) >= 2 and growth == terminal_growth_rate:
        first_v = history[0][1]
        last_v = history[-1][1]
        n_years = max(1, history[-1][0] - history[0][0])
        if first_v > 0:
            cagr = (last_v / first_v) ** (1.0 / n_years) - 1.0
            growth = max(-0.20, min(0.20, cagr))

    # Project + discount
    projections: List[Dict[str, Any]] = []
    pv_sum = 0.0
    current = year_0
    for year in range(1, projection_years + 1):
        current = current * (1.0 + growth)
        # Floor at zero — no negative cashflow modeled.
        current = max(0.0, current)
        pv = current / ((1.0 + discount_rate) ** year)
        pv_sum += pv
        projections.append(
            {"year": year, "projected_net": round(current, 2), "pv": round(pv, 2)}
        )

    terminal_year_rev = projections[-1]["projected_net"] if projections else year_0
    if discount_rate > terminal_growth_rate:
        terminal_value = (
            terminal_year_rev
            * (1.0 + terminal_growth_rate)
            / (discount_rate - terminal_growth_rate)
        )
    else:
        terminal_value = terminal_year_rev * 6.0  # conservative fallback
    pv_terminal = terminal_value / ((1.0 + discount_rate) ** projection_years)

    base = pv_sum + pv_terminal
    low = base * 0.80
    high = base * 1.20

    return {
        "value_low": round(low, 2),
        "value_base": round(base, 2),
        "value_high": round(high, 2),
        "year_0_revenue": round(year_0, 2),
        "growth_rate": round(growth, 4),
        "discount_rate": discount_rate,
        "projection_years": projection_years,
        "terminal_growth_rate": terminal_growth_rate,
        "projections": projections,
        "pv_cash_flows": round(pv_sum, 2),
        "terminal_value": round(terminal_value, 2),
        "pv_terminal": round(pv_terminal, 2),
        "total_dcf": round(base, 2),
        "has_data": True,
    }


def _confidence_score(
    has_statements: bool, has_streaming: bool, history_years: int
) -> Dict[str, Any]:
    """Three-signal confidence: matched-statements, streaming-metrics,
    and ≥ 2 years of history. Returns ``{score (0..1), label,
    has_statements, has_streaming, history_years}``.
    """
    has_history = history_years >= 2
    raw = (1 if has_statements else 0) + (1 if has_streaming else 0) + (1 if has_history else 0)
    score = raw / 3.0
    if score >= 0.66:
        label = "high"
    elif score >= 0.33:
        label = "medium"
    else:
        label = "low"
    return {
        "score": round(score, 4),
        "label": label,
        "has_statements": bool(has_statements),
        "has_streaming": bool(has_streaming),
        "history_years": history_years,
    }


def full_valuation(db: Session, song_id: int) -> Dict[str, Any]:
    """Full per-song valuation orchestrator.

    Returns ``{song_id, income, market_comparable, dcf, blended,
    confidence, data_sources}`` where each engine returns its own
    sub-dict with ``value_low / value_base / value_high`` (dollars)
    and a ``has_data`` flag. ``blended`` follows the
    ``income 40 / market 30 / dcf 30`` weighting from the spec.
    """
    income_breakdown = _compute_song_breakdown(db, song_id)
    income_total_dollars = income_breakdown["total_value_cents"] / 100.0

    income_section = {
        "value_low": round(income_total_dollars * 0.85, 2),
        "value_base": round(income_total_dollars, 2),
        "value_high": round(income_total_dollars * 1.15, 2),
        "annual_revenue": round(income_breakdown["total_annual_revenue_cents"] / 100.0, 2),
        "by_bucket_cents": income_breakdown["bucket_revenue_cents"],
        "by_bucket_value_cents": income_breakdown["bucket_value_cents"],
        "artist_value": round(income_breakdown["artist_value_cents"] / 100.0, 2),
        "publisher_value": round(income_breakdown["publisher_value_cents"] / 100.0, 2),
        "line_count": income_breakdown["line_count"],
        "statement_count": income_breakdown["statement_count"],
        "has_data": income_breakdown["line_count"] > 0,
    }

    market_section = market_comparable_valuation(db, song_id)
    dcf_section = dcf_valuation(db, song_id)

    w = _BLEND_WEIGHTS
    blended_low = (
        income_section["value_low"] * w["income"]
        + market_section["value_low"] * w["market_comparable"]
        + dcf_section["value_low"] * w["dcf"]
    )
    blended_base = (
        income_section["value_base"] * w["income"]
        + market_section["value_base"] * w["market_comparable"]
        + dcf_section["value_base"] * w["dcf"]
    )
    blended_high = (
        income_section["value_high"] * w["income"]
        + market_section["value_high"] * w["market_comparable"]
        + dcf_section["value_high"] * w["dcf"]
    )

    history = _annual_history_from_statements(db, song_id)
    history_years = len({yr for yr, _ in history})
    streaming_present = _latest_streaming_metric(db, song_id) is not None
    confidence = _confidence_score(
        has_statements=income_section["has_data"],
        has_streaming=streaming_present,
        history_years=history_years,
    )

    data_sources: List[str] = []
    if income_section["has_data"]:
        data_sources.append("matched_royalty_statements")
    if streaming_present:
        data_sources.append("song_streaming_metrics")
    if dcf_section.get("has_data"):
        data_sources.append("statement_history_dcf")
    if not data_sources:
        data_sources.append("no_data")

    return {
        "song_id": song_id,
        "income": income_section,
        "market_comparable": market_section,
        "dcf": dcf_section,
        "blended": {
            "value_low": round(blended_low, 2),
            "value_base": round(blended_base, 2),
            "value_high": round(blended_high, 2),
            "weights": dict(w),
        },
        "confidence": confidence,
        "data_sources": data_sources,
    }


# ---------------------------------------------------------------------------
# Catalog-level full valuation orchestrator (Task #172 Phase 5)
# ---------------------------------------------------------------------------


def _attribute_songs_to_creators(
    db: Session, song_ids: List[int]
) -> Dict[int, List[Tuple[int, Optional[str], float]]]:
    """Return ``{song_id: [(creator_id, creator_name, share_fraction), ...]}``.

    Per-creator attribution uses **RightsSplit** rows (joined via
    ``ContractAsset.asset_type='SONG'``) as the economic source of truth:
    each creator's share for a song = sum of their RightsSplit
    ``share_percentage`` across all rights_types they hold for that song,
    normalized so all returned shares for a song sum to 1.0.

    Songs that have no RightsSplit rows fall back to an **equal split
    across SongCredit** rows so the per-creator panel doesn't silently
    drop creators whose songs haven't been formally rights-mapped yet.
    """
    if not song_ids:
        return {}

    from collections import defaultdict
    from ..models.models import SongCredit as _SC, Creator as _Creator

    rs_rows = (
        db.query(
            ContractAsset.asset_id,
            RightsSplit.rights_holder_id,
            _Creator.display_name,
            RightsSplit.share_percentage,
        )
        .join(RightsSplit, RightsSplit.contract_asset_id == ContractAsset.id)
        .outerjoin(_Creator, _Creator.id == RightsSplit.rights_holder_id)
        .filter(
            ContractAsset.asset_type == "SONG",
            ContractAsset.asset_id.in_(song_ids),
            RightsSplit.rights_holder_id.isnot(None),
        )
        .all()
    )

    rights_per_song: Dict[int, Dict[int, Dict[str, Any]]] = defaultdict(
        lambda: defaultdict(lambda: {"name": None, "pct": 0.0})
    )
    for sid, cid, cname, share in rs_rows:
        if cid is None or share is None or float(share) <= 0:
            continue
        slot = rights_per_song[sid][cid]
        slot["name"] = cname or f"Creator #{cid}"
        slot["pct"] += float(share)

    result: Dict[int, List[Tuple[int, Optional[str], float]]] = {}
    for sid, by_creator in rights_per_song.items():
        total = sum(v["pct"] for v in by_creator.values())
        if total <= 0:
            continue
        result[sid] = [
            (cid, slot["name"], slot["pct"] / total)
            for cid, slot in by_creator.items()
        ]

    # Equal-split fallback for songs without any usable RightsSplit row.
    songs_without_rights = [sid for sid in song_ids if sid not in result]
    if songs_without_rights:
        cred_rows = (
            db.query(_SC.song_id, _SC.creator_id, _Creator.display_name)
            .join(_Creator, _Creator.id == _SC.creator_id)
            .filter(_SC.song_id.in_(songs_without_rights))
            .all()
        )
        cred_per_song: Dict[int, List[Tuple[int, Optional[str]]]] = defaultdict(list)
        for sid, cid, cname in cred_rows:
            cred_per_song[sid].append((cid, cname or f"Creator #{cid}"))
        for sid, creds in cred_per_song.items():
            n = len(creds)
            if n == 0:
                continue
            share = 1.0 / n
            result[sid] = [(cid, cname, share) for cid, cname in creds]

    return result


def compute_full_catalog_valuation(
    db: Session,
    org_id: int,
    scope_creator_id: Optional[int] = None,
    scope_song_ids: Optional[Iterable[int]] = None,
    persist: bool = True,
) -> Dict[str, Any]:
    """Run ``full_valuation`` over every in-scope song and aggregate.

    Persists one ``ValuationCalculation`` row per song with
    ``valuation_method='BLENDED'`` and:
      * ``streaming_multiple_value_cents`` ← market-comparable base
      * ``revenue_multiple_value_cents``   ← income base
      * ``black_box_value_cents``          ← DCF base
      * ``final_valuation_cents``          ← blended base

    Returns aggregated summary suitable for direct API serialization,
    keyed by methodology so the frontend can flip between
    ``income / market_comparable / dcf / blended`` without a second
    request.
    """
    song_ids = _resolve_song_ids(
        db,
        org_id=org_id,
        scope_creator_id=scope_creator_id,
        scope_song_ids=scope_song_ids,
    )

    now = datetime.utcnow()

    totals = {
        "income": {"low": 0.0, "base": 0.0, "high": 0.0},
        "market_comparable": {"low": 0.0, "base": 0.0, "high": 0.0},
        "dcf": {"low": 0.0, "base": 0.0, "high": 0.0},
        "blended": {"low": 0.0, "base": 0.0, "high": 0.0},
    }
    by_bucket_cents: Dict[str, int] = defaultdict(int)
    by_bucket_value_cents: Dict[str, int] = defaultdict(int)

    songs_with_statements = 0
    songs_with_streaming = 0
    confidence_scores: List[float] = []
    songs_summary: List[Dict[str, Any]] = []
    artist_total_cents = 0
    publisher_total_cents = 0
    annual_revenue_total_cents = 0

    # Pre-fetch song metadata so the per-song summary rows can include
    # title/primary_artist without one query per song.
    meta_rows = (
        db.query(Song.id, Song.title, Song.primary_artist)
        .filter(Song.id.in_(song_ids))
        .all()
        if song_ids
        else []
    )
    meta_by_id = {sid: (title, artist) for sid, title, artist in meta_rows}

    for sid in song_ids:
        fv = full_valuation(db, sid)

        for k in ("income", "market_comparable", "dcf", "blended"):
            seg = fv[k]
            totals[k]["low"] += seg["value_low"]
            totals[k]["base"] += seg["value_base"]
            totals[k]["high"] += seg["value_high"]

        income_seg = fv["income"]
        for b, cents in income_seg.get("by_bucket_cents", {}).items():
            by_bucket_cents[b] += int(cents or 0)
        for b, cents in income_seg.get("by_bucket_value_cents", {}).items():
            by_bucket_value_cents[b] += int(cents or 0)

        artist_total_cents += int(round(income_seg.get("artist_value", 0.0) * 100))
        publisher_total_cents += int(round(income_seg.get("publisher_value", 0.0) * 100))
        annual_revenue_total_cents += int(round(income_seg.get("annual_revenue", 0.0) * 100))

        if income_seg["has_data"]:
            songs_with_statements += 1
        if fv["market_comparable"].get("has_data"):
            songs_with_streaming += 1
        confidence_scores.append(fv["confidence"]["score"])

        title, primary_artist = meta_by_id.get(sid, (None, None))
        songs_summary.append({
            "song_id": sid,
            "title": title,
            "primary_artist": primary_artist,
            "income_base": income_seg["value_base"],
            "market_base": fv["market_comparable"]["value_base"],
            "dcf_base": fv["dcf"]["value_base"],
            "blended_base": fv["blended"]["value_base"],
            "annual_revenue": income_seg.get("annual_revenue", 0.0),
            "confidence_score": fv["confidence"]["score"],
            "confidence_label": fv["confidence"]["label"],
            "data_sources": fv["data_sources"],
        })

        if persist:
            row = ValuationCalculation(
                song_id=sid,
                organization_id=org_id,
                calculation_date=now,
                # Per-leg storage so the /summary endpoint can re-aggregate
                # without recomputing.
                streaming_multiple_value_cents=int(round(fv["market_comparable"]["value_base"] * 100)),
                revenue_multiple_value_cents=int(round(income_seg["value_base"] * 100)),
                market_comp_value_cents=int(round(fv["market_comparable"]["value_base"] * 100)),
                black_box_value_cents=int(round(fv["dcf"]["value_base"] * 100)),
                final_valuation_cents=int(round(fv["blended"]["value_base"] * 100)),
                annual_revenue_cents=int(round(income_seg.get("annual_revenue", 0.0) * 100)),
                ninety_day_revenue_cents=int(round(income_seg.get("annual_revenue", 0.0) * 25)),
                thirty_day_revenue_cents=int(round(income_seg.get("annual_revenue", 0.0) * 100 / 12)),
                growth_rate=float(fv["dcf"].get("growth_rate") or 0.0),
                risk_score=1.0 - float(fv["confidence"]["score"]),
                valuation_methodology="BLENDED",
                valuation_method="BLENDED",
                # Source-typed columns reused for income breakdown so the
                # source-typed summary endpoint also surfaces data from
                # blended runs.
                revenue_performance_cents=int(income_seg.get("by_bucket_cents", {}).get("performance") or 0),
                revenue_mechanical_cents=int(income_seg.get("by_bucket_cents", {}).get("mechanical") or 0),
                revenue_sync_cents=int(income_seg.get("by_bucket_cents", {}).get("sync") or 0),
                revenue_streaming_cents=int(income_seg.get("by_bucket_cents", {}).get("streaming") or 0),
                revenue_other_cents=int(income_seg.get("by_bucket_cents", {}).get("other") or 0),
                multiplier_performance=_BUCKET_MULTIPLIERS["performance"],
                multiplier_mechanical=_BUCKET_MULTIPLIERS["mechanical"],
                multiplier_sync=_BUCKET_MULTIPLIERS["sync"],
                multiplier_streaming=_BUCKET_MULTIPLIERS["streaming"],
                artist_valuation_cents=int(round(income_seg.get("artist_value", 0.0) * 100)),
                publisher_valuation_cents=int(round(income_seg.get("publisher_value", 0.0) * 100)),
                calc_metadata={
                    "engine": "full_valuation_v1",
                    "weights": _BLEND_WEIGHTS,
                    "discount_rate": fv["dcf"].get("discount_rate"),
                    "projection_years": fv["dcf"].get("projection_years"),
                    "market_tier": fv["market_comparable"].get("tier"),
                    "confidence": fv["confidence"],
                    "data_sources": fv["data_sources"],
                    # Scope tag — lets /full/trend tell apart org-wide
                    # snapshots from creator-scoped subset snapshots so
                    # picking "latest snapshot per day" doesn't swap a
                    # full-catalog total for a partial scoped total.
                    "scope_creator_id": scope_creator_id,
                    "scope_mode": "creator" if scope_creator_id is not None else "org",
                },
            )
            db.add(row)

    # Top songs by blended value (cap at 10 for the API response).
    songs_summary.sort(key=lambda s: s["blended_base"], reverse=True)
    top_songs = songs_summary[:10]

    # Per-creator share (only meaningful when scope is org-wide).
    per_creator_share: List[Dict[str, Any]] = []
    if scope_creator_id is None and song_ids:
        # RightsSplit-weighted attribution: each song's blended value is
        # split among creators by their normalized RightsSplit share
        # (falls back to equal-split SongCredit only for songs that have
        # no rights records). This is the economically correct allocation
        # for unequal shares — the previous equal-split version would
        # misstate creator attribution whenever rights are not 50/50.
        attribution = _attribute_songs_to_creators(db, list(song_ids))
        creator_totals: Dict[int, Dict[str, Any]] = {}
        song_blended_lookup = {s["song_id"]: s["blended_base"] for s in songs_summary}
        for sid, allocations in attribution.items():
            song_value = song_blended_lookup.get(sid, 0.0)
            if not allocations or song_value <= 0:
                continue
            for cid, cname, share_fraction in allocations:
                if cid not in creator_totals:
                    creator_totals[cid] = {
                        "creator_id": cid,
                        "creator_name": cname or f"Creator #{cid}",
                        "blended_value": 0.0,
                        "song_count": 0,
                    }
                creator_totals[cid]["blended_value"] += song_value * share_fraction
                creator_totals[cid]["song_count"] += 1
        per_creator_share = sorted(
            creator_totals.values(), key=lambda r: r["blended_value"], reverse=True
        )[:25]
        # Compute share % against the full catalog blended total so the UI can
        # render a real proportional bar without having to do its own math.
        catalog_blended_base = totals["blended"]["base"] or 0.0
        for r in per_creator_share:
            r["blended_value"] = round(r["blended_value"], 2)
            # Alias matching the per-song summary key shape so frontend
            # components can read either field name interchangeably.
            r["blended_base"] = r["blended_value"]
            r["share_pct"] = (
                round(r["blended_value"] / catalog_blended_base * 100.0, 2)
                if catalog_blended_base > 0
                else 0.0
            )

    overall_confidence = (
        sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0.0
    )
    if overall_confidence >= 0.66:
        conf_label = "high"
    elif overall_confidence >= 0.33:
        conf_label = "medium"
    else:
        conf_label = "low"

    data_quality = {
        "song_count": len(song_ids),
        "songs_with_statements": songs_with_statements,
        "songs_with_streaming": songs_with_streaming,
        "pct_with_statements": (
            round(songs_with_statements / len(song_ids) * 100, 1) if song_ids else 0.0
        ),
        "pct_with_streaming": (
            round(songs_with_streaming / len(song_ids) * 100, 1) if song_ids else 0.0
        ),
        "average_confidence": round(overall_confidence, 4),
        "confidence_label": conf_label,
    }

    by_source_revenue = {
        b: {
            "revenue_cents": int(by_bucket_cents.get(b, 0)),
            "value_cents": int(by_bucket_value_cents.get(b, 0)),
            "multiplier": _BUCKET_MULTIPLIERS.get(b),
        }
        for b in ("performance", "mechanical", "sync", "streaming", "other")
    }

    return {
        "org_id": org_id,
        "scope": {
            "creator_id": scope_creator_id,
            "song_ids": list(scope_song_ids) if scope_song_ids is not None else None,
        },
        "computed_at": now.isoformat(),
        "song_count": len(song_ids),
        "songs_with_statements": songs_with_statements,
        "songs_with_streaming": songs_with_streaming,
        "by_methodology": {
            k: {
                "low": round(totals[k]["low"], 2),
                "base": round(totals[k]["base"], 2),
                "high": round(totals[k]["high"], 2),
            }
            for k in totals
        },
        "by_source": by_source_revenue,
        "annual_revenue_cents": annual_revenue_total_cents,
        "artist_total_value_cents": artist_total_cents,
        "publisher_total_value_cents": publisher_total_cents,
        "weights": dict(_BLEND_WEIGHTS),
        "data_quality": data_quality,
        "top_songs": top_songs,
        "per_creator_share": per_creator_share,
        "fresh": True,
    }


# ---------------------------------------------------------------------------
# Legacy per-song stream-driven formula (kept verbatim for back-compat)
# ---------------------------------------------------------------------------

def calculate_valuation(
    analytics_data: Dict[str, Any],
    publishing_revenue: float = 0.0,
    master_revenue: float = 0.0,
) -> Dict[str, float]:
    """
    Calculate song valuation based on streaming data, playlist positions, and regional metrics.
    Returns a dictionary with low/base/high valuations for both publishing and master, plus estimated revenue.

    Valuation factors:
    - Spotify streams (weight: 0.4)
    - Playlist reach (weight: 0.3)
    - Chartmetric score (weight: 0.2)
    - Regional performance (weight: 0.1)

    Returns:
        {
            "estimated_revenue": float,
            "valuation_low": float (legacy - sum of pub + master),
            "valuation_base": float (legacy - sum of pub + master),
            "valuation_high": float (legacy - sum of pub + master),
            "valuation_low_pub": float,
            "valuation_base_pub": float,
            "valuation_high_pub": float,
            "valuation_low_master": float,
            "valuation_base_master": float,
            "valuation_high_master": float
        }
    """

    spotify_streams = analytics_data.get('spotify_streams', 0)
    playlist_count = analytics_data.get('playlist_count', 0)
    chartmetric_score = analytics_data.get('chartmetric_score', 0)

    stream_value = spotify_streams * 0.003

    playlist_value = 0
    top_playlists = analytics_data.get('top_playlists', [])
    for playlist in top_playlists:
        followers = playlist.get('followers', 0)
        position = playlist.get('position', 100)
        position_multiplier = max(0, (100 - position) / 100)
        playlist_value += (followers / 1000) * position_multiplier * 0.5

    score_value = (chartmetric_score / 100) * 5000

    regional_value = 0
    regional_data = analytics_data.get('regional_data', {})
    for region, data in regional_data.items():
        regional_streams = data.get('streams', 0)
        regional_value += regional_streams * 0.002

    base_valuation = (
        stream_value * 0.4 +
        playlist_value * 0.3 +
        score_value * 0.2 +
        regional_value * 0.1
    )

    estimated_annual_revenue = spotify_streams * 0.004

    # Fixed multipliers for all valuations (publishing and master)
    low_multiplier = 8
    base_multiplier = 12
    high_multiplier = 18

    # Calculate publishing valuations based on publishing revenue
    valuation_low_pub = publishing_revenue * low_multiplier
    valuation_base_pub = publishing_revenue * base_multiplier
    valuation_high_pub = publishing_revenue * high_multiplier

    # Calculate master valuations based on master revenue
    valuation_low_master = master_revenue * low_multiplier
    valuation_base_master = master_revenue * base_multiplier
    valuation_high_master = master_revenue * high_multiplier

    # Legacy combined valuations (sum of publishing + master)
    legacy_low = valuation_low_pub + valuation_low_master
    legacy_base = valuation_base_pub + valuation_base_master
    legacy_high = valuation_high_pub + valuation_high_master

    return {
        "estimated_revenue": round(estimated_annual_revenue, 2),
        "valuation_low": round(legacy_low, 2),
        "valuation_base": round(legacy_base, 2),
        "valuation_high": round(legacy_high, 2),
        "valuation_low_pub": round(valuation_low_pub, 2),
        "valuation_base_pub": round(valuation_base_pub, 2),
        "valuation_high_pub": round(valuation_high_pub, 2),
        "valuation_low_master": round(valuation_low_master, 2),
        "valuation_base_master": round(valuation_base_master, 2),
        "valuation_high_master": round(valuation_high_master, 2),
    }
