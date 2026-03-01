import os
import logging
import time
import requests
from typing import List, Dict, Any, Optional
from datetime import date

logger = logging.getLogger("cadence")

USER_AGENT = "Cadence Catalog Intelligence/1.0 (chart-data-fetch)"

SPOTIFY_CHART_PLAYLISTS = {
    "37i9dQZEVXbLRQDuF5jeBp": {"name": "Spotify Top 50 US", "country": "US"},
    "37i9dQZEVXbMDoHDwVN2tF": {"name": "Spotify Top 50 Global", "country": "GLOBAL"},
    "37i9dQZEVXbLnolsZ8PSNw": {"name": "Spotify Top 50 UK", "country": "GB"},
}


def _request_with_backoff(url: str, headers: dict = None, params: dict = None, max_retries: int = 3) -> Optional[requests.Response]:
    default_headers = {"User-Agent": USER_AGENT}
    if headers:
        default_headers.update(headers)

    for attempt in range(max_retries):
        try:
            resp = requests.get(url, headers=default_headers, params=params, timeout=20)
            if resp.status_code == 429:
                retry_after = int(resp.headers.get("Retry-After", 2 ** (attempt + 1)))
                logger.warning(f"Rate limited on {url}, retrying after {retry_after}s")
                time.sleep(min(retry_after, 60))
                continue
            if resp.status_code >= 500:
                wait = 2 ** (attempt + 1)
                logger.warning(f"Server error {resp.status_code} on {url}, retrying in {wait}s")
                time.sleep(wait)
                continue
            return resp
        except requests.exceptions.Timeout:
            logger.warning(f"Timeout on {url}, attempt {attempt + 1}/{max_retries}")
            time.sleep(2 ** (attempt + 1))
        except requests.exceptions.RequestException as e:
            logger.error(f"Request error on {url}: {e}")
            return None
    return None


def fetch_spotify_charts(playlist_id: str = None) -> List[Dict[str, Any]]:
    from .spotify_service import _get_access_token, _spotify_get

    token = _get_access_token()
    if not token:
        logger.error("Spotify chart fetch: no access token available")
        return []

    playlists_to_fetch = {}
    if playlist_id:
        info = SPOTIFY_CHART_PLAYLISTS.get(playlist_id, {"name": f"Playlist {playlist_id}", "country": "UNKNOWN"})
        playlists_to_fetch[playlist_id] = info
    else:
        playlists_to_fetch = SPOTIFY_CHART_PLAYLISTS

    all_entries = []
    today = date.today()

    for pid, info in playlists_to_fetch.items():
        try:
            data = _spotify_get(f"playlists/{pid}/tracks", token, params={"limit": 100, "fields": "items(track(id,name,artists,album(name),external_ids))"})
            if not data or "items" not in data:
                logger.warning(f"Spotify chart fetch: no items for playlist {pid}")
                continue

            for i, item in enumerate(data.get("items", [])):
                track = item.get("track")
                if not track:
                    continue

                isrc = None
                external_ids = track.get("external_ids", {})
                if external_ids:
                    isrc = external_ids.get("isrc")

                artists = track.get("artists", [])
                artist_name = ", ".join(a.get("name", "") for a in artists) if artists else "Unknown"
                album = track.get("album", {})

                all_entries.append({
                    "title": track.get("name", ""),
                    "artist": artist_name,
                    "isrc": isrc,
                    "external_id": track.get("id", ""),
                    "position": i + 1,
                    "stream_count": None,
                    "view_count": None,
                    "play_count": None,
                    "platform": "SPOTIFY",
                    "album_name": album.get("name"),
                    "chart_date": today,
                    "extra_data": {
                        "playlist_id": pid,
                        "chart_name": info["name"],
                        "country": info["country"],
                    },
                })

            logger.info(f"Spotify chart fetch: got {len(data.get('items', []))} tracks from {info['name']}")
        except Exception as e:
            logger.error(f"Spotify chart fetch error for playlist {pid}: {e}")

    return all_entries


