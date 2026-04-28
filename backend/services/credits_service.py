import logging
import secrets
from typing import Dict, Any, Optional, Set
from datetime import datetime, timedelta, date
from sqlalchemy.orm import Session
from sqlalchemy import func

logger = logging.getLogger("cadence")


# Per-song popularity is cached on ``songs.spotify_popularity`` /
# ``spotify_popularity_fetched_at`` so the Credits-tab compute path
# doesn't re-hit Spotify on every refresh. The dev-app daily Web API
# quota (~1k calls / 24h rolling for Development Mode) is otherwise
# exhausted by a single 100-credit creator and the page falls back to
# zeros across the board.
_POPULARITY_CACHE_FRESH_DAYS = 7


def _persist_popularity(song, popularity: int, db: Session) -> None:
    """Write ``popularity`` to the song's cache columns. Caller commits."""
    if popularity is None:
        return
    try:
        song.spotify_popularity = int(popularity)
        song.spotify_popularity_fetched_at = datetime.utcnow()
        db.flush()
    except Exception as e:
        logger.debug(f"Failed to persist spotify_popularity for song {song.id}: {e}")


def _cached_popularity_age_days(song) -> Optional[float]:
    fetched_at = getattr(song, "spotify_popularity_fetched_at", None)
    if not fetched_at:
        return None
    return (datetime.utcnow() - fetched_at).total_seconds() / 86400.0


