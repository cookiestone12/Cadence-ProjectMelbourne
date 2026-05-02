import logging
import math
from datetime import date
from typing import Optional, Dict, List, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import func, extract, cast, Integer

from ..models import (
    RoyaltyStatementLine, RoyaltyStatement, Song,
)

logger = logging.getLogger(__name__)


def _quarter_key(d: date) -> str:
    q = math.ceil(d.month / 3)
    return f"{d.year}Q{q}"


def _quarter_index(qk: str) -> float:
    year = int(qk[:4])
    q = int(qk[5])
    return year * 4 + q


def build_time_series(
    db: Session,
    org_id: int,
    song_id: Optional[int] = None,
    granularity: str = "quarter",
) -> List[dict]:
    query = db.query(
        RoyaltyStatementLine.activity_period_start,
        RoyaltyStatementLine.activity_period_end,
        func.sum(RoyaltyStatementLine.net_amount).label("total_net"),
        func.sum(RoyaltyStatementLine.gross_amount).label("total_gross"),
        func.count(RoyaltyStatementLine.id).label("line_count"),
    ).filter(
        RoyaltyStatementLine.org_id == org_id,
        RoyaltyStatementLine.activity_period_end.isnot(None),
    )

    if song_id:
        query = query.filter(RoyaltyStatementLine.matched_song_id == song_id)

    query = query.group_by(
        RoyaltyStatementLine.activity_period_start,
        RoyaltyStatementLine.activity_period_end,
    ).order_by(RoyaltyStatementLine.activity_period_end)

    results = query.all()

    if granularity == "quarter":
        quarter_data = {}
        for r in results:
            if r.activity_period_end:
                qk = _quarter_key(r.activity_period_end)
                if qk not in quarter_data:
                    quarter_data[qk] = {"period": qk, "net": 0.0, "gross": 0.0, "lines": 0}
                quarter_data[qk]["net"] += float(r.total_net or 0)
                quarter_data[qk]["gross"] += float(r.total_gross or 0)
                quarter_data[qk]["lines"] += r.line_count
        series = sorted(quarter_data.values(), key=lambda x: x["period"])
        for s in series:
            s["net"] = round(s["net"], 2)
            s["gross"] = round(s["gross"], 2)
        return series
    else:
        return [
            {
                "period_start": str(r.activity_period_start) if r.activity_period_start else None,
                "period_end": str(r.activity_period_end) if r.activity_period_end else None,
                "net": round(float(r.total_net or 0), 2),
                "gross": round(float(r.total_gross or 0), 2),
                "lines": r.line_count,
            }
            for r in results
        ]


def fit_exponential_decay(series: List[dict]) -> Optional[dict]:
    if len(series) < 3:
        return None

    peak_idx = 0
    peak_val = 0
    for i, s in enumerate(series):
        if s["net"] > peak_val:
            peak_val = s["net"]
            peak_idx = i

    post_peak = series[peak_idx:]
    if len(post_peak) < 3:
        return None

    y0 = post_peak[0]["net"]
    if y0 <= 0:
        return None

    ts = []
    log_ratios = []
    valid_points = []
    for i, s in enumerate(post_peak):
        if s["net"] > 0:
            t = float(i)
            ts.append(t)
            log_ratios.append(math.log(s["net"] / y0))
            valid_points.append(s)

    if len(ts) < 3:
        return None

    sum_t2 = sum(t * t for t in ts)
    sum_t_ln = sum(t * lr for t, lr in zip(ts, log_ratios))

    if sum_t2 == 0:
        return None

    k = -sum_t_ln / sum_t2

    if k <= 0:
        return None

    half_life = math.log(2) / k

    fitted = [y0 * math.exp(-k * t) for t in ts]

    log_y = [math.log(s["net"]) for s in valid_points]
    log_yhat = [math.log(f) for f in fitted]

    mean_log_y = sum(log_y) / len(log_y)
    ss_tot = sum((ly - mean_log_y) ** 2 for ly in log_y)
    ss_res = sum((ly - lyh) ** 2 for ly, lyh in zip(log_y, log_yhat))

    r2 = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0

    observed_fitted = []
    for i, s in enumerate(post_peak):
        entry = {"period": s["period"], "observed": s["net"]}
        if i < len(ts) and s["net"] > 0:
            idx = ts.index(float(i)) if float(i) in ts else None
            if idx is not None:
                entry["fitted"] = round(fitted[idx], 2)
        observed_fitted.append(entry)

    return {
        "peak_period": post_peak[0]["period"],
        "peak_value": round(y0, 2),
        "k_per_period": round(k, 4),
        "half_life_periods": round(half_life, 2),
        "r2_log": round(r2, 4),
        "decay_quality": "good" if r2 >= 0.7 else ("fair" if r2 >= 0.4 else "poor"),
        "data_points": len(valid_points),
        "observed_vs_fitted": observed_fitted,
    }


