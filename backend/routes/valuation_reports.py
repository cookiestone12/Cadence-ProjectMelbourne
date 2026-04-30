from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime, date, timedelta
from ..models import get_db
from ..models.models import (
    User, Organization, OrganizationMember, Song, SongCredit,
    ValuationCalculation, SongStreamingMetrics, TerritoryRevenue,
    Creator, UnderwritingRun, RoyaltyStatement
)
from ..utils.auth import get_current_user
from ..services.underwriting_engine import run_underwriting
from ..services.underwriting_controls import run_reconciliation_controls
from ..services.valuation_engine import compute_source_typed_valuation
import json

router = APIRouter(prefix="/api/valuation", tags=["Valuations"])

class SongValuationDetail(BaseModel):
    song_id: int
    title: str
    primary_artist: str
    isrc: Optional[str]
    release_date: Optional[str]
    
    total_streams: int
    ownership_percentage: float
    
    streaming_multiple_value: float
    revenue_multiple_value: float
    market_comp_value: float
    black_box_value: float
    final_valuation: float
    
    thirty_day_revenue: float
    ninety_day_revenue: float
    annual_revenue: float
    
    growth_rate: float
    risk_score: float
    
    class Config:
        from_attributes = True

class TerritoryRevenueDetail(BaseModel):
    territory_code: str
    territory_name: str
    total_streams: int
    publishing_revenue: float
    master_revenue: float
    total_revenue: float
    
    class Config:
        from_attributes = True

class CatalogValuationSummary(BaseModel):
    organization_name: str
    total_songs: int
    total_catalog_value: float
    total_thirty_day_revenue: float
    total_annual_revenue: float
    avg_growth_rate: float
    generated_at: str
    
    top_songs: List[SongValuationDetail]
    territory_breakdown: List[TerritoryRevenueDetail]

class SongDetailWithValuation(BaseModel):
    song: Dict[str, Any]
    streaming_metrics: Dict[str, Any]
    territory_revenues: List[Dict[str, Any]]
    valuation: Dict[str, Any]
    credits: List[Dict[str, Any]]

