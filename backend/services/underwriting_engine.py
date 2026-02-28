import logging
import math
from datetime import datetime, date
from typing import Optional
from collections import defaultdict

from sqlalchemy.orm import Session
from sqlalchemy import func, and_

from ..models.models import (
    RoyaltyStatement, RoyaltyStatementLine, Song, Work,
    UnderwritingRun, RoyaltyLedgerEntry, SongCredit,
)
from ..kb import get_kb, get_kb_version

logger = logging.getLogger("cadence")


def _period_key(d: date, granularity: str = "half") -> str:
    if granularity == "quarter":
        q = (d.month - 1) // 3 + 1
        return f"{d.year}Q{q}"
    else:
        h = "H1" if d.month <= 6 else "H2"
        return f"{d.year}{h}"


def _period_sort_key(period_str: str) -> tuple:
    if "Q" in period_str:
        year = int(period_str[:4])
        q = int(period_str[-1])
        return (year, q)
    else:
        year = int(period_str[:4])
        h = 1 if period_str.endswith("H1") else 2
        return (year, h)


def build_song_period_spine(
    db: Session,
    org_id: int,
    periodization_mode: str = "activity",
    granularity: str = "half",
    exclude_right_types: list[str] | None = None,
    exclude_flags: list[str] | None = None,
    scope_creator_id: int | None = None,
) -> list[dict]:
    query = db.query(RoyaltyStatementLine).filter(
        RoyaltyStatementLine.org_id == org_id,
        RoyaltyStatementLine.match_status == "MATCHED",
    )

    if exclude_right_types:
        for rt in exclude_right_types:
            query = query.filter(RoyaltyStatementLine.canonical_right_category != rt)

    if scope_creator_id:
        song_ids = [
            sc.song_id for sc in
            db.query(SongCredit.song_id).filter(SongCredit.creator_id == scope_creator_id).all()
        ]
        if song_ids:
            query = query.filter(RoyaltyStatementLine.matched_song_id.in_(song_ids))
        else:
            return []

    lines = query.all()

    spine_map = defaultdict(lambda: {
        "publisher_net": 0.0, "master_net": 0.0, "total_net": 0.0,
        "gross": 0.0, "withholding": 0.0, "line_count": 0,
    })

    for line in lines:
        if exclude_flags and line.accounting_flags:
            flags = line.accounting_flags
            if isinstance(flags, dict):
                active = [k.replace("is_", "") for k, v in flags.items() if v]
            elif isinstance(flags, list):
                active = flags
            else:
                active = []
            if any(f in exclude_flags for f in active):
                continue

        if periodization_mode == "activity" and line.activity_period_start:
            period_date = line.activity_period_start
        elif line.statement and line.statement.period_start:
            stmt = db.query(RoyaltyStatement).get(line.statement_id)
            period_date = stmt.period_start if stmt else (line.activity_period_start or date.today())
        else:
            period_date = line.activity_period_start or date.today()

        period = _period_key(period_date, granularity)
        song_id = line.matched_song_id
        work_id = line.matched_work_id

        key = (song_id, work_id, period)
        net = float(line.net_amount or 0)
        gross = float(line.gross_amount or 0)
        deductions = float(line.deductions_amount or 0)

        right_cat = (line.canonical_right_category or "").lower()
        if right_cat in ("mechanical", "performance", "sync", "print_lyrics"):
            spine_map[key]["publisher_net"] += net
        else:
            spine_map[key]["master_net"] += net

        spine_map[key]["total_net"] += net
        spine_map[key]["gross"] += gross
        spine_map[key]["withholding"] += deductions
        spine_map[key]["line_count"] += 1

    song_titles = {}
    song_ids_set = set(k[0] for k in spine_map if k[0])
    if song_ids_set:
        songs = db.query(Song.id, Song.title, Song.isrc).filter(Song.id.in_(song_ids_set)).all()
        for s in songs:
            song_titles[s.id] = {"title": s.title, "isrc": s.isrc}

    spine = []
    for (song_id, work_id, period), data in spine_map.items():
        entry = {
            "song_id": song_id,
            "work_id": work_id,
            "period": period,
            "song_title": song_titles.get(song_id, {}).get("title"),
            "isrc": song_titles.get(song_id, {}).get("isrc"),
            **data,
        }
        spine.append(entry)

    spine.sort(key=lambda x: (_period_sort_key(x["period"]), -(x["total_net"])))
    return spine