def compute_cagr(series: List[dict], periods_per_year: float = 4.0) -> Optional[dict]:
    if len(series) < 2:
        return None

    y0 = series[0]["net"]
    yt = series[-1]["net"]

    if y0 <= 0 or yt <= 0:
        return None

    n_periods = len(series) - 1
    dt_years = n_periods / periods_per_year

    if dt_years <= 0:
        return None

    cagr = (yt / y0) ** (1 / dt_years) - 1

    return {
        "start_period": series[0]["period"],
        "end_period": series[-1]["period"],
        "start_value": round(y0, 2),
        "end_value": round(yt, 2),
        "years": round(dt_years, 2),
        "cagr": round(cagr, 4),
        "cagr_pct": round(cagr * 100, 2),
    }


def compute_concentration(series_by_song: Dict[int, float]) -> dict:
    if not series_by_song:
        return {"top1_share": 0, "top5_share": 0, "hhi": 0, "song_count": 0}

    total = sum(series_by_song.values())
    if total <= 0:
        return {"top1_share": 0, "top5_share": 0, "hhi": 0, "song_count": len(series_by_song)}

    sorted_vals = sorted(series_by_song.values(), reverse=True)
    shares = [v / total for v in sorted_vals]

    top1 = shares[0] if shares else 0
    top5 = sum(shares[:5]) if len(shares) >= 5 else sum(shares)
    hhi = sum(s * s for s in shares)

    return {
        "top1_share": round(top1, 4),
        "top5_share": round(top5, 4),
        "hhi": round(hhi, 4),
        "song_count": len(series_by_song),
    }


def get_portfolio_analytics(db: Session, org_id: int) -> dict:
    portfolio_series = build_time_series(db, org_id)

    decay = fit_exponential_decay(portfolio_series)
    cagr = compute_cagr(portfolio_series)

    song_totals = db.query(
        RoyaltyStatementLine.matched_song_id,
        func.sum(RoyaltyStatementLine.net_amount).label("total_net"),
    ).filter(
        RoyaltyStatementLine.org_id == org_id,
        RoyaltyStatementLine.matched_song_id.isnot(None),
    ).group_by(RoyaltyStatementLine.matched_song_id).all()

    song_map = {s.matched_song_id: float(s.total_net or 0) for s in song_totals}
    concentration = compute_concentration(song_map)

    right_breakdown = db.query(
        RoyaltyStatementLine.canonical_right_category,
        func.sum(RoyaltyStatementLine.net_amount).label("total_net"),
    ).filter(
        RoyaltyStatementLine.org_id == org_id,
    ).group_by(RoyaltyStatementLine.canonical_right_category).all()

    channel_breakdown = db.query(
        RoyaltyStatementLine.canonical_channel,
        func.sum(RoyaltyStatementLine.net_amount).label("total_net"),
    ).filter(
        RoyaltyStatementLine.org_id == org_id,
    ).group_by(RoyaltyStatementLine.canonical_channel).all()

    top_songs = db.query(
        RoyaltyStatementLine.matched_song_id,
        Song.title,
        Song.primary_artist,
        func.sum(RoyaltyStatementLine.net_amount).label("total_net"),
    ).join(
        Song, Song.id == RoyaltyStatementLine.matched_song_id
    ).filter(
        RoyaltyStatementLine.org_id == org_id,
        RoyaltyStatementLine.matched_song_id.isnot(None),
    ).group_by(
        RoyaltyStatementLine.matched_song_id, Song.title, Song.primary_artist
    ).order_by(func.sum(RoyaltyStatementLine.net_amount).desc()).limit(10).all()

    return {
        "time_series": portfolio_series,
        "decay": decay,
        "cagr": cagr,
        "concentration": concentration,
        "by_right_category": [
            {"category": r.canonical_right_category or "other", "net_total": round(float(r.total_net or 0), 2)}
            for r in right_breakdown
        ],
        "by_channel": [
            {"channel": r.canonical_channel or "other", "net_total": round(float(r.total_net or 0), 2)}
            for r in channel_breakdown
        ],
        "top_songs": [
            {
                "song_id": s.matched_song_id,
                "title": s.title,
                "artist": s.primary_artist,
                "net_total": round(float(s.total_net or 0), 2),
            }
            for s in top_songs
        ],
    }


