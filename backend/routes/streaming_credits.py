from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
import bcrypt
import logging

from ..models.database import get_db
from ..models.models import (
    User, OrganizationMember, Creator, CreatorCreditsProfile,
    ChartSource, ChartEntry, StreamEstimate,
)
from .auth import get_current_user
from .client_sharing import has_shared_access

logger = logging.getLogger("cadence")

router = APIRouter(prefix="/api/streaming-credits", tags=["Streaming Credits"])
public_router = APIRouter(prefix="/api/public", tags=["Streaming Credits"])
admin_chart_router = APIRouter(prefix="/api/admin/charts", tags=["Streaming Credits"])


def _verify_org_access(user: User, org_id: int, db: Session, creator_id: int = None):
    membership = db.query(OrganizationMember).filter(
        OrganizationMember.user_id == user.id,
        OrganizationMember.organization_id == org_id,
    ).first()
    if not membership and not user.is_super_admin:
        if creator_id and has_shared_access(db, user.id, creator_id, required_module="catalog"):
            return None
        raise HTTPException(status_code=403, detail="Not a member of this organization")
    return membership


@router.get(
    "/org/{org_id}/overview",
    summary='Get the org-wide streaming credits overview',
    description='Returns the dashboard for songwriter/producer credits scraped from DSPs (Spotify/Apple) — total credited tracks per creator and missing-credit counts.\n\n**Path parameter:** `org_id`.\n**Query:** `dsp` (`spotify|apple|all`), `start_date`, `end_date`.\n**Auth:** Bearer JWT — caller must be a member of the org.\n**Response:** `{ creators: [{creator_id, name, total_credits, by_dsp: {...}, missing_count}] }`.',
)
def credits_overview(
    org_id: int,
    search: str = Query(None),
    sort_by: str = Query("streams"),
    force_refresh: bool = Query(False),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _verify_org_access(user, org_id, db)

    from ..services.credits_service import get_credits_overview, compute_all_creators
    from ..services.stream_estimator import estimate_all_songs

    results = get_credits_overview(org_id, db, search=search, sort_by=sort_by)

    if force_refresh:
        estimate_all_songs(org_id, db)
        compute_all_creators(org_id, db)
        results = get_credits_overview(org_id, db, search=search, sort_by=sort_by)
    elif not results:
        import threading
        from ..models.database import SessionLocal

        def _background_refresh(o_id):
            try:
                bg_db = SessionLocal()
                estimate_all_songs(o_id, bg_db)
                compute_all_creators(o_id, bg_db)
                bg_db.close()
                logger.info(f"Background credits refresh completed for org {o_id}")
            except Exception as e:
                logger.error(f"Background credits refresh failed for org {o_id}: {e}")

        thread = threading.Thread(target=_background_refresh, args=(org_id,), daemon=True)
        thread.start()

    return {"creators": results, "total": len(results)}


@router.get(
    "/org/{org_id}/creator/{creator_id}",
    summary="Get a creator's streaming-credits detail summary",
    description='Per-creator rollup: credit counts by DSP, by role (writer / producer / etc.), recently scraped, and pending claim issues.\n\n**Path parameters:** `org_id`, `creator_id`.\n**Auth:** Bearer JWT — caller must be a member of the org.\n**Response:** `{ creator_id, name, summary: {...}, pending: [...], last_scraped_at }`.',
)
def creator_credits_detail(
    org_id: int,
    creator_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _verify_org_access(user, org_id, db, creator_id=creator_id)

    from ..services.credits_service import get_credits_summary
    result = get_credits_summary(creator_id, org_id, db)
    if result.get("error"):
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@router.get(
    "/org/{org_id}/creator/{creator_id}/songs",
    summary='List the songs a creator has streaming credits on',
    description="Per-song detail behind the creator overview — DSP, role, ISRC, credit URL, and whether it's matched to a Song in the catalog.\n\n**Path parameters:** `org_id`, `creator_id`.\n**Query:** `dsp`, `role`, `matched` (bool), `q`, `limit`, `offset`.\n**Auth:** Bearer JWT — caller must be a member of the org.\n**Response:** `{ total, songs: [{credit_id, dsp, track_title, artist, isrc, role, credit_url, matched_song_id}] }`.",
)
def creator_credited_songs(
    org_id: int,
    creator_id: int,
    page: int = Query(1, ge=1),
    per_page: int = Query(50, le=100),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _verify_org_access(user, org_id, db, creator_id=creator_id)

    from ..models.models import SongCredit, Song, SongDSPLink
    from ..services.stream_estimator import get_song_stream_summary
    from sqlalchemy import or_

    spotify_dsp_subq = db.query(SongDSPLink.song_id).filter(
        SongDSPLink.platform == "SPOTIFY",
    ).distinct()

    credits_q = db.query(SongCredit, Song).join(
        Song, SongCredit.song_id == Song.id
    ).filter(
        SongCredit.creator_id == creator_id,
        Song.organization_id == org_id,
        or_(
            Song.spotify_link.isnot(None),
            Song.id.in_(spotify_dsp_subq),
        ),
    )

    total = credits_q.count()
    offset = (page - 1) * per_page
    credits_list = credits_q.offset(offset).limit(per_page).all()

    songs = []
    for credit, song in credits_list:
        stream_summary = get_song_stream_summary(song.id, org_id, db)
        songs.append({
            "song_id": song.id,
            "title": song.title,
            "artist": song.primary_artist,
            "role": credit.role,
            "share_percentage": credit.share_percentage,
            "isrc": song.isrc,
            "release_date": song.release_date.isoformat() if song.release_date else None,
            "artwork_url": song.media_url,
            "total_streams": stream_summary.get("total_streams", 0),
            "platforms": {
                p: (pdata.get("streams", 0) if isinstance(pdata, dict) else (pdata or 0))
                for p, pdata in stream_summary.get("platforms", {}).items()
            },
            "confidence": stream_summary.get("confidence", 0),
        })

    songs.sort(key=lambda x: x["total_streams"], reverse=True)
    return {"songs": songs, "total": total, "page": page, "per_page": per_page}


@router.post(
    "/org/{org_id}/creator/{creator_id}/refresh",
    summary='Re-scrape DSP credits for a creator',
    description='Triggers an on-demand scrape against Spotify/Apple credit pages for the creator. Synchronous; returns when the scrape completes.\n\n**Path parameters:** `org_id`, `creator_id`.\n**Auth:** Bearer JWT — caller must be a member of the org.\n**Response:** `{ creator_id, fetched, added, updated, errors }`.',
)
def refresh_creator_credits(
    org_id: int,
    creator_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _verify_org_access(user, org_id, db, creator_id=creator_id)

    from ..services.credits_service import compute_creator_credits
    result = compute_creator_credits(creator_id, org_id, db, force_refresh=True)
    if result.get("error"):
        raise HTTPException(status_code=404, detail=result["error"])
    return result


class ShareSettings(BaseModel):
    is_public: bool = True
    passcode: Optional[str] = None


@router.post(
    "/org/{org_id}/creator/{creator_id}/share",
    summary="Mint or rotate a public share link for a creator's credits",
    description="Creates (or rotates and replaces) the public share token used by `/credits/{share_token}` to expose the creator's credits page without auth. Returns the new URL.\n\n**Path parameters:** `org_id`, `creator_id`.\n**Body:** `{ expires_in_days?: int, rotate?: bool }`.\n**Auth:** Bearer JWT — caller must be a member of the org.\n**Response:** `{ share_token, share_url, expires_at }`.",
)
def manage_share_link(
    org_id: int,
    creator_id: int,
    body: ShareSettings,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _verify_org_access(user, org_id, db)

    import secrets as sec
    profile = db.query(CreatorCreditsProfile).filter(
        CreatorCreditsProfile.creator_id == creator_id,
        CreatorCreditsProfile.organization_id == org_id,
    ).first()

    if not profile:
        profile = CreatorCreditsProfile(
            creator_id=creator_id,
            organization_id=org_id,
            share_token=sec.token_hex(16),
        )
        db.add(profile)

    if not profile.share_token:
        profile.share_token = sec.token_hex(16)

    profile.is_public = body.is_public

    if body.passcode:
        hashed = bcrypt.hashpw(body.passcode.encode('utf-8'), bcrypt.gensalt())
        profile.share_passcode = hashed.decode('utf-8')
    elif body.passcode == "":
        profile.share_passcode = None

    db.commit()

    return {
        "share_token": profile.share_token,
        "is_public": profile.is_public,
        "has_passcode": bool(profile.share_passcode),
        "share_url": f"/shared/credits/{profile.share_token}",
    }


@router.delete(
    "/org/{org_id}/creator/{creator_id}/share",
    summary="Revoke the public share link for a creator's credits",
    description='Invalidates the existing token so the public page returns 410.\n\n**Path parameters:** `org_id`, `creator_id`.\n**Auth:** Bearer JWT — caller must be a member of the org.\n**Response:** `{ success: true }`.',
)
def revoke_share_link(
    org_id: int,
    creator_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _verify_org_access(user, org_id, db)

    profile = db.query(CreatorCreditsProfile).filter(
        CreatorCreditsProfile.creator_id == creator_id,
        CreatorCreditsProfile.organization_id == org_id,
    ).first()

    if not profile:
        raise HTTPException(status_code=404, detail="Credits profile not found")

    profile.is_public = False
    profile.share_passcode = None
    import secrets as sec
    profile.share_token = sec.token_hex(16)
    db.commit()

    return {"status": "Share link revoked"}


@public_router.get(
    "/credits/{share_token}",
    summary='Public read-only credits page for a creator',
    description="Resolves a share token to the creator's public credits view. Returns 404/410 if the token is invalid or expired.\n\n**Path parameter:** `share_token`.\n**Auth:** None — public.\n**Response:** `{ creator_name, organization_name, credits: [...], expires_at }`.",
)
def public_credits_page(
    share_token: str,
    passcode: str = Query(None),
    db: Session = Depends(get_db),
):
    from ..services.credits_service import get_public_credits
    result = get_public_credits(share_token, passcode=passcode, db=db)

    if result is None:
        raise HTTPException(status_code=404, detail="Credits profile not found")
    if result.get("error") == "passcode_required":
        return {"requires_passcode": True}
    if result.get("error") == "invalid_passcode":
        raise HTTPException(status_code=403, detail="Invalid passcode")
    if result.get("error"):
        raise HTTPException(status_code=403, detail=result["error"])

    return result


def _verify_super_admin(user: User):
    if not user.is_super_admin:
        raise HTTPException(status_code=403, detail="Super admin access required")


@admin_chart_router.get(
    "/sources",
    summary='List configured chart-data sources',
    description='Returns every ChartSource the platform polls for chart positions (Billboard, Spotify Charts, Apple Music charts, etc.) along with their fetch status.\n\n**Auth:** Bearer JWT — platform admin.\n**Response:** `{ sources: [{id, name, platform, url, status, last_fetched_at, next_fetch_at, error}] }`.',
)
def list_chart_sources(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _verify_super_admin(user)

    sources = db.query(ChartSource).order_by(ChartSource.platform, ChartSource.name).all()
    result = []
    for s in sources:
        entry_count = db.query(ChartEntry).filter(ChartEntry.chart_source_id == s.id).count()
        result.append({
            "id": s.id,
            "name": s.name,
            "platform": s.platform,
            "chart_type": s.chart_type,
            "country_code": s.country_code,
            "is_active": s.is_active,
            "fetch_frequency": s.fetch_frequency,
            "last_fetched_at": s.last_fetched_at.isoformat() if s.last_fetched_at else None,
            "last_error": s.last_error,
            "entry_count": entry_count,
        })
    return {"sources": result}


class ChartSourceCreate(BaseModel):
    name: str
    platform: str
    chart_type: str = "TOP_SONGS"
    country_code: Optional[str] = None
    url: Optional[str] = None
    external_playlist_id: Optional[str] = None
    fetch_frequency: str = "DAILY"


@admin_chart_router.post(
    "/sources",
    summary='Register a new chart-data source',
    description='Adds a new chart source the fetcher should poll on a schedule. Validates the URL is reachable.\n\n**Body:** `{ name, platform, url, schedule_cron?, country?: string }`.\n**Auth:** Bearer JWT — platform admin.\n**Response:** `{ id, name, status: "active" }`.',
)
def create_chart_source(
    body: ChartSourceCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _verify_super_admin(user)

    source = ChartSource(
        name=body.name,
        platform=body.platform,
        chart_type=body.chart_type,
        country_code=body.country_code,
        url=body.url,
        external_playlist_id=body.external_playlist_id,
        fetch_frequency=body.fetch_frequency,
    )
    db.add(source)
    db.commit()
    db.refresh(source)

    return {"id": source.id, "name": source.name, "status": "created"}


class ChartSourceUpdate(BaseModel):
    is_active: Optional[bool] = None
    fetch_frequency: Optional[str] = None
    name: Optional[str] = None


@admin_chart_router.put(
    "/sources/{source_id}",
    summary='Update a chart source',
    description='Patches an existing ChartSource (URL, schedule, status). Pass `status="paused"` to stop polling without deleting.\n\n**Path parameter:** `source_id`.\n**Body:** any subset of writable fields from create + `status`.\n**Auth:** Bearer JWT — platform admin.\n**Response:** `{ id, status }`.',
)
def update_chart_source(
    source_id: int,
    body: ChartSourceUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _verify_super_admin(user)

    source = db.query(ChartSource).filter(ChartSource.id == source_id).first()
    if not source:
        raise HTTPException(status_code=404, detail="Chart source not found")

    if body.is_active is not None:
        source.is_active = body.is_active
    if body.fetch_frequency:
        source.fetch_frequency = body.fetch_frequency
    if body.name:
        source.name = body.name

    db.commit()
    return {"id": source.id, "status": "updated"}


@admin_chart_router.post(
    "/fetch/{source_id}",
    summary='Trigger an immediate fetch of a chart source',
    description="Bypasses the schedule and runs a fetch right now — useful for debugging a source that's failing.\n\n**Path parameter:** `source_id`.\n**Auth:** Bearer JWT — platform admin.\n**Response:** `{ source_id, status, fetched_entries, error? }`.",
)
def trigger_manual_fetch(
    source_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _verify_super_admin(user)

    source = db.query(ChartSource).filter(ChartSource.id == source_id).first()
    if not source:
        raise HTTPException(status_code=404, detail="Chart source not found")

    from ..services.chart_scheduler import fetch_source
    result = fetch_source(source, db)
    return result


@admin_chart_router.get(
    "/stats",
    summary='Get chart-fetcher health statistics',
    description='Returns aggregate fetcher metrics for the admin overview tile.\n\n**Auth:** Bearer JWT — platform admin.\n**Response:** `{ total_sources, active_sources, by_platform: [...], total_entries, matched_entries, match_rate }`.',
)
def chart_stats(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _verify_super_admin(user)

    from sqlalchemy import func

    total_sources = db.query(ChartSource).count()
    active_sources = db.query(ChartSource).filter(ChartSource.is_active == True).count()
    total_entries = db.query(ChartEntry).count()
    matched_entries = db.query(ChartEntry).filter(ChartEntry.song_id.isnot(None)).count()

    platform_counts = db.query(
        ChartSource.platform,
        func.count(ChartEntry.id)
    ).join(ChartEntry, ChartSource.id == ChartEntry.chart_source_id).group_by(
        ChartSource.platform
    ).all()

    return {
        "total_sources": total_sources,
        "active_sources": active_sources,
        "total_entries": total_entries,
        "matched_entries": matched_entries,
        "match_rate": round(matched_entries / total_entries * 100, 1) if total_entries else 0,
        "by_platform": {p: c for p, c in platform_counts},
    }


@admin_chart_router.post(
    "/backfill",
    summary='Kick off a historical chart-data backfill',
    description='Asynchronously walks every active source and refetches its historical archive (where supported) so the chart store has deeper history. Long-running.\n\n**Body:** `{ source_ids?: int[], start_date?, end_date? }`.\n**Auth:** Bearer JWT — platform admin.\n**Response:** `{ status: "queued", message }`.',
)
def trigger_backfill(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _verify_super_admin(user)

    from ..services.chart_scheduler import seed_chart_sources, run_chart_ingestion

    seed_chart_sources(db)

    import threading
    thread = threading.Thread(target=run_chart_ingestion)
    thread.daemon = True
    thread.start()

    return {"status": "Backfill started in background", "message": "Chart data will be fetched and matched. Check back in a few minutes."}
