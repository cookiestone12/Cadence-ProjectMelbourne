from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func, extract, case, and_, or_, distinct
from datetime import datetime, timedelta, date
from collections import defaultdict

from ..models import (
    get_db, User, OrganizationMember, Song, Creator, SongCredit,
    Work, WorkTrack, Release, ReleaseTrack,
    Contract, ContractAsset, RightsSplit,
    RoyaltyStatement, RoyaltyTransaction, RoyaltyAllocation,
    Placement, ActionItem, Payment,
    ValuationCalculation, SongValuationSnapshot, Organization
)
from ..utils.auth import get_current_user

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


def verify_org_access(db: Session, user_id: int, org_id: int):
    member = db.query(OrganizationMember).filter(
        OrganizationMember.user_id == user_id,
        OrganizationMember.organization_id == org_id
    ).first()
    if not member:
        raise HTTPException(status_code=403, detail="Not a member of this organization")
    return member


@router.get("/org/{org_id}/overview")
def get_overview_analytics(org_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    verify_org_access(db, current_user.id, org_id)

    total_songs = db.query(func.count(Song.id)).filter(Song.organization_id == org_id).scalar() or 0
    total_works = db.query(func.count(Work.id)).filter(Work.organization_id == org_id).scalar() or 0
    total_releases = db.query(func.count(Release.id)).filter(Release.organization_id == org_id).scalar() or 0
    total_creators = db.query(func.count(Creator.id)).filter(Creator.organization_id == org_id).scalar() or 0
    total_contracts = db.query(func.count(Contract.id)).filter(Contract.organization_id == org_id).scalar() or 0
    total_placements = db.query(func.count(Placement.id)).filter(Placement.organization_id == org_id).scalar() or 0

    avg_health = db.query(func.avg(Song.status_health_score)).filter(Song.organization_id == org_id).scalar() or 0
    released_count = db.query(func.count(Song.id)).filter(Song.organization_id == org_id, Song.is_released == True).scalar() or 0

    total_revenue_cents = db.query(func.sum(RoyaltyTransaction.revenue_cents)).filter(
        RoyaltyTransaction.organization_id == org_id
    ).scalar() or 0

    total_placement_value = db.query(func.sum(Placement.license_fee)).filter(
        Placement.organization_id == org_id,
        Placement.license_fee.isnot(None)
    ).scalar() or 0

    active_contracts = db.query(func.count(Contract.id)).filter(
        Contract.organization_id == org_id,
        Contract.status == "ACTIVE"
    ).scalar() or 0

    pending_actions = db.query(func.count(ActionItem.id)).filter(
        ActionItem.organization_id == org_id,
        ActionItem.status == "PENDING"
    ).scalar() or 0

    return {
        "totals": {
            "songs": total_songs,
            "works": total_works,
            "releases": total_releases,
            "creators": total_creators,
            "contracts": total_contracts,
            "placements": total_placements,
        },
        "health": {
            "avg_score": round(float(avg_health), 1),
            "released_songs": released_count,
            "release_rate": round((released_count / total_songs * 100) if total_songs > 0 else 0, 1),
        },
        "financial": {
            "total_royalty_revenue": int(total_revenue_cents),
            "total_placement_value": float(total_placement_value),
            "active_contracts": active_contracts,
        },
        "tasks": {
            "pending_actions": pending_actions,
        }
    }


@router.get("/org/{org_id}/catalog-growth")
def get_catalog_growth(org_id: int, months: int = 12, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    verify_org_access(db, current_user.id, org_id)

    cutoff = datetime.utcnow() - timedelta(days=months * 30)

    songs_by_month = db.query(
        func.date_trunc('month', Song.created_at).label('month'),
        func.count(Song.id).label('count')
    ).filter(
        Song.organization_id == org_id,
        Song.created_at >= cutoff
    ).group_by('month').order_by('month').all()

    works_by_month = db.query(
        func.date_trunc('month', Work.created_at).label('month'),
        func.count(Work.id).label('count')
    ).filter(
        Work.organization_id == org_id,
        Work.created_at >= cutoff
    ).group_by('month').order_by('month').all()

    releases_by_month = db.query(
        func.date_trunc('month', Release.created_at).label('month'),
        func.count(Release.id).label('count')
    ).filter(
        Release.organization_id == org_id,
        Release.created_at >= cutoff
    ).group_by('month').order_by('month').all()

    months_map = defaultdict(lambda: {"songs": 0, "works": 0, "releases": 0})
    for row in songs_by_month:
        key = row.month.strftime("%Y-%m") if row.month else "Unknown"
        months_map[key]["songs"] = row.count
    for row in works_by_month:
        key = row.month.strftime("%Y-%m") if row.month else "Unknown"
        months_map[key]["works"] = row.count
    for row in releases_by_month:
        key = row.month.strftime("%Y-%m") if row.month else "Unknown"
        months_map[key]["releases"] = row.count

    timeline = []
    for month_key in sorted(months_map.keys()):
        data = months_map[month_key]
        timeline.append({
            "month": month_key,
            "songs": data["songs"],
            "works": data["works"],
            "releases": data["releases"],
        })

    return {"timeline": timeline}


@router.get("/org/{org_id}/health-distribution")
def get_health_distribution(org_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    verify_org_access(db, current_user.id, org_id)

    songs = db.query(Song.status_health_score).filter(Song.organization_id == org_id).all()

    distribution = [
        {"name": "Critical (0-25%)", "value": 0, "color": "#C47068"},
        {"name": "Needs Work (25-50%)", "value": 0, "color": "#C4956B"},
        {"name": "Good (50-75%)", "value": 0, "color": "#5A8A9A"},
        {"name": "Excellent (75-100%)", "value": 0, "color": "#5B9A6E"},
    ]

    for (score,) in songs:
        s = score or 0
        if s < 25:
            distribution[0]["value"] += 1
        elif s < 50:
            distribution[1]["value"] += 1
        elif s < 75:
            distribution[2]["value"] += 1
        else:
            distribution[3]["value"] += 1

    missing_isrc = db.query(func.count(Song.id)).filter(
        Song.organization_id == org_id,
        or_(Song.isrc == None, Song.isrc == "")
    ).scalar() or 0

    missing_iswc = db.query(func.count(Song.id)).filter(
        Song.organization_id == org_id,
        or_(Song.iswc == None, Song.iswc == "")
    ).scalar() or 0

    no_contract = db.query(func.count(Song.id)).filter(
        Song.organization_id == org_id,
        Song.has_contract_executed == False
    ).scalar() or 0

    not_registered_pro = db.query(func.count(Song.id)).filter(
        Song.organization_id == org_id,
        Song.is_registered_with_pro == False
    ).scalar() or 0

    return {
        "distribution": distribution,
        "gaps": {
            "missing_isrc": missing_isrc,
            "missing_iswc": missing_iswc,
            "no_contract": no_contract,
            "not_registered_pro": not_registered_pro,
        }
    }


@router.get("/org/{org_id}/revenue")
def get_revenue_analytics(org_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    verify_org_access(db, current_user.id, org_id)

    revenue_by_month = db.query(
        func.date_trunc('month', RoyaltyStatement.period_start).label('month'),
        func.sum(RoyaltyStatement.total_revenue_cents).label('revenue')
    ).filter(
        RoyaltyStatement.organization_id == org_id,
        RoyaltyStatement.period_start.isnot(None)
    ).group_by('month').order_by('month').all()

    monthly_revenue = []
    for row in revenue_by_month:
        monthly_revenue.append({
            "month": row.month.strftime("%Y-%m") if row.month else "Unknown",
            "revenue": int(row.revenue or 0),
        })

    top_tracks = db.query(
        Song.title,
        Song.primary_artist,
        func.sum(RoyaltyTransaction.revenue_cents).label('total_revenue')
    ).join(
        RoyaltyTransaction, RoyaltyTransaction.song_id == Song.id
    ).filter(
        Song.organization_id == org_id
    ).group_by(Song.id, Song.title, Song.primary_artist).order_by(
        func.sum(RoyaltyTransaction.revenue_cents).desc()
    ).limit(10).all()

    top_tracks_data = [
        {"title": t.title, "artist": t.primary_artist, "revenue": int(t.total_revenue or 0)}
        for t in top_tracks
    ]

    revenue_by_platform = db.query(
        RoyaltyTransaction.platform,
        func.sum(RoyaltyTransaction.revenue_cents).label('revenue')
    ).filter(
        RoyaltyTransaction.organization_id == org_id,
        RoyaltyTransaction.platform.isnot(None)
    ).group_by(RoyaltyTransaction.platform).order_by(
        func.sum(RoyaltyTransaction.revenue_cents).desc()
    ).limit(10).all()

    platform_data = [
        {"platform": r.platform or "Unknown", "revenue": int(r.revenue or 0)}
        for r in revenue_by_platform
    ]

    revenue_by_territory = db.query(
        RoyaltyTransaction.territory,
        func.sum(RoyaltyTransaction.revenue_cents).label('revenue')
    ).filter(
        RoyaltyTransaction.organization_id == org_id,
        RoyaltyTransaction.territory.isnot(None)
    ).group_by(RoyaltyTransaction.territory).order_by(
        func.sum(RoyaltyTransaction.revenue_cents).desc()
    ).limit(10).all()

    territory_data = [
        {"territory": r.territory or "Unknown", "revenue": int(r.revenue or 0)}
        for r in revenue_by_territory
    ]

    total_revenue = db.query(func.sum(RoyaltyTransaction.revenue_cents)).filter(
        RoyaltyTransaction.organization_id == org_id
    ).scalar() or 0

    total_paid = db.query(func.sum(Payment.amount_cents)).filter(
        Payment.organization_id == org_id,
        Payment.status == "COMPLETED"
    ).scalar() or 0

    return {
        "monthly_revenue": monthly_revenue,
        "top_tracks": top_tracks_data,
        "by_platform": platform_data,
        "by_territory": territory_data,
        "totals": {
            "total_revenue": int(total_revenue),
            "total_paid": int(total_paid),
            "unpaid": int(total_revenue) - int(total_paid),
        }
    }


@router.get("/org/{org_id}/creators")
def get_creator_analytics(org_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    verify_org_access(db, current_user.id, org_id)

    creators = db.query(Creator).filter(Creator.organization_id == org_id).all()

    creator_stats = []
    for c in creators:
        song_count = db.query(func.count(distinct(SongCredit.song_id))).filter(
            SongCredit.creator_id == c.id
        ).scalar() or 0

        work_count = db.query(func.count(distinct(Work.id))).join(
            WorkTrack, WorkTrack.work_id == Work.id
        ).join(
            SongCredit, and_(
                SongCredit.song_id == WorkTrack.song_id,
                SongCredit.creator_id == c.id
            )
        ).scalar() or 0

        song_ids = db.query(SongCredit.song_id).filter(SongCredit.creator_id == c.id).subquery()
        avg_health = db.query(func.avg(Song.status_health_score)).filter(
            Song.id.in_(song_ids)
        ).scalar() or 0

        revenue = db.query(func.sum(RoyaltyTransaction.revenue_cents)).filter(
            RoyaltyTransaction.song_id.in_(song_ids),
            RoyaltyTransaction.organization_id == org_id
        ).scalar() or 0

        creator_stats.append({
            "id": c.id,
            "name": c.display_name,
            "roles": c.roles or [],
            "song_count": song_count,
            "work_count": work_count,
            "avg_health": round(float(avg_health), 1),
            "total_revenue": int(revenue),
        })

    creator_stats.sort(key=lambda x: x["song_count"], reverse=True)

    by_role = defaultdict(int)
    for c in creators:
        for role in (c.roles or []):
            by_role[role] += 1

    by_pro = defaultdict(int)
    for c in creators:
        if c.primary_pro:
            by_pro[c.primary_pro] += 1

    return {
        "creators": creator_stats[:20],
        "total_creators": len(creators),
        "by_role": dict(by_role),
        "by_pro": dict(by_pro),
    }


@router.get("/org/{org_id}/placements")
def get_placement_analytics(org_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    verify_org_access(db, current_user.id, org_id)

    placements = db.query(Placement).filter(Placement.organization_id == org_id).all()

    by_status = defaultdict(int)
    by_type = defaultdict(int)
    by_type_value = defaultdict(float)
    total_value = 0
    secured_value = 0
    paid_value = 0

    for p in placements:
        by_status[p.status] += 1
        by_type[p.placement_type] += 1
        fee = float(p.license_fee or 0)
        by_type_value[p.placement_type] += fee
        total_value += fee
        if p.status in ("SECURED", "DELIVERED", "AIRED", "PAID"):
            secured_value += fee
        if p.status == "PAID":
            paid_value += fee

    funnel_stages = ["PITCHED", "IN_REVIEW", "IN_NEGOTIATION", "SECURED", "DELIVERED", "AIRED", "PAID"]
    funnel = [{"stage": s, "count": by_status.get(s, 0)} for s in funnel_stages]

    conversion_rate = 0
    pitched = by_status.get("PITCHED", 0) + by_status.get("IN_REVIEW", 0) + by_status.get("IN_NEGOTIATION", 0) + by_status.get("SECURED", 0) + by_status.get("DELIVERED", 0) + by_status.get("AIRED", 0) + by_status.get("PAID", 0)
    secured_total = by_status.get("SECURED", 0) + by_status.get("DELIVERED", 0) + by_status.get("AIRED", 0) + by_status.get("PAID", 0)
    if pitched > 0:
        conversion_rate = round(secured_total / pitched * 100, 1)

    type_breakdown = [
        {"type": t, "count": by_type[t], "value": round(by_type_value[t], 2)}
        for t in sorted(by_type.keys())
    ]

    placements_by_month = defaultdict(int)
    for p in placements:
        if p.created_at:
            key = p.created_at.strftime("%Y-%m")
            placements_by_month[key] += 1

    monthly_activity = [
        {"month": m, "count": c}
        for m, c in sorted(placements_by_month.items())
    ]

    return {
        "funnel": funnel,
        "by_type": type_breakdown,
        "monthly_activity": monthly_activity,
        "totals": {
            "total": len(placements),
            "total_value": round(total_value, 2),
            "secured_value": round(secured_value, 2),
            "paid_value": round(paid_value, 2),
            "conversion_rate": conversion_rate,
        },
        "by_status": dict(by_status),
    }


@router.get("/org/{org_id}/rights-coverage")
def get_rights_coverage(org_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    verify_org_access(db, current_user.id, org_id)

    total_songs = db.query(func.count(Song.id)).filter(Song.organization_id == org_id).scalar() or 0

    songs_with_contracts = db.query(func.count(distinct(ContractAsset.song_id))).join(
        Contract, Contract.id == ContractAsset.contract_id
    ).filter(
        Contract.organization_id == org_id,
        ContractAsset.song_id.isnot(None)
    ).scalar() or 0

    songs_with_splits = db.query(func.count(distinct(RightsSplit.song_id))).join(
        Contract, Contract.id == RightsSplit.contract_id
    ).filter(
        Contract.organization_id == org_id,
        RightsSplit.song_id.isnot(None)
    ).scalar() or 0

    contracts_by_status = db.query(
        Contract.status, func.count(Contract.id)
    ).filter(Contract.organization_id == org_id).group_by(Contract.status).all()

    contracts_by_type = db.query(
        Contract.contract_type, func.count(Contract.id)
    ).filter(Contract.organization_id == org_id).group_by(Contract.contract_type).all()

    expiring_soon = db.query(func.count(Contract.id)).filter(
        Contract.organization_id == org_id,
        Contract.status == "ACTIVE",
        Contract.end_date.isnot(None),
        Contract.end_date <= date.today() + timedelta(days=90)
    ).scalar() or 0

    return {
        "coverage": {
            "total_songs": total_songs,
            "songs_with_contracts": songs_with_contracts,
            "songs_with_splits": songs_with_splits,
            "contract_coverage_rate": round((songs_with_contracts / total_songs * 100) if total_songs > 0 else 0, 1),
            "splits_coverage_rate": round((songs_with_splits / total_songs * 100) if total_songs > 0 else 0, 1),
        },
        "contracts_by_status": {s: c for s, c in contracts_by_status},
        "contracts_by_type": {t: c for t, c in contracts_by_type},
        "expiring_soon": expiring_soon,
    }


@router.get("/org/{org_id}/valuation")
def get_valuation_analytics(org_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    verify_org_access(db, current_user.id, org_id)

    from sqlalchemy.orm import aliased

    latest_vals = db.query(
        ValuationCalculation.song_id,
        func.max(ValuationCalculation.id).label('max_id')
    ).filter(
        ValuationCalculation.organization_id == org_id
    ).group_by(ValuationCalculation.song_id).subquery()

    valuations = db.query(ValuationCalculation).join(
        latest_vals, ValuationCalculation.id == latest_vals.c.max_id
    ).all()

    total_valuation = sum(v.final_valuation_cents or 0 for v in valuations)
    total_streaming = sum(v.streaming_multiple_value_cents or 0 for v in valuations)
    total_revenue_mult = sum(v.revenue_multiple_value_cents or 0 for v in valuations)
    total_market = sum(v.market_comp_value_cents or 0 for v in valuations)
    total_blackbox = sum(v.black_box_value_cents or 0 for v in valuations)

    top_songs = sorted(valuations, key=lambda v: v.final_valuation_cents or 0, reverse=True)[:10]
    top_songs_data = []
    for v in top_songs:
        song = db.query(Song.title, Song.primary_artist).filter(Song.id == v.song_id).first()
        if song:
            top_songs_data.append({
                "song_id": v.song_id,
                "title": song.title,
                "artist": song.primary_artist,
                "valuation_cents": v.final_valuation_cents or 0,
            })

    return {
        "total_valuation_cents": total_valuation,
        "songs_valued": len(valuations),
        "methodology_breakdown": {
            "streaming_multiple": total_streaming,
            "revenue_multiple": total_revenue_mult,
            "market_comparables": total_market,
            "black_box": total_blackbox,
        },
        "top_valued_songs": top_songs_data,
    }


@router.get("/org/{org_id}/expiring-contracts")
def get_expiring_contracts(org_id: int, days: int = 90, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    verify_org_access(db, current_user.id, org_id)

    cutoff = date.today() + timedelta(days=days)

    contracts = db.query(Contract).filter(
        Contract.organization_id == org_id,
        Contract.status == "ACTIVE",
        Contract.end_date.isnot(None),
        Contract.end_date <= cutoff
    ).order_by(Contract.end_date.asc()).all()

    result = []
    for c in contracts:
        asset_count = db.query(func.count(ContractAsset.id)).filter(
            ContractAsset.contract_id == c.id
        ).scalar() or 0

        days_remaining = (c.end_date - date.today()).days if c.end_date else None

        result.append({
            "id": c.id,
            "title": c.title,
            "contract_type": c.contract_type,
            "end_date": c.end_date.isoformat() if c.end_date else None,
            "days_remaining": days_remaining,
            "asset_count": asset_count,
            "status": c.status,
        })

    return {"contracts": result}


@router.get("/admin/platform-stats")
def get_platform_stats(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if not current_user.is_super_admin:
        raise HTTPException(status_code=403, detail="Super admin access required")

    total_users = db.query(func.count(User.id)).scalar() or 0
    total_orgs = db.query(func.count(Organization.id)).scalar() or 0
    total_songs = db.query(func.count(Song.id)).scalar() or 0
    total_works = db.query(func.count(Work.id)).scalar() or 0
    total_releases = db.query(func.count(Release.id)).scalar() or 0
    total_contracts = db.query(func.count(Contract.id)).scalar() or 0
    total_placements = db.query(func.count(Placement.id)).scalar() or 0
    total_revenue = db.query(func.sum(RoyaltyTransaction.revenue_cents)).scalar() or 0

    top_orgs = db.query(
        Organization.id,
        Organization.name,
        func.count(Song.id).label('song_count')
    ).outerjoin(Song, Song.organization_id == Organization.id).group_by(
        Organization.id, Organization.name
    ).order_by(func.count(Song.id).desc()).limit(10).all()

    top_orgs_data = [{"id": o.id, "name": o.name or "Unnamed", "song_count": o.song_count} for o in top_orgs]

    recent_orgs = db.query(
        Organization.id,
        Organization.name,
        func.max(Song.created_at).label('last_activity')
    ).outerjoin(Song, Song.organization_id == Organization.id).group_by(
        Organization.id, Organization.name
    ).order_by(func.max(Song.created_at).desc().nullslast()).limit(10).all()

    recent_activity = [
        {"id": o.id, "name": o.name, "last_activity": o.last_activity.isoformat() if o.last_activity else None}
        for o in recent_orgs
    ]

    return {
        "totals": {
            "users": total_users,
            "organizations": total_orgs,
            "songs": total_songs,
            "works": total_works,
            "releases": total_releases,
            "contracts": total_contracts,
            "placements": total_placements,
            "total_revenue_cents": int(total_revenue),
        },
        "top_orgs": top_orgs_data,
        "recent_activity": recent_activity,
    }


@router.get("/org/{org_id}/export/{report_type}")
def export_analytics(org_id: int, report_type: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    verify_org_access(db, current_user.id, org_id)

    import csv
    import io
    from fastapi.responses import StreamingResponse

    if report_type == "catalog-summary":
        songs = db.query(Song).filter(Song.organization_id == org_id).all()
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["Title", "Artist", "ISRC", "ISWC", "Health Score", "Released", "Release Date", "Created"])
        for s in songs:
            writer.writerow([s.title, s.primary_artist, s.isrc or "", s.iswc or "",
                           round(s.status_health_score or 0, 1), "Yes" if s.is_released else "No",
                           s.release_date.isoformat() if s.release_date else "",
                           s.created_at.strftime("%Y-%m-%d") if s.created_at else ""])
        output.seek(0)
        return StreamingResponse(io.BytesIO(output.getvalue().encode()), media_type="text/csv",
                                headers={"Content-Disposition": f"attachment; filename=catalog-summary-{org_id}.csv"})

    elif report_type == "revenue-summary":
        transactions = db.query(
            Song.title, Song.primary_artist, RoyaltyTransaction.platform,
            RoyaltyTransaction.territory, RoyaltyTransaction.revenue_cents
        ).outerjoin(Song, Song.id == RoyaltyTransaction.song_id).filter(
            RoyaltyTransaction.organization_id == org_id
        ).all()
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["Track", "Artist", "Platform", "Territory", "Revenue"])
        for t in transactions:
            writer.writerow([t.title or "Unknown", t.primary_artist or "", t.platform or "",
                           t.territory or "", round((t.revenue_cents or 0) / 100, 2)])
        output.seek(0)
        return StreamingResponse(io.BytesIO(output.getvalue().encode()), media_type="text/csv",
                                headers={"Content-Disposition": f"attachment; filename=revenue-summary-{org_id}.csv"})

    elif report_type == "creators-summary":
        creators = db.query(Creator).filter(Creator.organization_id == org_id).all()
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["Name", "Legal Name", "Email", "Roles", "PRO", "IPI", "Territory"])
        for c in creators:
            writer.writerow([c.display_name, c.legal_name or "", c.email or "",
                           ", ".join(c.roles or []), c.primary_pro or "", c.primary_ipi or "",
                           c.primary_territory or ""])
        output.seek(0)
        return StreamingResponse(io.BytesIO(output.getvalue().encode()), media_type="text/csv",
                                headers={"Content-Disposition": f"attachment; filename=creators-summary-{org_id}.csv"})

    elif report_type == "contracts-summary":
        contracts = db.query(Contract).filter(Contract.organization_id == org_id).all()
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["Title", "Type", "Status", "Start Date", "End Date", "Territory", "Advance"])
        for c in contracts:
            writer.writerow([c.title, c.contract_type or "", c.status or "",
                           c.start_date.isoformat() if c.start_date else "",
                           c.end_date.isoformat() if c.end_date else "",
                           c.territory or "", float(c.advance_amount or 0)])
        output.seek(0)
        return StreamingResponse(io.BytesIO(output.getvalue().encode()), media_type="text/csv",
                                headers={"Content-Disposition": f"attachment; filename=contracts-summary-{org_id}.csv"})

    elif report_type == "placements-summary":
        placements = db.query(Placement).filter(Placement.organization_id == org_id).all()
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["Title", "Type", "Status", "Client", "Project", "License Fee", "Currency", "Pitched Date", "Secured Date"])
        for p in placements:
            writer.writerow([p.title, p.placement_type or "", p.status or "",
                           p.client_name or "", p.project_name or "",
                           float(p.license_fee or 0), p.license_currency or "USD",
                           p.pitched_date.isoformat() if p.pitched_date else "",
                           p.secured_date.isoformat() if p.secured_date else ""])
        output.seek(0)
        return StreamingResponse(io.BytesIO(output.getvalue().encode()), media_type="text/csv",
                                headers={"Content-Disposition": f"attachment; filename=placements-summary-{org_id}.csv"})

    else:
        raise HTTPException(status_code=400, detail=f"Unknown report type: {report_type}")