def get_song_analytics(db: Session, org_id: int, song_id: int) -> dict:
    song = db.query(Song).filter(Song.id == song_id, Song.organization_id == org_id).first()
    if not song:
        return {"error": "Song not found"}

    series = build_time_series(db, org_id, song_id=song_id)
    decay = fit_exponential_decay(series)
    cagr = compute_cagr(series)

    right_breakdown = db.query(
        RoyaltyStatementLine.canonical_right_category,
        func.sum(RoyaltyStatementLine.net_amount).label("total_net"),
    ).filter(
        RoyaltyStatementLine.org_id == org_id,
        RoyaltyStatementLine.matched_song_id == song_id,
    ).group_by(RoyaltyStatementLine.canonical_right_category).all()

    territory_breakdown = db.query(
        RoyaltyStatementLine.territory_iso2,
        func.sum(RoyaltyStatementLine.net_amount).label("total_net"),
    ).filter(
        RoyaltyStatementLine.org_id == org_id,
        RoyaltyStatementLine.matched_song_id == song_id,
        RoyaltyStatementLine.territory_iso2.isnot(None),
    ).group_by(RoyaltyStatementLine.territory_iso2).order_by(
        func.sum(RoyaltyStatementLine.net_amount).desc()
    ).limit(10).all()

    return {
        "song": {"id": song.id, "title": song.title, "artist": song.primary_artist},
        "time_series": series,
        "decay": decay,
        "cagr": cagr,
        "by_right_category": [
            {"category": r.canonical_right_category or "other", "net_total": round(float(r.total_net or 0), 2)}
            for r in right_breakdown
        ],
        "by_territory": [
            {"territory": r.territory_iso2, "net_total": round(float(r.total_net or 0), 2)}
            for r in territory_breakdown
        ],
    }


# ---------------------------------------------------------------------------
# Task #199 Phase 4 — per-song trajectories, measured catalog decay,
# new-vs-catalog revenue split.
# ---------------------------------------------------------------------------

def compute_song_trajectories(
    db: Session,
    org_id: int,
    song_ids: Optional[List[int]] = None,
    granularity: str = "quarter",
) -> Dict[int, List[dict]]:
    """For each matched song, return its quarterly revenue series.

    Returns ``{ song_id: [{period, net_total, gross_total, line_count}, ...] }``
    sorted chronologically. Songs with zero matched lines are omitted.
    """
    q = db.query(
        RoyaltyStatementLine.matched_song_id,
        RoyaltyStatementLine.activity_period_start,
        RoyaltyStatementLine.activity_period_end,
        func.sum(RoyaltyStatementLine.net_amount).label("net_total"),
        func.sum(RoyaltyStatementLine.gross_amount).label("gross_total"),
        func.count(RoyaltyStatementLine.id).label("line_count"),
    ).filter(
        RoyaltyStatementLine.org_id == org_id,
        RoyaltyStatementLine.matched_song_id.isnot(None),
        RoyaltyStatementLine.activity_period_end.isnot(None),
    )
    if song_ids:
        q = q.filter(RoyaltyStatementLine.matched_song_id.in_(song_ids))
    q = q.group_by(
        RoyaltyStatementLine.matched_song_id,
        RoyaltyStatementLine.activity_period_start,
        RoyaltyStatementLine.activity_period_end,
    )

    by_song: Dict[int, Dict[str, dict]] = {}
    for sid, _ps, pe, net, gross, lc in q.all():
        if not pe or not sid:
            continue
        qk = _quarter_key(pe)
        sb = by_song.setdefault(sid, {})
        bucket = sb.setdefault(qk, {
            "period": qk, "net_total": 0.0, "gross_total": 0.0, "line_count": 0,
        })
        bucket["net_total"] += float(net or 0)
        bucket["gross_total"] += float(gross or 0)
        bucket["line_count"] += int(lc or 0)

    out: Dict[int, List[dict]] = {}
    for sid, periods in by_song.items():
        ordered = sorted(periods.values(), key=lambda x: _quarter_index(x["period"]))
        out[sid] = [
            {
                "period": p["period"],
                "net_total": round(p["net_total"], 2),
                "gross_total": round(p["gross_total"], 2),
                "line_count": p["line_count"],
            }
            for p in ordered
        ]
    return out