def compute_decay_params(series: list[float]) -> dict | None:
    if len(series) < 3:
        return None

    peak_idx = series.index(max(series))
    post_peak = series[peak_idx:]

    if len(post_peak) < 3:
        return None

    positive = [(i, v) for i, v in enumerate(post_peak) if v > 0]
    if len(positive) < 3:
        return None

    y0 = positive[0][1]
    sum_t_lny = 0.0
    sum_t2 = 0.0
    for t_idx, (orig_i, val) in enumerate(positive):
        t = orig_i
        if t == 0:
            continue
        ln_ratio = math.log(val / y0)
        sum_t_lny += t * ln_ratio
        sum_t2 += t * t

    if sum_t2 == 0:
        return None

    k = -sum_t_lny / sum_t2
    if k <= 0:
        return {"k": 0, "half_life_periods": None, "r2": 0, "peak_value": y0, "peak_index": peak_idx, "growing": True}

    half_life = math.log(2) / k

    ss_res = 0.0
    ss_tot = 0.0
    mean_ln_y = sum(math.log(v) for _, v in positive) / len(positive)
    for orig_i, val in positive:
        ln_y = math.log(val)
        ln_yhat = math.log(y0) - k * orig_i
        ss_res += (ln_y - ln_yhat) ** 2
        ss_tot += (ln_y - mean_ln_y) ** 2

    r2 = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0

    n = len(series)
    if n >= 2 and series[0] > 0 and series[-1] > 0:
        cagr = (series[-1] / series[0]) ** (1.0 / (n - 1)) - 1
    else:
        cagr = None

    return {
        "k": round(k, 4),
        "half_life_periods": round(half_life, 2),
        "r2": round(max(0, r2), 4),
        "cagr": round(cagr, 4) if cagr is not None else None,
        "peak_value": round(y0, 2),
        "peak_index": peak_idx,
        "data_points": len(positive),
        "growing": False,
    }


def compute_volatility(series: list[float]) -> float | None:
    if len(series) < 3:
        return None
    log_returns = []
    for i in range(1, len(series)):
        if series[i] > 0 and series[i - 1] > 0:
            log_returns.append(math.log(series[i] / series[i - 1]))
    if len(log_returns) < 2:
        return None
    mean_lr = sum(log_returns) / len(log_returns)
    variance = sum((lr - mean_lr) ** 2 for lr in log_returns) / (len(log_returns) - 1)
    return round(math.sqrt(variance), 4)


def compute_concentration(spine: list[dict], period: str) -> dict:
    period_entries = [e for e in spine if e["period"] == period and e["total_net"] > 0]
    if not period_entries:
        return {"top_1": 0, "top_3": 0, "top_5": 0, "top_10": 0, "hhi": 0, "song_count": 0}

    total = sum(e["total_net"] for e in period_entries)
    if total <= 0:
        return {"top_1": 0, "top_3": 0, "top_5": 0, "top_10": 0, "hhi": 0, "song_count": len(period_entries)}

    sorted_entries = sorted(period_entries, key=lambda x: x["total_net"], reverse=True)
    shares = [e["total_net"] / total for e in sorted_entries]

    return {
        "top_1": round(shares[0] if len(shares) >= 1 else 0, 4),
        "top_3": round(sum(shares[:3]), 4),
        "top_5": round(sum(shares[:5]), 4),
        "top_10": round(sum(shares[:10]), 4),
        "hhi": round(sum(s ** 2 for s in shares), 4),
        "song_count": len(period_entries),
    }