def fetch_youtube_trending(region_code: str = "US", max_results: int = 50) -> List[Dict[str, Any]]:
    api_key = os.getenv("YOUTUBE_API_KEY")
    if not api_key:
        logger.warning("YouTube chart fetch: YOUTUBE_API_KEY not set")
        return []

    url = "https://www.googleapis.com/youtube/v3/videos"
    params = {
        "part": "snippet,statistics",
        "chart": "mostPopular",
        "regionCode": region_code,
        "videoCategoryId": "10",
        "maxResults": max_results,
        "key": api_key,
    }

    resp = _request_with_backoff(url, params=params)
    if not resp or resp.status_code != 200:
        logger.error(f"YouTube trending fetch failed: {resp.status_code if resp else 'no response'}")
        return []

    data = resp.json()
    entries = []
    today = date.today()

    for i, item in enumerate(data.get("items", [])):
        snippet = item.get("snippet", {})
        stats = item.get("statistics", {})
        channel = snippet.get("channelTitle", "Unknown")
        title = snippet.get("title", "")

        entries.append({
            "title": title,
            "artist": channel,
            "isrc": None,
            "external_id": item.get("id", ""),
            "position": i + 1,
            "stream_count": None,
            "view_count": int(stats.get("viewCount", 0)),
            "play_count": None,
            "platform": "YOUTUBE",
            "album_name": None,
            "chart_date": today,
            "extra_data": {
                "region": region_code,
                "like_count": int(stats.get("likeCount", 0)) if stats.get("likeCount") else None,
                "comment_count": int(stats.get("commentCount", 0)) if stats.get("commentCount") else None,
                "published_at": snippet.get("publishedAt"),
                "thumbnail": snippet.get("thumbnails", {}).get("high", {}).get("url"),
            },
        })

    logger.info(f"YouTube trending fetch: got {len(entries)} music videos for {region_code}")
    return entries


def fetch_apple_charts(country: str = "us", limit: int = 100) -> List[Dict[str, Any]]:
    url = f"https://rss.itunes.apple.com/api/v1/{country}/itunes-music/top-songs/all/{limit}/explicit.json"

    resp = _request_with_backoff(url)
    if not resp or resp.status_code != 200:
        logger.error(f"Apple charts fetch failed: {resp.status_code if resp else 'no response'}")
        return []

    try:
        data = resp.json()
        feed = data.get("feed", {})
        results = feed.get("results", [])
    except Exception as e:
        logger.error(f"Apple charts parse error: {e}")
        return []

    entries = []
    today = date.today()

    for i, item in enumerate(results):
        entries.append({
            "title": item.get("name", ""),
            "artist": item.get("artistName", ""),
            "isrc": None,
            "external_id": item.get("id", ""),
            "position": i + 1,
            "stream_count": None,
            "view_count": None,
            "play_count": None,
            "platform": "APPLE",
            "album_name": item.get("collectionName"),
            "chart_date": today,
            "extra_data": {
                "country": country.upper(),
                "genre": item.get("genres", [{}])[0].get("name") if item.get("genres") else None,
                "release_date": item.get("releaseDate"),
                "artwork_url": item.get("artworkUrl100"),
                "url": item.get("url"),
            },
        })

    logger.info(f"Apple charts fetch: got {len(entries)} top songs for {country.upper()}")
    return entries


