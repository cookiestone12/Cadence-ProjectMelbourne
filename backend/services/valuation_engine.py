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

from ..config.statement_formats import get_format_spec
from ..models.models import (
    ContractAsset,
    RightsSplit,
    RoyaltyStatement,
    RoyaltyStatementLine,
    Song,
    SongCredit,
    ValuationCalculation,
)


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