def compute_catalog_decay_rate(
    trajectories: Dict[int, List[dict]],
    min_periods: int = 4,
) -> Dict:
    """Average measured quarterly decay across catalog songs.

    A "catalog song" here = any song with at least ``min_periods``
    quarters of recorded earnings (default 4 = a year of history).

    Decay is computed per song as the slope of a simple linear fit on
    log-revenue vs quarter index, expressed as a per-quarter %
    contraction. Returned ``catalog_decay_rate`` is the median across
    songs (more robust than mean when one outlier doubles or 10× a
    quarter — common with sync placements).
    """
    rates: List[float] = []
    songs_used = 0
    for sid, series in trajectories.items():
        if len(series) < min_periods:
            continue
        # log-linear fit
        xs = [_quarter_index(p["period"]) for p in series]
        ys = [p["net_total"] for p in series if p["net_total"] > 0]
        if len(ys) < min_periods:
            continue
        # Recompute xs aligned to ys (drop zero/negative values).
        pairs = [(_quarter_index(p["period"]), p["net_total"])
                 for p in series if p["net_total"] > 0]
        n = len(pairs)
        sx = sum(x for x, _ in pairs)
        sy = sum(math.log(y) for _, y in pairs)
        sxx = sum(x * x for x, _ in pairs)
        sxy = sum(x * math.log(y) for x, y in pairs)
        denom = n * sxx - sx * sx
        if denom == 0:
            continue
        slope = (n * sxy - sx * sy) / denom
        # slope is d(ln revenue)/d(quarter); decay = 1 - e^slope.
        per_quarter_change = math.exp(slope) - 1.0
        rates.append(per_quarter_change)
        songs_used += 1

    if not rates:
        return {
            "catalog_decay_rate": None,
            "songs_used": 0,
            "decay_quality": "insufficient_data",
        }

    rates.sort()
    median = rates[len(rates) // 2] if len(rates) % 2 else (
        (rates[len(rates) // 2 - 1] + rates[len(rates) // 2]) / 2.0
    )
    # Convention: a healthy catalog decays 5–15% per quarter (negative
    # change); positive numbers = growth.
    if median <= -0.20:
        quality = "concerning"
    elif median <= -0.05:
        quality = "healthy"
    elif median < 0:
        quality = "stable"
    else:
        quality = "growing"

    return {
        "catalog_decay_rate": round(median, 4),
        "median_quarterly_change": round(median, 4),
        "songs_used": songs_used,
        "decay_quality": quality,
        "min_quarters_required": min_periods,
    }


def compute_new_vs_catalog_revenue(
    db: Session,
    org_id: int,
    new_threshold_quarters: int = 2,
    granularity: str = "quarter",
) -> Dict:
    """Split revenue into "new" songs vs "catalog" songs.

    A song is "new" if its first matched-line period is within
    ``new_threshold_quarters`` of the most recent period in the org.
    Healthy publishing catalog: ~60-70% recurring catalog revenue.
    """
    trajectories = compute_song_trajectories(db, org_id)
    if not trajectories:
        return {
            "new_revenue": 0.0,
            "catalog_revenue": 0.0,
            "new_pct": 0.0,
            "catalog_pct": 0.0,
            "new_song_count": 0,
            "catalog_song_count": 0,
        }

    # Latest period across all songs.
    all_periods = sorted({p["period"] for series in trajectories.values() for p in series},
                         key=_quarter_index)
    if not all_periods:
        return {
            "new_revenue": 0.0, "catalog_revenue": 0.0,
            "new_pct": 0.0, "catalog_pct": 0.0,
            "new_song_count": 0, "catalog_song_count": 0,
        }
    latest_idx = _quarter_index(all_periods[-1])

    new_rev = 0.0
    cat_rev = 0.0
    new_count = 0
    cat_count = 0
    for sid, series in trajectories.items():
        first_idx = _quarter_index(series[0]["period"])
        total = sum(p["net_total"] for p in series)
        if (latest_idx - first_idx) < new_threshold_quarters:
            new_rev += total
            new_count += 1
        else:
            cat_rev += total
            cat_count += 1

    grand = new_rev + cat_rev
    return {
        "new_revenue": round(new_rev, 2),
        "catalog_revenue": round(cat_rev, 2),
        "new_pct": round(new_rev / grand, 4) if grand else 0.0,
        "catalog_pct": round(cat_rev / grand, 4) if grand else 0.0,
        "new_song_count": new_count,
        "catalog_song_count": cat_count,
        "new_threshold_quarters": new_threshold_quarters,
    }