def _batch_fetch_spotify_popularity(songs_needing_lookup: dict, db: Session) -> Dict[int, dict]:
    from ..models.models import SongDSPLink
    from .stream_estimator import _extract_spotify_id
    from .spotify_service import is_spotify_throttled
    results = {}
    track_id_to_song_ids: Dict[str, list] = {}
    songs_for_search = {}
    cache_hits = 0

    # Pass 1 — serve fresh cached popularity directly. No API call needed.
    # Songs that fall through to pass 2/3 may still benefit from a STALE
    # cached value if Spotify ends up unavailable; we defer that decision
    # until we know whether the API path got real data.
    songs_to_lookup: Dict[int, Any] = {}
    for song_id, song in songs_needing_lookup.items():
        cached_pop = getattr(song, "spotify_popularity", None)
        age_days = _cached_popularity_age_days(song)
        if cached_pop is not None and age_days is not None and age_days < _POPULARITY_CACHE_FRESH_DAYS:
            results[song_id] = {
                "popularity": int(cached_pop),
                "album_art": None,  # song.media_url already populated on the
                                    # original fetch; don't disturb it here.
                "from_cache": True,
            }
            cache_hits += 1
        else:
            songs_to_lookup[song_id] = song

    if cache_hits:
        logger.info(
            f"Spotify popularity cache: {cache_hits}/{len(songs_needing_lookup)} "
            f"songs served from cached popularity (fresh < {_POPULARITY_CACHE_FRESH_DAYS}d); "
            f"{len(songs_to_lookup)} require lookup"
        )

    # If the circuit breaker is already tripped from a prior call this
    # window, don't bother going to Spotify at all — go straight to the
    # stale-cache fallback at the bottom.
    if is_spotify_throttled():
        logger.warning(
            f"Spotify circuit breaker tripped; skipping API lookup for "
            f"{len(songs_to_lookup)} songs and falling back to stale cache where available"
        )
        for song_id, song in songs_to_lookup.items():
            cached_pop = getattr(song, "spotify_popularity", None)
            if cached_pop is not None:
                age_days = _cached_popularity_age_days(song)
                age_str = f"{age_days:.1f}d" if age_days is not None else "unknown age"
                logger.info(
                    f"Stale-cache fallback for song {song_id}: "
                    f"popularity={cached_pop} ({age_str})"
                )
                results[song_id] = {
                    "popularity": int(cached_pop),
                    "album_art": None,
                    "from_cache": True,
                    "stale": True,
                }
        return results

    for song_id, song in songs_to_lookup.items():
        spotify_url = song.spotify_link
        if not spotify_url:
            dsp = db.query(SongDSPLink).filter(
                SongDSPLink.song_id == song_id,
                SongDSPLink.platform == "SPOTIFY",
            ).first()
            if dsp:
                spotify_url = dsp.url

        if spotify_url:
            track_id = _extract_spotify_id(spotify_url)
            if track_id:
                if track_id not in track_id_to_song_ids:
                    track_id_to_song_ids[track_id] = []
                track_id_to_song_ids[track_id].append(song_id)
                continue

        songs_for_search[song_id] = song

    if track_id_to_song_ids:
        try:
            from .spotify_service import _get_access_token, _batch_or_individual_track_lookup
            token = _get_access_token()
            if token:
                unique_track_ids = list(track_id_to_song_ids.keys())
                logger.info(f"Spotify credits lookup: {len(unique_track_ids)} unique track IDs")
                # Helper transparently falls back to per-ID lookup when
                # Spotify Development Mode 403s the bulk endpoint, so we
                # get real popularity for our own dev-app accounts that
                # don't have Extended Quota Mode.
                by_id = _batch_or_individual_track_lookup(unique_track_ids, token, logger)
                for tid, track in by_id.items():
                    if not track or track.get("popularity") is None:
                        continue
                    album_art = None
                    album_images = track.get("album", {}).get("images", [])
                    if album_images:
                        album_art = album_images[0].get("url")
                    pop_data = {
                        "popularity": track["popularity"],
                        "album_art": album_art,
                    }
                    for sid in track_id_to_song_ids.get(tid, []):
                        results[sid] = pop_data
                        # Persist to song-level cache so future Credits-tab
                        # refreshes don't re-burn the dev-app daily quota.
                        song_obj = songs_to_lookup.get(sid)
                        if song_obj is not None:
                            _persist_popularity(song_obj, track["popularity"], db)
        except Exception as e:
            logger.error(f"Spotify batch lookup failed: {e}", exc_info=True)

    if songs_for_search:
        try:
            from .spotify_service import _get_access_token, _spotify_get
            token = _get_access_token()
            if token:
                logger.info(f"Spotify search lookup for {len(songs_for_search)} songs without URLs")
                for song_id, song in songs_for_search.items():
                    if song_id in results:
                        continue
                    query_parts = []
                    if song.title:
                        clean_title = song.title.split(" - ")[0].split(" (")[0].strip()
                        query_parts.append(f"track:{clean_title}")
                    if song.primary_artist:
                        clean_artist = song.primary_artist.split(" feat.")[0].split(" ft.")[0].split(",")[0].strip()
                        query_parts.append(f"artist:{clean_artist}")
                    if not query_parts:
                        logger.info(f"Song {song_id} has no title or artist for search")
                        continue
                    search_query = " ".join(query_parts)
                    try:
                        search_data = _spotify_get("search", token, {"q": search_query, "type": "track", "limit": 1})
                        if search_data and search_data.get("tracks", {}).get("items"):
                            track = search_data["tracks"]["items"][0]
                            pop = track.get("popularity", 0)
                            track_id = track.get("id")
                            # Spotify Development Mode degrades the
                            # popularity field on /v1/search results
                            # (always 0). The single-track endpoint is
                            # not affected, so confirm with one lookup
                            # before discarding the signal.
                            if pop == 0 and track_id:
                                try:
                                    confirm = _spotify_get(f"tracks/{track_id}", token)
                                    confirmed_pop = (confirm or {}).get("popularity", 0) or 0
                                    if confirmed_pop > 0:
                                        logger.info(
                                            f"Spotify search→track confirm rescued popularity for song {song_id}: "
                                            f"'{track.get('name')}' search-pop=0 -> confirmed-pop={confirmed_pop}"
                                        )
                                        pop = confirmed_pop
                                except Exception as ce:
                                    logger.debug(
                                        f"Spotify search→track confirm failed for song {song_id} "
                                        f"({track_id}): {ce}"
                                    )
                            if pop > 0:
                                album_art = None
                                album_images = track.get("album", {}).get("images", [])
                                if album_images:
                                    album_art = album_images[0].get("url")
                                results[song_id] = {
                                    "popularity": pop,
                                    "album_art": album_art,
                                }
                                _persist_popularity(song, pop, db)
                                logger.info(f"Spotify search hit for song {song_id}: '{track.get('name')}' pop={pop}")
                            else:
                                logger.info(f"Spotify search found '{track.get('name')}' for song {song_id} but popularity=0 (after confirm)")
                        else:
                            logger.info(f"Spotify search returned no results for song {song_id}: '{search_query}'")
                    except Exception as e:
                        logger.warning(f"Spotify search failed for song {song_id} ('{search_query}'): {e}")
            else:
                logger.warning(f"No Spotify token available for search lookup of {len(songs_for_search)} songs")
        except Exception as e:
            logger.error(f"Spotify search batch failed: {e}", exc_info=True)

    # Pass 3 — stale-cache fallback. Any song that needed a lookup but
    # didn't get a fresh result from Spotify (throttled mid-batch, null
    # response, network error) falls back to its previous cached
    # popularity if any exists. A days-old real number is far more
    # useful than a confident zero.
    stale_fallbacks = 0
    for song_id, song in songs_to_lookup.items():
        if song_id in results:
            continue
        cached_pop = getattr(song, "spotify_popularity", None)
        if cached_pop is not None:
            age_days = _cached_popularity_age_days(song)
            results[song_id] = {
                "popularity": int(cached_pop),
                "album_art": None,
                "from_cache": True,
                "stale": True,
            }
            stale_fallbacks += 1
            logger.info(
                f"Stale-cache fallback for song {song_id}: popularity={cached_pop} "
                f"({age_days:.1f}d old)" if age_days is not None else
                f"Stale-cache fallback for song {song_id}: popularity={cached_pop}"
            )
    if stale_fallbacks:
        logger.info(f"Used stale popularity cache for {stale_fallbacks} songs")

    return results