def project_forward(
    annual_net: float,
    decay_k: float,
    horizon_years: int = 10,
    scenario_band: float = 1.0,
    periods_per_year: int = 2,
) -> list[dict]:
    effective_k = decay_k * scenario_band
    k_per_period = effective_k / periods_per_year if periods_per_year > 0 else effective_k

    projections = []
    current = annual_net / periods_per_year if periods_per_year > 0 else annual_net

    for year in range(1, horizon_years + 1):
        year_total = 0.0
        for p in range(periods_per_year):
            t = (year - 1) * periods_per_year + p
            val = current * math.exp(-k_per_period * t) if effective_k > 0 else current
            year_total += val
        projections.append({
            "year": year,
            "projected_net": round(year_total, 2),
        })

    return projections


def compute_dcf(
    projections: list[dict],
    discount_rate: float = 0.11,
    terminal_multiple: float = 6.0,
) -> dict:
    pv_sum = 0.0
    for proj in projections:
        year = proj["year"]
        pv = proj["projected_net"] / ((1 + discount_rate) ** year)
        pv_sum += pv

    terminal_year_revenue = projections[-1]["projected_net"] if projections else 0
    terminal_value = terminal_year_revenue * terminal_multiple
    pv_terminal = terminal_value / ((1 + discount_rate) ** len(projections))

    return {
        "pv_cash_flows": round(pv_sum, 2),
        "terminal_value": round(terminal_value, 2),
        "pv_terminal": round(pv_terminal, 2),
        "total_dcf": round(pv_sum + pv_terminal, 2),
        "discount_rate": discount_rate,
        "terminal_multiple": terminal_multiple,
    }


def compute_multiplier_valuation(
    annual_revenue: float,
    publisher_share: float,
    master_share: float,
    stability_signals: dict | None = None,
) -> dict:
    kb = get_kb()
    pub_multiples = kb["valuation"]["multipliers"]["publishing_nps"]
    master_multiples = kb["valuation"]["multipliers"]["masters_net"]
    adjustments = kb["valuation"]["multiple_adjustments"]

    adj_factor = 0.0
    signals = stability_signals or {}
    if signals.get("high_concentration"):
        adj_factor += adjustments["high_concentration_penalty"]
    if signals.get("high_volatility"):
        adj_factor += adjustments["high_volatility_penalty"]
    if signals.get("low_r2"):
        adj_factor += adjustments["low_r2_penalty"]
    if signals.get("has_disputes"):
        adj_factor += adjustments["dispute_penalty"]
    if signals.get("missing_periods"):
        adj_factor += adjustments["missing_periods_penalty"]
    if signals.get("strong_growth"):
        adj_factor += adjustments["strong_growth_bonus"]

    pub_revenue = annual_revenue * publisher_share if publisher_share else 0
    master_revenue = annual_revenue * master_share if master_share else 0

    def apply_mult(base_rev, multiples):
        return {
            "low": round(base_rev * multiples["low"] * (1 + adj_factor), 2),
            "base": round(base_rev * multiples["base"] * (1 + adj_factor), 2),
            "high": round(base_rev * multiples["high"] * (1 + adj_factor), 2),
        }

    pub_val = apply_mult(pub_revenue, pub_multiples)
    master_val = apply_mult(master_revenue, master_multiples)

    return {
        "publishing": pub_val,
        "masters": master_val,
        "combined": {
            "low": round(pub_val["low"] + master_val["low"], 2),
            "base": round(pub_val["base"] + master_val["base"], 2),
            "high": round(pub_val["high"] + master_val["high"], 2),
        },
        "adjustment_factor": round(adj_factor, 4),
        "annual_revenue": round(annual_revenue, 2),
        "publisher_share": publisher_share,
        "master_share": master_share,
    }