@router.get("/catalog/summary", summary="Get comprehensive catalog valuation summary for the organization", description="Returns the comprehensive catalog valuation summary used by the valuation dashboard (NPV band, multiples, top contributors, last underwriting run).\n\n**Query:** `org_id` (defaults to caller's current org), `discount_rate?`, `multiple?`, `scope_creator_id?` (restricts the summary to songs credited to a single creator in the caller's org).\n**Auth:** Bearer JWT — caller must be a member of the org.\n**Response:** `{ npv_cents, low_high_band: [low, high], multiple_value_cents, top_contributors: [...], last_run_at }`.")
def get_catalog_valuation_summary(
    scope_creator_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get comprehensive catalog valuation summary for the organization.

    When ``scope_creator_id`` is provided, the summary is restricted to songs
    credited to that creator. The creator must belong to the caller's org or
    the request is rejected with 404 to avoid cross-org data exposure.
    """
    
    membership = db.query(OrganizationMember).filter(
        OrganizationMember.user_id == current_user.id
    ).first()
    
    if not membership:
        raise HTTPException(status_code=404, detail="Organization membership not found")
    
    org = db.query(Organization).filter(Organization.id == membership.organization_id).first()

    scoped_song_ids: Optional[set] = None
    if scope_creator_id is not None:
        from ..models.models import Creator as _Creator, SongCredit as _SongCredit
        creator_in_org = db.query(_Creator.id).filter(
            _Creator.id == scope_creator_id,
            _Creator.organization_id == org.id,
        ).first()
        if not creator_in_org:
            raise HTTPException(status_code=404, detail="Creator not found in this org")
        scoped_song_ids = {
            sid for (sid,) in db.query(_SongCredit.song_id)
            .filter(_SongCredit.creator_id == scope_creator_id)
            .distinct()
            .all()
        }
        if scoped_song_ids:
            songs = db.query(Song).filter(
                Song.organization_id == org.id,
                Song.id.in_(scoped_song_ids),
            ).all()
        else:
            songs = []
    else:
        songs = db.query(Song).filter(Song.organization_id == org.id).all()
    
    valuations_q = db.query(ValuationCalculation).filter(
        ValuationCalculation.organization_id == org.id
    )
    if scoped_song_ids is not None:
        # Restrict org-wide valuation rows to the scoped creator's songs so
        # totals/top-songs/avg-growth reflect ONLY that creator's catalog.
        if scoped_song_ids:
            valuations_q = valuations_q.filter(
                ValuationCalculation.song_id.in_(scoped_song_ids)
            )
        else:
            valuations_q = valuations_q.filter(False)
    valuations = valuations_q.order_by(ValuationCalculation.calculation_date.desc()).all()
    
    valuation_by_song = {}
    for v in valuations:
        if v.song_id not in valuation_by_song:
            valuation_by_song[v.song_id] = v
    
    total_catalog_value = sum(v.final_valuation_cents for v in valuation_by_song.values()) / 100 if valuation_by_song else 0.0
    total_thirty_day_revenue = sum(v.thirty_day_revenue_cents for v in valuation_by_song.values()) / 100 if valuation_by_song else 0.0
    total_annual_revenue = sum(v.annual_revenue_cents for v in valuation_by_song.values()) / 100 if valuation_by_song else 0.0
    
    growth_rates = [v.growth_rate for v in valuation_by_song.values() if v.growth_rate]
    avg_growth_rate = sum(growth_rates) / len(growth_rates) if growth_rates else 0.0
    
    top_valuations = sorted(valuation_by_song.values(), key=lambda v: v.final_valuation_cents, reverse=True)[:10] if valuation_by_song else []
    
    top_songs = []
    for val in top_valuations:
        song = next((s for s in songs if s.id == val.song_id), None)
        if song:
            metrics = db.query(SongStreamingMetrics).filter(
                SongStreamingMetrics.song_id == song.id
            ).order_by(SongStreamingMetrics.period_date.desc()).first()
            
            top_songs.append({
                "song_id": song.id,
                "title": song.title,
                "primary_artist": song.primary_artist,
                "isrc": song.isrc,
                "release_date": song.release_date.isoformat() if song.release_date else None,
                "total_streams": metrics.total_streams if metrics else 0,
                "ownership_percentage": metrics.ownership_percentage if metrics else 1.0,
                "streaming_multiple_value": val.streaming_multiple_value_cents / 100,
                "revenue_multiple_value": val.revenue_multiple_value_cents / 100,
                "market_comp_value": val.market_comp_value_cents / 100,
                "black_box_value": val.black_box_value_cents / 100,
                "final_valuation": val.final_valuation_cents / 100,
                "thirty_day_revenue": val.thirty_day_revenue_cents / 100,
                "ninety_day_revenue": val.ninety_day_revenue_cents / 100,
                "annual_revenue": val.annual_revenue_cents / 100,
                "growth_rate": val.growth_rate,
                "risk_score": val.risk_score
            })
    
    territory_q = db.query(
        TerritoryRevenue.territory_code,
        TerritoryRevenue.territory_name,
        func.sum(TerritoryRevenue.total_streams).label("total_streams"),
        func.sum(TerritoryRevenue.publishing_revenue_cents).label("publishing_revenue_cents"),
        func.sum(TerritoryRevenue.master_revenue_cents).label("master_revenue_cents"),
        func.sum(TerritoryRevenue.total_revenue_cents).label("total_revenue_cents")
    ).filter(
        TerritoryRevenue.organization_id == org.id
    )
    if scoped_song_ids is not None:
        if scoped_song_ids:
            territory_q = territory_q.filter(TerritoryRevenue.song_id.in_(scoped_song_ids))
        else:
            territory_q = territory_q.filter(False)
    territory_data = territory_q.group_by(
        TerritoryRevenue.territory_code,
        TerritoryRevenue.territory_name
    ).order_by(desc("total_revenue_cents")).all()
    
    territory_breakdown = [
        {
            "territory_code": t.territory_code,
            "territory_name": t.territory_name,
            "total_streams": t.total_streams,
            "publishing_revenue": t.publishing_revenue_cents / 100,
            "master_revenue": t.master_revenue_cents / 100,
            "total_revenue": t.total_revenue_cents / 100
        }
        for t in territory_data
    ]
    
    return {
        "organization_name": org.display_name or org.name,
        "total_songs": len(songs),
        "total_catalog_value": total_catalog_value,
        "total_thirty_day_revenue": total_thirty_day_revenue,
        "total_annual_revenue": total_annual_revenue,
        "avg_growth_rate": avg_growth_rate,
        "generated_at": datetime.utcnow().isoformat(),
        "top_songs": top_songs,
        "territory_breakdown": territory_breakdown
    }

@router.get("/song/{song_id}/detail", summary="Get detailed valuation information for a specific song", description="Returns detailed valuation information for a specific song (cashflow history, decay fit, NPV breakdown).\n\n**Path parameter:** `song_id`.\n**Auth:** Bearer JWT — caller must be a member of the song's org.\n**Response:** `{ song_id, title, npv_cents, historical: [{period, cents}], projected: [{period, cents}], decay: {a, k, r2}, share_of_catalog_pct }`.")
def get_song_valuation_detail(
    song_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get detailed valuation information for a specific song"""
    
    song = db.query(Song).filter(Song.id == song_id).first()
    if not song:
        raise HTTPException(status_code=404, detail="Song not found")
    
    membership = db.query(OrganizationMember).filter(
        OrganizationMember.user_id == current_user.id,
        OrganizationMember.organization_id == song.organization_id
    ).first()
    
    if not membership:
        raise HTTPException(status_code=403, detail="Not authorized to access this song")
    
    valuation = db.query(ValuationCalculation).filter(
        ValuationCalculation.song_id == song_id
    ).order_by(ValuationCalculation.calculation_date.desc()).first()
    
    metrics = db.query(SongStreamingMetrics).filter(
        SongStreamingMetrics.song_id == song_id
    ).order_by(SongStreamingMetrics.period_date.desc()).first()
    
    territory_revenues = db.query(TerritoryRevenue).filter(
        TerritoryRevenue.song_id == song_id
    ).order_by(TerritoryRevenue.total_revenue_cents.desc()).all()
    
    credits = db.query(SongCredit, Creator).join(
        Creator, SongCredit.creator_id == Creator.id
    ).filter(SongCredit.song_id == song_id).all()
    
    return {
        "song": {
            "id": song.id,
            "title": song.title,
            "primary_artist": song.primary_artist,
            "isrc": song.isrc,
            "iswc": song.iswc,
            "release_date": song.release_date.isoformat() if song.release_date else None,
            "health_score": song.status_health_score
        },
        "streaming_metrics": {
            "total_streams": metrics.total_streams if metrics else 0,
            "ad_supported_streams": metrics.ad_supported_streams if metrics else 0,
            "premium_streams": metrics.premium_streams if metrics else 0,
            "interactive_streams": metrics.interactive_streams if metrics else 0,
            "on_demand_streams": metrics.on_demand_streams if metrics else 0,
            "programmed_streams": metrics.programmed_streams if metrics else 0,
            "audio_streams": metrics.audio_streams if metrics else 0,
            "video_streams": metrics.video_streams if metrics else 0,
            "song_sales": metrics.song_sales if metrics else 0,
            "ownership_percentage": metrics.ownership_percentage if metrics else 1.0
        } if metrics else {},
        "territory_revenues": [
            {
                "territory_code": tr.territory_code,
                "territory_name": tr.territory_name,
                "total_streams": tr.total_streams,
                "publishing_revenue": tr.publishing_revenue_cents / 100,
                "master_revenue": tr.master_revenue_cents / 100,
                "total_revenue": tr.total_revenue_cents / 100
            }
            for tr in territory_revenues
        ],
        "valuation": {
            "streaming_multiple_value": valuation.streaming_multiple_value_cents / 100 if valuation else 0,
            "revenue_multiple_value": valuation.revenue_multiple_value_cents / 100 if valuation else 0,
            "market_comp_value": valuation.market_comp_value_cents / 100 if valuation else 0,
            "black_box_value": valuation.black_box_value_cents / 100 if valuation else 0,
            "final_valuation": valuation.final_valuation_cents / 100 if valuation else 0,
            "methodology": valuation.valuation_methodology if valuation else "N/A",
            "thirty_day_revenue": valuation.thirty_day_revenue_cents / 100 if valuation else 0,
            "ninety_day_revenue": valuation.ninety_day_revenue_cents / 100 if valuation else 0,
            "annual_revenue": valuation.annual_revenue_cents / 100 if valuation else 0,
            "growth_rate": valuation.growth_rate if valuation else 0,
            "risk_score": valuation.risk_score if valuation else 0.5
        } if valuation else {},
        "credits": [
            {
                "creator_id": credit.SongCredit.creator_id,
                "creator_name": credit.Creator.display_name,
                "role": credit.SongCredit.role,
                "share_percentage": credit.SongCredit.share_percentage
            }
            for credit in credits
        ]
    }

@router.get("/catalog/download/excel", summary="Download catalog valuation report as Excel file", description='Renders the catalog valuation report as an Excel workbook for download.\n\n**Query:** `org_id`, `discount_rate?`, `multiple?`.\n**Auth:** Bearer JWT — caller must be a member of the org.\n**Response:** `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet` download.')
def download_catalog_valuation_excel(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Download catalog valuation report as Excel file"""
    
    import io
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Alignment
    
    membership = db.query(OrganizationMember).filter(
        OrganizationMember.user_id == current_user.id
    ).first()
    
    if not membership:
        raise HTTPException(status_code=404, detail="Organization membership not found")
    
    org = db.query(Organization).filter(Organization.id == membership.organization_id).first()
    
    wb = Workbook()
    
    ws_summary = wb.active
    ws_summary.title = "Catalog Summary"
    
    ws_summary['A1'] = "Cadence Catalog Report"
    ws_summary['A1'].font = Font(size=14, bold=True)
    ws_summary['A2'] = f"Catalog: {org.name}"
    ws_summary['A3'] = f"Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}"
    
    ws_summary['A5'] = "Metric"
    ws_summary['B5'] = "Value"
    ws_summary['A5'].font = Font(bold=True)
    ws_summary['B5'].font = Font(bold=True)
    
    songs = db.query(Song).filter(Song.organization_id == org.id).all()
    valuations = db.query(ValuationCalculation).filter(
        ValuationCalculation.organization_id == org.id
    ).all()
    
    valuation_by_song = {}
    for v in valuations:
        if v.song_id not in valuation_by_song:
            valuation_by_song[v.song_id] = v
    
    total_catalog_value = sum(v.final_valuation_cents for v in valuation_by_song.values()) / 100
    total_annual_revenue = sum(v.annual_revenue_cents for v in valuation_by_song.values()) / 100
    
    ws_summary['A6'] = "Total Songs"
    ws_summary['B6'] = len(songs)
    ws_summary['A7'] = "Total Catalog Value"
    ws_summary['B7'] = f"${total_catalog_value:,.2f}"
    ws_summary['A8'] = "Annual Revenue"
    ws_summary['B8'] = f"${total_annual_revenue:,.2f}"
    
    ws_details = wb.create_sheet("Song Details")
    headers = ['Title', 'Artist', 'ISRC', 'Release Date', 'Total Streams', 'Valuation', 'Annual Revenue', 'Growth Rate']
    for col, header in enumerate(headers, 1):
        cell = ws_details.cell(row=1, column=col, value=header)
        cell.font = Font(bold=True)
        cell.fill = PatternFill(start_color="D0D0D0", end_color="D0D0D0", fill_type="solid")
    
    row = 2
    for song in songs:
        val = valuation_by_song.get(song.id)
        metrics = db.query(SongStreamingMetrics).filter(
            SongStreamingMetrics.song_id == song.id
        ).order_by(SongStreamingMetrics.period_date.desc()).first()
        
        ws_details.cell(row=row, column=1, value=song.title)
        ws_details.cell(row=row, column=2, value=song.primary_artist)
        ws_details.cell(row=row, column=3, value=song.isrc or "")
        ws_details.cell(row=row, column=4, value=song.release_date.isoformat() if song.release_date else "")
        ws_details.cell(row=row, column=5, value=metrics.total_streams if metrics else 0)
        ws_details.cell(row=row, column=6, value=f"${val.final_valuation_cents / 100:,.2f}" if val else "$0.00")
        ws_details.cell(row=row, column=7, value=f"${val.annual_revenue_cents / 100:,.2f}" if val else "$0.00")
        ws_details.cell(row=row, column=8, value=f"{val.growth_rate * 100:.1f}%" if val else "0.0%")
        row += 1
    
    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    
    filename = f"cadence_catalog_report_{org.name.replace(' ', '_')}_{datetime.utcnow().strftime('%Y%m%d')}.xlsx"
    
    return Response(
        content=output.getvalue(),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": f"attachment; filename={filename}"
        }
    )


class UnderwritingRunRequest(BaseModel):
    periodization_mode: str = "activity"
    granularity: str = "half"
    exclude_right_types: List[str] = []
    exclude_flags: List[str] = []
    scope_creator_id: Optional[int] = None
    include_sync: bool = True
    use_gross: bool = False


@router.post(
    "/underwriting/run",
    summary='Trigger a fresh underwriting run on the catalog',
    description="Kicks off the underwriting engine which produces a snapshot of the catalog's value: spine groupings, decay fits, concentration metrics. Synchronous; returns when complete.\n\n**Body:** `{ org_id: int, params?: {discount_rate, horizon_years, ...} }`.\n**Auth:** Bearer JWT — caller must be a member of the org.\n**Response:** `{ run_id, status, started_at, completed_at }`.",
)
def trigger_underwriting_run(
    request: UnderwritingRunRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    membership = db.query(OrganizationMember).filter(
        OrganizationMember.user_id == current_user.id
    ).first()
    if not membership:
        raise HTTPException(status_code=404, detail="Organization membership not found")

    if request.scope_creator_id is not None:
        from ..models.models import Creator as _Creator
        belongs = db.query(_Creator.id).filter(
            _Creator.id == request.scope_creator_id,
            _Creator.organization_id == membership.organization_id,
        ).first()
        if not belongs:
            raise HTTPException(status_code=404, detail="Creator not found in this org")

    try:
        result = run_underwriting(
            db=db,
            org_id=membership.organization_id,
            user_id=current_user.id,
            periodization_mode=request.periodization_mode,
            granularity=request.granularity,
            exclude_right_types=request.exclude_right_types or None,
            exclude_flags=request.exclude_flags or None,
            scope_creator_id=request.scope_creator_id,
            include_sync=request.include_sync,
            use_gross=request.use_gross,
        )
        db.commit()
        return result
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Underwriting run failed: {str(e)}")


@router.get(
    "/underwriting/runs",
    summary='List historical underwriting runs',
    description='Returns the audit trail of `/run` invocations.\n\n**Query:** `org_id`, `limit`, `offset`.\n**Auth:** Bearer JWT — caller must be a member of the org.\n**Response:** `{ runs: [{id, started_at, completed_at, params, npv_cents, status}] }`.',
)
def list_underwriting_runs(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    membership = db.query(OrganizationMember).filter(
        OrganizationMember.user_id == current_user.id
    ).first()
    if not membership:
        raise HTTPException(status_code=404, detail="Organization membership not found")

    runs = db.query(UnderwritingRun).filter(
        UnderwritingRun.organization_id == membership.organization_id
    ).order_by(UnderwritingRun.created_at.desc()).limit(20).all()

    creator_ids = {r.scope_creator_id for r in runs if r.scope_creator_id}
    name_by_id: dict[int, str] = {}
    if creator_ids:
        from ..models.models import Creator as _Creator
        # Restrict creator-name lookup to the caller's org so a stray
        # cross-org scope_creator_id (legacy or malicious) cannot leak the
        # display name of a creator from another tenant.
        for c in db.query(_Creator.id, _Creator.display_name).filter(
            _Creator.id.in_(creator_ids),
            _Creator.organization_id == membership.organization_id,
        ).all():
            name_by_id[c.id] = c.display_name

    return [
        {
            "id": r.id,
            "status": r.status,
            "kb_version": r.kb_version,
            "inputs": r.inputs,
            "scope_creator_id": r.scope_creator_id,
            "scope_creator_name": name_by_id.get(r.scope_creator_id) if r.scope_creator_id else None,
            "portfolio_summary": r.outputs,
            "valuation": r.valuation_data.get("blended") if r.valuation_data else None,
            "created_at": r.created_at.isoformat() if r.created_at else None,
            "completed_at": r.completed_at.isoformat() if r.completed_at else None,
        }
        for r in runs
    ]


@router.get(
    "/underwriting/runs/{run_id}",
    summary='Get the headline result of a single underwriting run',
    description="Returns the run's summary numbers: NPV, multiples, top contributors, model parameters.\n\n**Path parameter:** `run_id`.\n**Auth:** Bearer JWT — caller must be a member of the run's org.\n**Response:** `{ id, params, summary: {...}, top_contributors: [...], completed_at }`.",
)
def get_underwriting_run(
    run_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    membership = db.query(OrganizationMember).filter(
        OrganizationMember.user_id == current_user.id
    ).first()
    if not membership:
        raise HTTPException(status_code=404, detail="Organization membership not found")

    run = db.query(UnderwritingRun).filter(
        UnderwritingRun.id == run_id,
        UnderwritingRun.organization_id == membership.organization_id,
    ).first()
    if not run:
        raise HTTPException(status_code=404, detail="Underwriting run not found")

    return {
        "id": run.id,
        "status": run.status,
        "kb_version": run.kb_version,
        "inputs": run.inputs,
        "portfolio_summary": run.outputs,
        "spine": run.spine_data,
        "decay": run.decay_data,
        "concentration": run.concentration_data,
        "projections": run.projection_data,
        "valuation": run.valuation_data,
        "exceptions": run.exceptions,
        "created_at": run.created_at.isoformat() if run.created_at else None,
        "completed_at": run.completed_at.isoformat() if run.completed_at else None,
    }


@router.get(
    "/underwriting/runs/{run_id}/spine",
    summary='Get the spine breakdown of an underwriting run',
    description='The "spine" is the cohort grouping used by the model — returns per-cohort cashflows, weights, and projected NPV.\n\n**Path parameter:** `run_id`.\n**Auth:** Bearer JWT — caller must be a member of the run\'s org.\n**Response:** `{ spine: [{cohort_label, weight, historical: [...], projected: [...], npv_cents}] }`.',
)
def get_underwriting_spine(
    run_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    membership = db.query(OrganizationMember).filter(
        OrganizationMember.user_id == current_user.id
    ).first()
    if not membership:
        raise HTTPException(status_code=404, detail="Organization membership not found")

    run = db.query(UnderwritingRun).filter(
        UnderwritingRun.id == run_id,
        UnderwritingRun.organization_id == membership.organization_id,
    ).first()
    if not run:
        raise HTTPException(status_code=404, detail="Underwriting run not found")

    return run.spine_data or {"entries": [], "total_entries": 0}


@router.get(
    "/underwriting/runs/{run_id}/decay",
    summary='Get the decay-curve fits from an underwriting run',
    description="Returns the per-cohort exponential decay parameters used to project earnings.\n\n**Path parameter:** `run_id`.\n**Auth:** Bearer JWT — caller must be a member of the run's org.\n**Response:** `{ fits: [{cohort_label, a, k, r2, data_points}] }`.",
)
def get_underwriting_decay(
    run_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    membership = db.query(OrganizationMember).filter(
        OrganizationMember.user_id == current_user.id
    ).first()
    if not membership:
        raise HTTPException(status_code=404, detail="Organization membership not found")

    run = db.query(UnderwritingRun).filter(
        UnderwritingRun.id == run_id,
        UnderwritingRun.organization_id == membership.organization_id,
    ).first()
    if not run:
        raise HTTPException(status_code=404, detail="Underwriting run not found")

    return run.decay_data or {}


@router.get(
    "/underwriting/runs/{run_id}/concentration",
    summary='Get the concentration risk metrics for an underwriting run',
    description="How concentrated catalog earnings are in a small set of songs/creators (HHI, top-N share, Gini coefficient).\n\n**Path parameter:** `run_id`.\n**Auth:** Bearer JWT — caller must be a member of the run's org.\n**Response:** `{ hhi, top10_share_pct, gini, top_concentrations: [...] }`.",
)
def get_underwriting_concentration(
    run_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    membership = db.query(OrganizationMember).filter(
        OrganizationMember.user_id == current_user.id
    ).first()
    if not membership:
        raise HTTPException(status_code=404, detail="Organization membership not found")

    run = db.query(UnderwritingRun).filter(
        UnderwritingRun.id == run_id,
        UnderwritingRun.organization_id == membership.organization_id,
    ).first()
    if not run:
        raise HTTPException(status_code=404, detail="Underwriting run not found")

    return run.concentration_data or {}


@router.get(
    "/underwriting/latest",
    summary='Get the latest underwriting run for the org',
    description="Convenience endpoint that returns the most recent completed run headline so dashboards don't have to list-then-fetch.\n\n**Query:** `org_id`.\n**Auth:** Bearer JWT — caller must be a member of the org.\n**Response:** same shape as `/runs/{run_id}` or `null` if no run exists yet.",
)
def get_latest_underwriting(
    scope_creator_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    membership = db.query(OrganizationMember).filter(
        OrganizationMember.user_id == current_user.id
    ).first()
    if not membership:
        raise HTTPException(status_code=404, detail="Organization membership not found")

    if scope_creator_id is not None:
        from ..models.models import Creator as _Creator
        belongs = db.query(_Creator.id).filter(
            _Creator.id == scope_creator_id,
            _Creator.organization_id == membership.organization_id,
        ).first()
        if not belongs:
            raise HTTPException(status_code=404, detail="Creator not found in this org")

    q = db.query(UnderwritingRun).filter(
        UnderwritingRun.organization_id == membership.organization_id,
        UnderwritingRun.status == "COMPLETED",
    )
    if scope_creator_id is not None:
        q = q.filter(UnderwritingRun.scope_creator_id == scope_creator_id)
    else:
        q = q.filter(UnderwritingRun.scope_creator_id.is_(None))
    run = q.order_by(UnderwritingRun.created_at.desc()).first()

    if not run:
        return {"has_data": False}

    return {
        "has_data": True,
        "run_id": run.id,
        "status": run.status,
        "kb_version": run.kb_version,
        "inputs": run.inputs,
        "portfolio_summary": run.outputs,
        "spine": run.spine_data,
        "decay": run.decay_data,
        "concentration": run.concentration_data,
        "projections": run.projection_data,
        "valuation": run.valuation_data,
        "exceptions": run.exceptions,
        "created_at": run.created_at.isoformat() if run.created_at else None,
        "completed_at": run.completed_at.isoformat() if run.completed_at else None,
    }


@router.get(
    "/statements/{statement_id}/reconciliation",
    summary='Get the reconciliation snapshot tied to a statement',
    description="Returns the underwriting-side reconciliation for a specific RoyaltyStatement (matched vs. unmatched cashflow, valuation adjustments).\n\n**Path parameter:** `statement_id`.\n**Auth:** Bearer JWT — caller must be a member of the statement's org.\n**Response:** `{ statement_id, reported_total, matched_total, valuation_delta }`.",
)
def get_statement_reconciliation(
    statement_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    membership = db.query(OrganizationMember).filter(
        OrganizationMember.user_id == current_user.id
    ).first()
    if not membership:
        raise HTTPException(status_code=404, detail="Organization membership not found")

    result = run_reconciliation_controls(db, statement_id, membership.organization_id)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    db.commit()
    return result


# ---------------------------------------------------------------------------
# Source-typed valuation engine (Task #162)
# ---------------------------------------------------------------------------

class SourceTypedRunRequest(BaseModel):
    scope_creator_id: Optional[int] = None
    scope_song_ids: Optional[List[int]] = None


def _scope_check_creator(db: Session, creator_id: int, org_id: int) -> None:
    from ..models.models import Creator as _Creator
    belongs = db.query(_Creator.id).filter(
        _Creator.id == creator_id,
        _Creator.organization_id == org_id,
    ).first()
    if not belongs:
        raise HTTPException(status_code=404, detail="Creator not found in this org")


def _serialize_source_typed_summary(
    org_id: int,
    db: Session,
    scope_creator_id: Optional[int],
    *,
    summary: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """If ``summary`` is supplied (fresh run) return its aggregated
    shape directly. Otherwise re-aggregate the most recent
    source-typed ``ValuationCalculation`` row per song so the
    ``/summary`` endpoint can serve the latest persisted result
    without recomputing.
    """
    if summary is not None:
        return {
            "computed_at": summary["computed_at"],
            "song_count": summary["song_count"],
            "songs_with_revenue": summary["songs_with_revenue"],
            "by_bucket": summary["by_bucket"],
            "total_annual_revenue_cents": summary["total_annual_revenue_cents"],
            "total_value_cents": summary["total_value_cents"],
            "artist_total_value_cents": summary["artist_total_value_cents"],
            "publisher_total_value_cents": summary["publisher_total_value_cents"],
            "scope": summary["scope"],
            "fresh": True,
        }

    # Re-aggregate from the latest source-typed row per song.
    q = db.query(ValuationCalculation).filter(
        ValuationCalculation.organization_id == org_id,
        ValuationCalculation.valuation_method == "SOURCE_TYPED",
    )

    scoped_song_ids: Optional[set] = None
    if scope_creator_id is not None:
        from ..models.models import SongCredit as _SongCredit
        scoped_song_ids = {
            sid for (sid,) in db.query(_SongCredit.song_id)
            .filter(_SongCredit.creator_id == scope_creator_id)
            .distinct()
            .all()
        }
        if scoped_song_ids:
            q = q.filter(ValuationCalculation.song_id.in_(scoped_song_ids))
        else:
            q = q.filter(False)

    rows = q.order_by(ValuationCalculation.calculation_date.desc()).all()
    latest_per_song: Dict[int, ValuationCalculation] = {}
    for r in rows:
        if r.song_id not in latest_per_song:
            latest_per_song[r.song_id] = r

    if not latest_per_song:
        return {
            "computed_at": None,
            "song_count": 0,
            "songs_with_revenue": 0,
            "by_bucket": {
                b: {"revenue_cents": 0, "multiplier": None, "value_cents": 0}
                for b in ("performance", "mechanical", "sync", "streaming", "other")
            },
            "total_annual_revenue_cents": 0,
            "total_value_cents": 0,
            "artist_total_value_cents": 0,
            "publisher_total_value_cents": 0,
            "scope": {"creator_id": scope_creator_id, "song_ids": None},
            "fresh": False,
        }

    by_bucket: Dict[str, Dict[str, Any]] = {
        b: {"revenue_cents": 0, "value_cents": 0, "multiplier": None}
        for b in ("performance", "mechanical", "sync", "streaming", "other")
    }
    total_value = 0
    total_revenue = 0
    artist_total = 0
    publisher_total = 0
    songs_with_revenue = 0
    latest_calc = None

    for r in latest_per_song.values():
        # Multiplier values are constants per bucket; pick from any row.
        if by_bucket["performance"]["multiplier"] is None and r.multiplier_performance is not None:
            by_bucket["performance"]["multiplier"] = r.multiplier_performance
            by_bucket["mechanical"]["multiplier"] = r.multiplier_mechanical
            by_bucket["sync"]["multiplier"] = r.multiplier_sync
            by_bucket["streaming"]["multiplier"] = r.multiplier_streaming

        for col, bucket in (
            ("revenue_performance_cents", "performance"),
            ("revenue_mechanical_cents", "mechanical"),
            ("revenue_sync_cents", "sync"),
            ("revenue_streaming_cents", "streaming"),
            ("revenue_other_cents", "other"),
        ):
            v = getattr(r, col, 0) or 0
            by_bucket[bucket]["revenue_cents"] += int(v)

        for bucket in ("performance", "mechanical", "sync", "streaming"):
            mult = by_bucket[bucket]["multiplier"] or 0
            rev = getattr(
                r, f"revenue_{bucket}_cents"
            ) or 0
            by_bucket[bucket]["value_cents"] += int(round(rev * mult))

        total_value += int(r.final_valuation_cents or 0)
        total_revenue += int(r.annual_revenue_cents or 0)
        artist_total += int(r.artist_valuation_cents or 0)
        publisher_total += int(r.publisher_valuation_cents or 0)
        if (r.annual_revenue_cents or 0) > 0:
            songs_with_revenue += 1
        if latest_calc is None or (r.calculation_date and r.calculation_date > latest_calc):
            latest_calc = r.calculation_date

    return {
        "computed_at": latest_calc.isoformat() if latest_calc else None,
        "song_count": len(latest_per_song),
        "songs_with_revenue": songs_with_revenue,
        "by_bucket": by_bucket,
        "total_annual_revenue_cents": total_revenue,
        "total_value_cents": total_value,
        "artist_total_value_cents": artist_total,
        "publisher_total_value_cents": publisher_total,
        "scope": {"creator_id": scope_creator_id, "song_ids": None},
        "fresh": False,
    }


@router.post(
    "/source-typed/run",
    summary="Run the source-typed valuation engine for the org (or scoped to a creator/song list)",
    description="Computes annualized revenue per right-category bucket from matched royalty statements, applies industry multipliers (performance 10x, mechanical 9x, sync 7x, streaming 12.5x), and splits each song's value into artist (MASTER) vs publisher (PUBLISHING) shares from RightsSplit rows. Persists one ValuationCalculation row per song with valuation_method='SOURCE_TYPED'.\n\n**Body:** `{ scope_creator_id?, scope_song_ids?: int[] }`.\n**Auth:** Bearer JWT — caller must be a member of the org.",
)
def run_source_typed_valuation(
    request: SourceTypedRunRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    membership = db.query(OrganizationMember).filter(
        OrganizationMember.user_id == current_user.id
    ).first()
    if not membership:
        raise HTTPException(status_code=404, detail="Organization membership not found")

    if request.scope_creator_id is not None:
        _scope_check_creator(db, request.scope_creator_id, membership.organization_id)

    try:
        summary = compute_source_typed_valuation(
            db,
            org_id=membership.organization_id,
            scope_creator_id=request.scope_creator_id,
            scope_song_ids=request.scope_song_ids,
            persist=True,
        )
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Source-typed valuation failed: {e}")

    return _serialize_source_typed_summary(
        membership.organization_id,
        db,
        request.scope_creator_id,
        summary=summary,
    )


@router.get(
    "/source-typed/summary",
    summary="Get the latest persisted source-typed valuation breakdown",
    description="Aggregates the most recent source-typed ValuationCalculation row per song into a single org-wide (or per-creator) breakdown. Useful for dashboards that want the current numbers without re-running the engine.\n\n**Query:** `scope_creator_id?`.\n**Auth:** Bearer JWT — caller must be a member of the org.",
)
def get_source_typed_summary(
    scope_creator_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    membership = db.query(OrganizationMember).filter(
        OrganizationMember.user_id == current_user.id
    ).first()
    if not membership:
        raise HTTPException(status_code=404, detail="Organization membership not found")

    if scope_creator_id is not None:
        _scope_check_creator(db, scope_creator_id, membership.organization_id)

    return _serialize_source_typed_summary(
        membership.organization_id,
        db,
        scope_creator_id,
    )
