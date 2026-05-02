"""Task #199 — read-only intelligence endpoints surfacing the new
BMI v2 parser, rate intelligence, valuation confidence, and
trajectory analytics. All endpoints are tenant-scoped via
``verify_org_access`` and live under ``/api/v1/royalty-intelligence``.
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..models import get_db, User
from .auth import get_current_user
from .royalties import verify_org_access
from ..services import rate_intelligence, decay_analytics_engine
from ..services.valuation_engine import (
    classify_bmi_source,
    international_multiplier,
    INTERNATIONAL_MULTIPLIERS,
)


router = APIRouter(
    prefix="/api/v1/royalty-intelligence",
    tags=["Royalty Intelligence"],
)


@router.get(
    "/{org_id}/statements/{statement_id}/validation",
    summary="BMI parse-quality and stated-vs-computed delta",
    description=(
        "Returns the parse quality score (0–1) and the dollar delta "
        "between the BMI statement's stated grand total and the sum of "
        "ingested line items. NULL ``parse_quality`` for non-BMI uploads."
    ),
)
def get_statement_validation(
    org_id: int,
    statement_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    verify_org_access(current_user, org_id, db)
    out = rate_intelligence.compute_statement_validation(
        db, org_id, statement_id,
    )
    if not out:
        raise HTTPException(status_code=404, detail="Statement not found")
    return out


@router.get(
    "/{org_id}/rates",
    summary="Per-platform effective rate intelligence",
    description=(
        "Returns one row per BMI ``platform_source`` with stream count, "
        "raw rate per stream, writer-share-adjusted effective rate per "
        "stream, and a band flag (LOW / NORMAL / HIGH / NO_BENCHMARK). "
        "Pass ``statement_id`` to scope to a single uploaded file."
    ),
)
def get_rate_intelligence(
    org_id: int,
    statement_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    verify_org_access(current_user, org_id, db)
    return {
        "rates": rate_intelligence.compute_per_platform_rates(
            db, org_id, statement_id=statement_id,
        ),
    }


@router.get(
    "/{org_id}/trajectories",
    summary="Per-song quarterly revenue trajectories + measured catalog decay",
    description=(
        "Returns each song's quarterly net revenue series plus the "
        "median measured catalog decay rate and the new-vs-catalog "
        "revenue split. Powers the DCF model and the trajectory page."
    ),
)
def get_trajectories(
    org_id: int,
    min_quarters: int = 4,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    verify_org_access(current_user, org_id, db)
    trajectories = decay_analytics_engine.compute_song_trajectories(db, org_id)
    decay = decay_analytics_engine.compute_catalog_decay_rate(
        trajectories, min_periods=min_quarters,
    )
    split = decay_analytics_engine.compute_new_vs_catalog_revenue(db, org_id)
    return {
        "trajectories": [
            {"song_id": sid, "series": series}
            for sid, series in trajectories.items()
        ],
        "catalog_decay": decay,
        "new_vs_catalog": split,
    }


@router.get(
    "/{org_id}/source-classification",
    summary="Preview the BMI source → valuation bucket mapping",
    description=(
        "Lookup helper exposing ``classify_bmi_source`` and the "
        "international multiplier table so the frontend can display "
        "what bucket a given source rolls up into."
    ),
)
def preview_source_classification(
    org_id: int,
    source: Optional[str] = None,
    society: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    verify_org_access(current_user, org_id, db)
    out = {
        "international_multipliers": dict(INTERNATIONAL_MULTIPLIERS),
    }
    if source is not None:
        out["source"] = source
        out["bucket"] = classify_bmi_source(source)
    if society is not None:
        out["society"] = society
        out["multiplier"] = international_multiplier(society)
    return out