def run_underwriting(
    db: Session,
    org_id: int,
    user_id: int | None = None,
    periodization_mode: str = "activity",
    granularity: str = "half",
    exclude_right_types: list[str] | None = None,
    exclude_flags: list[str] | None = None,
    scope_creator_id: int | None = None,
    include_sync: bool = True,
    use_gross: bool = False,
) -> dict:
    kb = get_kb()
    kb_version = get_kb_version()

    effective_exclude_rt = list(exclude_right_types or [])
    if not include_sync and "sync" not in effective_exclude_rt:
        effective_exclude_rt.append("sync")
    if not include_sync and "print_lyrics" not in effective_exclude_rt:
        effective_exclude_rt.append("print_lyrics")

    inputs_config = {
        "periodization_mode": periodization_mode,
        "granularity": granularity,
        "exclude_right_types": effective_exclude_rt,
        "exclude_flags": exclude_flags or [],
        "scope_creator_id": scope_creator_id,
        "include_sync": include_sync,
        "use_gross": use_gross,
    }

    run = UnderwritingRun(
        organization_id=org_id,
        created_by_user_id=user_id,
        kb_version=kb_version,
        status="RUNNING",
        scope_creator_id=scope_creator_id,
        inputs=inputs_config,
    )
    db.add(run)
    db.flush()

    try:
        spine = build_song_period_spine(
            db, org_id,
            periodization_mode=periodization_mode,
            granularity=granularity,
            exclude_right_types=effective_exclude_rt if effective_exclude_rt else None,
            exclude_flags=exclude_flags,
            scope_creator_id=scope_creator_id,
        )

        periods = sorted(set(e["period"] for e in spine), key=_period_sort_key)

        song_series = defaultdict(dict)
        for entry in spine:
            sid = entry["song_id"] or f"work_{entry['work_id']}"
            val = entry.get("gross" if use_gross else "total_net", 0)
            song_series[sid][entry["period"]] = val

        decay_results = {}
        exceptions = []
        min_points = kb["analytics"]["decay"]["min_data_points"]

        for sid, period_data in song_series.items():
            series_values = [period_data.get(p, 0) for p in periods]
            if sum(1 for v in series_values if v > 0) < min_points:
                exceptions.append({
                    "song_id": sid,
                    "reason": "insufficient_data",
                    "data_points": sum(1 for v in series_values if v > 0),
                })
                continue

            decay = compute_decay_params(series_values)
            vol = compute_volatility(series_values)

            if decay:
                decay["volatility"] = vol
                decay["series"] = series_values
                decay_results[str(sid)] = decay

        concentration_by_period = {}
        for period in periods:
            concentration_by_period[period] = compute_concentration(spine, period)

        total_annual = 0.0
        publisher_annual = 0.0
        master_annual = 0.0

        if len(periods) >= 2:
            last_periods = periods[-2:]
            for entry in spine:
                if entry["period"] in last_periods:
                    total_annual += entry["total_net"]
                    publisher_annual += entry["publisher_net"]
                    master_annual += entry["master_net"]
        elif periods:
            for entry in spine:
                if entry["period"] == periods[-1]:
                    scale = 2 if granularity == "half" else 4
                    total_annual += entry["total_net"] * scale
                    publisher_annual += entry["publisher_net"] * scale
                    master_annual += entry["master_net"] * scale

        total_rev = publisher_annual + master_annual
        pub_share = publisher_annual / total_rev if total_rev > 0 else 0.5
        master_share = master_annual / total_rev if total_rev > 0 else 0.5

        decay_ks = [d["k"] for d in decay_results.values() if d.get("k") and d["k"] > 0]
        portfolio_k = sum(decay_ks) / len(decay_ks) if decay_ks else 0.1

        half_lives = [d["half_life_periods"] for d in decay_results.values() if d.get("half_life_periods")]
        portfolio_half_life = sum(half_lives) / len(half_lives) if half_lives else None

        latest_conc = concentration_by_period.get(periods[-1], {}) if periods else {}

        stability_signals = {
            "high_concentration": latest_conc.get("hhi", 0) > 0.25,
            "high_volatility": any(d.get("volatility", 0) and d["volatility"] > 0.5 for d in decay_results.values()),
            "low_r2": any(d.get("r2", 1) < 0.5 for d in decay_results.values()),
            "has_disputes": False,
            "missing_periods": len(exceptions) > len(decay_results) * 0.3 if decay_results else False,
            "strong_growth": portfolio_k < 0,
        }

        decay_bands = kb["analytics"]["scenario_matrix"]["decay_bands"]
        dcf_config = kb["valuation"]["dcf"]

        projection_scenarios = {}
        dcf_scenarios = {}
        for scenario_name, band_mult in decay_bands.items():
            projections = project_forward(
                total_annual, portfolio_k,
                horizon_years=dcf_config["horizon_years"],
                scenario_band=band_mult,
            )
            projection_scenarios[scenario_name] = projections

            for rate_name, rate_val in dcf_config["discount_rate_bands"].items():
                terminal_mult = dcf_config["terminal_multiple"].get(rate_name, 6)
                dcf = compute_dcf(projections, rate_val, terminal_mult)
                dcf_scenarios[f"{scenario_name}_{rate_name}"] = dcf

        multiplier_val = compute_multiplier_valuation(
            total_annual, pub_share, master_share, stability_signals
        )

        base_dcf = dcf_scenarios.get("base_base", {})
        low_dcf = dcf_scenarios.get("downside_high", {})
        high_dcf = dcf_scenarios.get("upside_low", {})

        valuation_output = {
            "dcf": {
                "low": low_dcf.get("total_dcf", 0),
                "base": base_dcf.get("total_dcf", 0),
                "high": high_dcf.get("total_dcf", 0),
                "scenarios": dcf_scenarios,
            },
            "multiplier": multiplier_val,
            "blended": {
                "low": round((multiplier_val["combined"]["low"] + (low_dcf.get("total_dcf", 0))) / 2, 2),
                "base": round((multiplier_val["combined"]["base"] + (base_dcf.get("total_dcf", 0))) / 2, 2),
                "high": round((multiplier_val["combined"]["high"] + (high_dcf.get("total_dcf", 0))) / 2, 2),
            },
        }

        portfolio_summary = {
            "total_songs_in_spine": len(set(e["song_id"] for e in spine if e["song_id"])),
            "total_periods": len(periods),
            "periods": periods,
            "annual_revenue": round(total_annual, 2),
            "publisher_annual": round(publisher_annual, 2),
            "master_annual": round(master_annual, 2),
            "publisher_share": round(pub_share, 4),
            "master_share": round(master_share, 4),
            "portfolio_decay_k": round(portfolio_k, 4),
            "portfolio_half_life": round(portfolio_half_life, 2) if portfolio_half_life else None,
            "stability_signals": stability_signals,
        }

        spine_for_storage = spine[:500]

        run.spine_data = {
            "entries": spine_for_storage,
            "total_entries": len(spine),
            "portfolio_summary": portfolio_summary,
        }
        run.decay_data = {
            "per_song": {k: {kk: vv for kk, vv in v.items() if kk != "series"} for k, v in decay_results.items()},
            "portfolio_k": round(portfolio_k, 4),
            "portfolio_half_life": round(portfolio_half_life, 2) if portfolio_half_life else None,
            "half_life_distribution": _compute_half_life_distribution(decay_results),
        }
        run.concentration_data = concentration_by_period
        run.projection_data = projection_scenarios
        run.valuation_data = valuation_output
        run.exceptions = exceptions
        run.outputs = portfolio_summary
        run.status = "COMPLETED"
        run.completed_at = datetime.utcnow()
        db.flush()

        logger.info(f"Underwriting run {run.id} completed for org {org_id}: {len(spine)} spine entries, {len(decay_results)} decay fits")

        return {
            "run_id": run.id,
            "status": "COMPLETED",
            "portfolio_summary": portfolio_summary,
            "valuation": valuation_output,
            "spine_count": len(spine),
            "decay_fits": len(decay_results),
            "exceptions": len(exceptions),
        }

    except Exception as e:
        run.status = "FAILED"
        run.exceptions = [{"error": str(e)}]
        run.completed_at = datetime.utcnow()
        db.flush()
        logger.error(f"Underwriting run {run.id} failed: {e}")
        raise


def _compute_half_life_distribution(decay_results: dict) -> dict:
    bins = {"0-1q": 0, "1-2q": 0, "2-4q": 0, "4-8q": 0, "8q+": 0}
    for data in decay_results.values():
        hl = data.get("half_life_periods")
        if hl is None:
            continue
        if hl < 1:
            bins["0-1q"] += 1
        elif hl < 2:
            bins["1-2q"] += 1
        elif hl < 4:
            bins["2-4q"] += 1
        elif hl < 8:
            bins["4-8q"] += 1
        else:
            bins["8q+"] += 1
    return bins