def compute_creator_credits(creator_id: int, org_id: int, db: Session, force_refresh: bool = False) -> Dict[str, Any]:
    from ..models.models import SongCredit, Song, Creator, CreatorCreditsProfile, StreamEstimate, Analytics, SongStreamingMetrics
    from .stream_estimator import get_song_stream_summary, estimate_streams_for_song, _estimate_from_popularity, MARKET_SHARE_RATIOS

    creator = db.query(Creator).filter(Creator.id == creator_id, Creator.organization_id == org_id).first()
    if not creator:
        return {"error": "Creator not found"}

    credits = db.query(SongCredit).filter(SongCredit.creator_id == creator_id).all()

    song_ids = [c.song_id for c in credits]
    songs = {}
    if song_ids:
        song_list = db.query(Song).filter(
            Song.id.in_(song_ids),
            Song.organization_id == org_id,
        ).all()
        songs = {s.id: s for s in song_list}

    unique_song_ids = list({c.song_id for c in credits if c.song_id in songs})

    today = date.today()
    recently_estimated = set()
    if unique_song_ids and not force_refresh:
        nonzero_songs = db.query(StreamEstimate.song_id).filter(
            StreamEstimate.song_id.in_(unique_song_ids),
            StreamEstimate.organization_id == org_id,
            StreamEstimate.period_date == today,
            StreamEstimate.estimated_streams > 0,
        ).distinct().all()
        recently_estimated = {r[0] for r in nonzero_songs}

    songs_needing_spotify = {}
    songs_with_local_data = set()
    for sid in unique_song_ids:
        if sid in recently_estimated:
            continue
        song = songs[sid]
        analytics = db.query(Analytics).filter(Analytics.song_id == sid).first()
        if analytics and analytics.spotify_streams:
            songs_with_local_data.add(sid)
            continue
        latest_metric = db.query(SongStreamingMetrics).filter(
            SongStreamingMetrics.song_id == sid,
        ).order_by(SongStreamingMetrics.period_date.desc()).first()
        if latest_metric and latest_metric.total_streams:
            songs_with_local_data.add(sid)
            continue
        songs_needing_spotify[sid] = song

    logger.info(f"Credits refresh for creator {creator_id} (force={force_refresh}): {len(unique_song_ids)} unique songs, {len(recently_estimated)} cached with data, {len(songs_with_local_data)} have local data, {len(songs_needing_spotify)} need Spotify lookup")

    spotify_diagnostics = {
        "token_available": False,
        "token_source": None,
        "lookup_attempted": len(songs_needing_spotify) > 0,
        "lookup_success_count": 0,
        "lookup_failure_count": 0,
        "songs_cached": len(recently_estimated),
        "songs_with_local_data": len(songs_with_local_data),
        "songs_needing_lookup": len(songs_needing_spotify),
    }

    if songs_needing_spotify:
        try:
            from .spotify_service import _get_access_token
            token = _get_access_token()
            if token:
                spotify_diagnostics["token_available"] = True
                spotify_diagnostics["token_source"] = "connector_or_credentials"
            else:
                spotify_diagnostics["token_available"] = False
                spotify_diagnostics["token_source"] = "none"
        except Exception:
            spotify_diagnostics["token_available"] = False
            spotify_diagnostics["token_source"] = "error"

    prefetched = {}
    if songs_needing_spotify:
        prefetched = _batch_fetch_spotify_popularity(songs_needing_spotify, db)
        spotify_diagnostics["lookup_success_count"] = len(prefetched)
        spotify_diagnostics["lookup_failure_count"] = len(songs_needing_spotify) - len(prefetched)
        logger.info(f"Batch Spotify fetch returned data for {len(prefetched)}/{len(songs_needing_spotify)} songs")

    for sid in songs_with_local_data:
        try:
            estimate_streams_for_song(sid, org_id, db)
        except Exception as e:
            logger.warning(f"Stream estimation failed for song {sid}: {e}")

    for sid in songs_needing_spotify:
        if sid in prefetched:
            song = songs[sid]
            pop_data = prefetched[sid]
            popularity = pop_data["popularity"]
            spotify_streams = _estimate_from_popularity(popularity)

            if pop_data.get("album_art") and not song.media_url:
                song.media_url = pop_data["album_art"]
                db.flush()

            db.query(StreamEstimate).filter(
                StreamEstimate.song_id == sid,
                StreamEstimate.organization_id == org_id,
                StreamEstimate.period_date == today,
            ).delete()
            db.flush()

            base_spotify = spotify_streams
            estimates_to_save = {
                "SPOTIFY": {"estimated_streams": spotify_streams, "actual_streams": None, "method": "POPULARITY_ESTIMATE", "confidence": 0.7},
            }
            for platform, ratio in MARKET_SHARE_RATIOS.items():
                estimates_to_save[platform] = {"estimated_streams": int(base_spotify * ratio), "actual_streams": None, "method": "MARKET_SHARE", "confidence": 0.3}

            source = {"base_spotify": base_spotify, "spotify_popularity": popularity}
            for platform, est in estimates_to_save.items():
                db.add(StreamEstimate(
                    song_id=sid,
                    organization_id=org_id,
                    period_date=today,
                    platform=platform,
                    estimated_streams=est["estimated_streams"],
                    actual_streams=est.get("actual_streams"),
                    estimation_method=est["method"],
                    confidence_score=est["confidence"],
                    source_data=source,
                ))
            db.flush()
        else:
            try:
                estimate_streams_for_song(sid, org_id, db)
            except Exception as e:
                logger.warning(f"Stream estimation failed for song {sid}: {e}")

    db.commit()

    role_breakdown = {}
    total_credits = 0
    total_streams = 0
    song_stream_map = {}
    seen_song_ids = set()

    for credit in credits:
        song = songs.get(credit.song_id)
        if not song:
            continue

        total_credits += 1
        role = credit.role or "OTHER"
        role_breakdown[role] = role_breakdown.get(role, 0) + 1

        if credit.song_id in seen_song_ids:
            if credit.song_id in song_stream_map:
                song_stream_map[credit.song_id]["roles"].append(role)
            continue

        seen_song_ids.add(credit.song_id)

        stream_summary = get_song_stream_summary(song.id, org_id, db)
        song_streams = stream_summary.get("total_streams", 0)
        total_streams += song_streams

        song_stream_map[credit.song_id] = {
            "song_id": song.id,
            "title": song.title,
            "artist": song.primary_artist,
            "roles": [role],
            "role": role,
            "share_percentage": credit.share_percentage,
            "total_streams": song_streams,
            "platforms": stream_summary.get("platforms", {}),
            "isrc": song.isrc,
            "artwork_url": getattr(song, 'media_url', None),
        }

    song_stream_data = list(song_stream_map.values())
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

    result = {
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

    if force_refresh:
        result["spotify_status"] = spotify_diagnostics

    return result


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
        "avatar_url": creator.hero_image_url if creator else None,
        "organization_name": (org.display_name or org.name) if org else None,
        "total_credits": profile.total_credits or 0,
        "total_estimated_streams": profile.total_estimated_streams or 0,
        "role_breakdown": profile.role_breakdown or {},
        "top_songs": profile.top_songs or [],
        "platform_breakdown": profile.platform_breakdown or {},
        "last_computed_at": profile.last_computed_at.isoformat() if profile.last_computed_at else None,
    }
