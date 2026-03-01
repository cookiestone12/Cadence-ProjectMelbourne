import logging
import secrets
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func

logger = logging.getLogger("cadence")


def compute_creator_credits(creator_id: int, org_id: int, db: Session) -> Dict[str, Any]:
    from ..models.models import SongCredit, Song, Creator, CreatorCreditsProfile, SongDSPLink
    from .stream_estimator import get_song_stream_summary, estimate_streams_for_song
    from sqlalchemy import or_

    creator = db.query(Creator).filter(Creator.id == creator_id, Creator.organization_id == org_id).first()
    if not creator:
        return {"error": "Creator not found"}

    credits = db.query(SongCredit).filter(SongCredit.creator_id == creator_id).all()

    song_ids = [c.song_id for c in credits]
    songs = {}
    if song_ids:
        spotify_dsp_subq = db.query(SongDSPLink.song_id).filter(
            SongDSPLink.song_id.in_(song_ids),
            SongDSPLink.platform == "SPOTIFY",
        ).distinct()

        song_list = db.query(Song).filter(
            Song.id.in_(song_ids),
            Song.organization_id == org_id,
            or_(
                Song.spotify_link.isnot(None),
                Song.id.in_(spotify_dsp_subq),
            ),
        ).all()
        songs = {s.id: s for s in song_list}

    role_breakdown = {}
    total_credits = 0
    total_streams = 0
    song_stream_data = []

    for credit in credits:
        song = songs.get(credit.song_id)
        if not song:
            continue

        total_credits += 1
        role = credit.role or "OTHER"
        role_breakdown[role] = role_breakdown.get(role, 0) + 1

        try:
            estimate_streams_for_song(song.id, org_id, db)
        except Exception as e:
            logger.warning(f"Stream estimation failed for song {song.id}: {e}")

        stream_summary = get_song_stream_summary(song.id, org_id, db)
        song_streams = stream_summary.get("total_streams", 0)
        total_streams += song_streams

        song_stream_data.append({
            "song_id": song.id,
            "title": song.title,
            "artist": song.primary_artist,
            "role": role,
            "share_percentage": credit.share_percentage,
            "total_streams": song_streams,
            "platforms": stream_summary.get("platforms", {}),
            "isrc": song.isrc,
            "artwork_url": getattr(song, 'media_url', None),
        })

    song_stream_data.sort(key=lambda x: x["total_streams"], reverse=True)
    top_songs = song_stream_data[:10]

    platform_totals = {}
    for ssd in song_stream_data:
        for platform, pdata in ssd.get("platforms", {}).items():
            stream_val = pdata.get("streams", 0) if isinstance(pdata, dict) else (pdata or 0)
            if platform not in platform_totals:
                platform_totals[platform] = 0
            platform_totals[platform] += stream_val

    profile = db.query(CreatorCreditsProfile).filter(
        CreatorCreditsProfile.creator_id == creator_id,
        CreatorCreditsProfile.organization_id == org_id,
    ).first()

    if not profile:
        profile = CreatorCreditsProfile(
            creator_id=creator_id,
            organization_id=org_id,
            share_token=secrets.token_hex(16),
        )
        db.add(profile)

    profile.total_credits = total_credits
    profile.total_estimated_streams = total_streams
    profile.role_breakdown = role_breakdown
    profile.top_songs = top_songs
    profile.platform_breakdown = platform_totals
    profile.last_computed_at = datetime.utcnow()
    profile.updated_at = datetime.utcnow()

    db.commit()

    logger.info(f"Credits computed for creator {creator_id}: {total_credits} credits, {total_streams} est. streams")

    return {
        "creator_id": creator_id,
        "display_name": creator.display_name,
        "hero_image_url": creator.hero_image_url,
        "total_credits": total_credits,
        "total_estimated_streams": total_streams,
        "role_breakdown": role_breakdown,
        "top_songs": top_songs,
        "platform_breakdown": platform_totals,
        "share_token": profile.share_token,
        "is_public": profile.is_public,
        "has_passcode": bool(profile.share_passcode),
        "last_computed_at": profile.last_computed_at.isoformat() if profile.last_computed_at else None,
    }


def compute_all_creators(org_id: int, db: Session) -> Dict[str, Any]:
    from ..models.models import Creator

    creators = db.query(Creator).filter(Creator.organization_id == org_id).all()
    results = {"total": len(creators), "computed": 0, "errors": 0}

    for creator in creators:
        try:
            result = compute_creator_credits(creator.id, org_id, db)
            if not result.get("error"):
                results["computed"] += 1
        except Exception as e:
            logger.error(f"Credits computation error for creator {creator.id}: {e}")
            results["errors"] += 1

    logger.info(f"Batch credits computation for org {org_id}: {results['computed']}/{results['total']} creators")
    return results


