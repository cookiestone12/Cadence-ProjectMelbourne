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
        Song.artist,
        func.sum(RoyaltyStatementLine.net_amount).label("total_net"),
    ).join(
        Song, Song.id == RoyaltyStatementLine.matched_song_id
    ).filter(
        RoyaltyStatementLine.org_id == org_id,
        RoyaltyStatementLine.matched_song_id.isnot(None),
    ).group_by(
        RoyaltyStatementLine.matched_song_id, Song.title, Song.artist
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
                "artist": s.artist,
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
        "song": {"id": song.id, "title": song.title, "artist": song.artist},
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