def fetch_deezer_charts(country_id: int = None) -> List[Dict[str, Any]]:
    if country_id:
        url = f"https://api.deezer.com/chart/{country_id}"
    else:
        url = "https://api.deezer.com/chart/"

    resp = _request_with_backoff(url)
    if not resp or resp.status_code != 200:
        logger.error(f"Deezer charts fetch failed: {resp.status_code if resp else 'no response'}")
        return []

    try:
        data = resp.json()
        tracks = data.get("tracks", {}).get("data", [])
    except Exception as e:
        logger.error(f"Deezer charts parse error: {e}")
        return []

    entries = []
    today = date.today()

    for i, track in enumerate(tracks):
        artist = track.get("artist", {})
        album = track.get("album", {})

        entries.append({
            "title": track.get("title", ""),
            "artist": artist.get("name", "Unknown"),
            "isrc": None,
            "external_id": str(track.get("id", "")),
            "position": i + 1 if track.get("position") is None else track.get("position"),
            "stream_count": None,
            "view_count": None,
            "play_count": None,
            "platform": "DEEZER",
            "album_name": album.get("title"),
            "chart_date": today,
            "extra_data": {
                "duration": track.get("duration"),
                "preview_url": track.get("preview"),
                "cover_url": album.get("cover_medium"),
            },
        })

    logger.info(f"Deezer charts fetch: got {len(entries)} tracks")
    return entries


def fetch_lastfm_charts(country: str = None, limit: int = 100) -> List[Dict[str, Any]]:
    api_key = os.getenv("LASTFM_API_KEY")
    if not api_key:
        logger.warning("Last.fm chart fetch: LASTFM_API_KEY not set")
        return []

    if country:
        method = "geo.gettoptracks"
        params = {
            "method": method,
            "country": country,
            "api_key": api_key,
            "format": "json",
            "limit": limit,
        }
    else:
        method = "chart.gettoptracks"
        params = {
            "method": method,
            "api_key": api_key,
            "format": "json",
            "limit": limit,
        }

    url = "http://ws.audioscrobbler.com/2.0/"
    resp = _request_with_backoff(url, params=params)
    if not resp or resp.status_code != 200:
        logger.error(f"Last.fm chart fetch failed: {resp.status_code if resp else 'no response'}")
        return []

    try:
        data = resp.json()
        if country:
            tracks = data.get("tracks", {}).get("track", [])
        else:
            tracks = data.get("tracks", {}).get("track", [])
    except Exception as e:
        logger.error(f"Last.fm chart parse error: {e}")
        return []

    entries = []
    today = date.today()

    for i, track in enumerate(tracks):
        artist_info = track.get("artist", {})
        artist_name = artist_info.get("name", "Unknown") if isinstance(artist_info, dict) else str(artist_info)

        play_count = None
        if track.get("playcount"):
            try:
                play_count = int(track["playcount"])
            except (ValueError, TypeError):
                pass
        if not play_count and track.get("listeners"):
            try:
                play_count = int(track["listeners"])
            except (ValueError, TypeError):
                pass

        entries.append({
            "title": track.get("name", ""),
            "artist": artist_name,
            "isrc": None,
            "external_id": track.get("mbid", "") or track.get("url", ""),
            "position": i + 1,
            "stream_count": None,
            "view_count": None,
            "play_count": play_count,
            "platform": "LASTFM",
            "album_name": None,
            "chart_date": today,
            "extra_data": {
                "country": country,
                "url": track.get("url"),
                "listeners": int(track.get("listeners", 0)) if track.get("listeners") else None,
                "mbid": track.get("mbid"),
            },
        })

    logger.info(f"Last.fm chart fetch: got {len(entries)} tracks" + (f" for {country}" if country else " (global)"))
    return entries


FETCHER_MAP = {
    "SPOTIFY": fetch_spotify_charts,
    "YOUTUBE": fetch_youtube_trending,
    "APPLE": fetch_apple_charts,
    "DEEZER": fetch_deezer_charts,
    "LASTFM": fetch_lastfm_charts,
}


def fetch_for_source(platform: str, **kwargs) -> List[Dict[str, Any]]:
    fetcher = FETCHER_MAP.get(platform.upper())
    if not fetcher:
        logger.error(f"No fetcher found for platform: {platform}")
        return []
    return fetcher(**kwargs)