def get_credits_summary(creator_id: int, org_id: int, db: Session, force_refresh: bool = False) -> Dict[str, Any]:
    from ..models.models import CreatorCreditsProfile, Creator

    profile = db.query(CreatorCreditsProfile).filter(
        CreatorCreditsProfile.creator_id == creator_id,
        CreatorCreditsProfile.organization_id == org_id,
    ).first()

    if force_refresh or not profile or not profile.last_computed_at or \
       (datetime.utcnow() - profile.last_computed_at) > timedelta(hours=24):
        return compute_creator_credits(creator_id, org_id, db)

    creator = db.query(Creator).filter(Creator.id == creator_id).first()

    return {
        "creator_id": creator_id,
        "display_name": creator.display_name if creator else "Unknown",
        "hero_image_url": creator.hero_image_url if creator else None,
        "total_credits": profile.total_credits or 0,
        "total_estimated_streams": profile.total_estimated_streams or 0,
        "role_breakdown": profile.role_breakdown or {},
        "top_songs": profile.top_songs or [],
        "platform_breakdown": profile.platform_breakdown or {},
        "share_token": profile.share_token,
        "is_public": profile.is_public,
        "has_passcode": bool(profile.share_passcode),
        "last_computed_at": profile.last_computed_at.isoformat() if profile.last_computed_at else None,
    }


def get_credits_overview(org_id: int, db: Session, search: str = None, sort_by: str = "streams") -> list:
    from ..models.models import CreatorCreditsProfile, Creator

    query = db.query(CreatorCreditsProfile, Creator).join(
        Creator, CreatorCreditsProfile.creator_id == Creator.id
    ).filter(CreatorCreditsProfile.organization_id == org_id)

    if search:
        query = query.filter(Creator.display_name.ilike(f"%{search}%"))

    profiles = query.all()

    results = []
    for profile, creator in profiles:
        role_breakdown = profile.role_breakdown or {}
        top_role = max(role_breakdown, key=role_breakdown.get) if role_breakdown else None

        results.append({
            "creator_id": creator.id,
            "display_name": creator.display_name,
            "hero_image_url": creator.hero_image_url,
            "total_credits": profile.total_credits or 0,
            "total_estimated_streams": profile.total_estimated_streams or 0,
            "role_breakdown": role_breakdown,
            "top_role": top_role,
            "platform_breakdown": profile.platform_breakdown or {},
            "share_token": profile.share_token,
            "is_public": profile.is_public,
            "last_computed_at": profile.last_computed_at.isoformat() if profile.last_computed_at else None,
        })

    if sort_by == "streams":
        results.sort(key=lambda x: x["total_estimated_streams"], reverse=True)
    elif sort_by == "credits":
        results.sort(key=lambda x: x["total_credits"], reverse=True)
    elif sort_by == "name":
        results.sort(key=lambda x: (x["display_name"] or "").lower())

    return results


def get_public_credits(share_token: str, passcode: str = None, db: Session = None) -> Optional[Dict[str, Any]]:
    from ..models.models import CreatorCreditsProfile, Creator, Organization
    import bcrypt

    profile = db.query(CreatorCreditsProfile).filter(
        CreatorCreditsProfile.share_token == share_token,
    ).first()

    if not profile:
        return None

    if not profile.is_public and not profile.share_passcode:
        return {"error": "This profile is not shared publicly"}

    if profile.share_passcode:
        if not passcode:
            return {"error": "passcode_required", "requires_passcode": True}
        try:
            if not bcrypt.checkpw(passcode.encode('utf-8'), profile.share_passcode.encode('utf-8')):
                return {"error": "invalid_passcode"}
        except Exception:
            return {"error": "invalid_passcode"}

    creator = db.query(Creator).filter(Creator.id == profile.creator_id).first()
    org = db.query(Organization).filter(Organization.id == profile.organization_id).first()

    stale = not profile.last_computed_at or (datetime.utcnow() - profile.last_computed_at) > timedelta(hours=24)
    if stale:
        compute_creator_credits(profile.creator_id, profile.organization_id, db)
        db.refresh(profile)

    return {
        "creator_name": creator.display_name if creator else "Unknown",
        "hero_image_url": creator.hero_image_url if creator else None,
        "organization_name": (org.display_name or org.name) if org else None,
        "total_credits": profile.total_credits or 0,
        "total_estimated_streams": profile.total_estimated_streams or 0,
        "role_breakdown": profile.role_breakdown or {},
        "top_songs": profile.top_songs or [],
        "platform_breakdown": profile.platform_breakdown or {},
        "last_computed_at": profile.last_computed_at.isoformat() if profile.last_computed_at else None,
    }
