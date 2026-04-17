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

@router.get("/catalog/summary")
def get_catalog_valuation_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get comprehensive catalog valuation summary for the organization"""
    
    membership = db.query(OrganizationMember).filter(
        OrganizationMember.user_id == current_user.id
    ).first()
    
    if not membership:
        raise HTTPException(status_code=404, detail="Organization membership not found")
    
    org = db.query(Organization).filter(Organization.id == membership.organization_id).first()
    
    songs = db.query(Song).filter(Song.organization_id == org.id).all()
    
    valuations = db.query(ValuationCalculation).filter(
        ValuationCalculation.organization_id == org.id
    ).order_by(ValuationCalculation.calculation_date.desc()).all()
    
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
    
    territory_data = db.query(
        TerritoryRevenue.territory_code,
        TerritoryRevenue.territory_name,
        func.sum(TerritoryRevenue.total_streams).label("total_streams"),
        func.sum(TerritoryRevenue.publishing_revenue_cents).label("publishing_revenue_cents"),
        func.sum(TerritoryRevenue.master_revenue_cents).label("master_revenue_cents"),
        func.sum(TerritoryRevenue.total_revenue_cents).label("total_revenue_cents")
    ).filter(
        TerritoryRevenue.organization_id == org.id
    ).group_by(
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

@router.get("/song/{song_id}/detail")
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

@router.get("/catalog/download/excel")
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


@router.post("/underwriting/run")
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


@router.get("/underwriting/runs")
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

    return [
        {
            "id": r.id,
            "status": r.status,
            "kb_version": r.kb_version,
            "inputs": r.inputs,
            "portfolio_summary": r.outputs,
            "valuation": r.valuation_data.get("blended") if r.valuation_data else None,
            "created_at": r.created_at.isoformat() if r.created_at else None,
            "completed_at": r.completed_at.isoformat() if r.completed_at else None,
        }
        for r in runs
    ]


@router.get("/underwriting/runs/{run_id}")
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


@router.get("/underwriting/runs/{run_id}/spine")
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


@router.get("/underwriting/runs/{run_id}/decay")
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


@router.get("/underwriting/runs/{run_id}/concentration")
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


@router.get("/underwriting/latest")
def get_latest_underwriting(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    membership = db.query(OrganizationMember).filter(
        OrganizationMember.user_id == current_user.id
    ).first()
    if not membership:
        raise HTTPException(status_code=404, detail="Organization membership not found")

    run = db.query(UnderwritingRun).filter(
        UnderwritingRun.organization_id == membership.organization_id,
        UnderwritingRun.status == "COMPLETED",
    ).order_by(UnderwritingRun.created_at.desc()).first()

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


@router.get("/statements/{statement_id}/reconciliation")
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
