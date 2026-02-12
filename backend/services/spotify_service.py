import json
import os
import requests
from typing import Dict, Any, List, Optional

SPOTIFY_CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
SPOTIFY_CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")


def _get_replit_connector_header() -> Optional[str]:
    repl_identity = os.getenv("REPL_IDENTITY")
    web_repl_renewal = os.getenv("WEB_REPL_RENEWAL")
    if repl_identity:
        return f"repl {repl_identity}"
    elif web_repl_renewal:
        return f"depl {web_repl_renewal}"
    return None


def _get_replit_access_token() -> Optional[str]:
    import logging
    logger = logging.getLogger("rythm")
    hostname = os.getenv("REPLIT_CONNECTORS_HOSTNAME")
    x_replit_token = _get_replit_connector_header()

    if not hostname:
        logger.info("Spotify connector: REPLIT_CONNECTORS_HOSTNAME not set")
        return None
    if not x_replit_token:
        logger.info("Spotify connector: no REPL_IDENTITY or WEB_REPL_RENEWAL token available")
        return None

    try:
        resp = requests.get(
            f"https://{hostname}/api/v2/connection?include_secrets=true&connector_names=spotify",
            headers={
                "Accept": "application/json",
                "X_REPLIT_TOKEN": x_replit_token,
            },
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        item = data.get("items", [None])[0] if data.get("items") else None
        if not item:
            logger.warning("Spotify connector: no connection items found in connector response")
            return None

        settings = item.get("settings", {})
        oauth = settings.get("oauth", {})
        creds = oauth.get("credentials", {})

        access_token = settings.get("access_token") or creds.get("access_token")
        refresh_token = creds.get("refresh_token")
        client_id = creds.get("client_id")

        logger.info(
            f"Spotify connector credentials: "
            f"access_token={'present (' + str(len(access_token)) + ' chars)' if access_token else 'missing'}, "
            f"refresh_token={'present (' + str(len(refresh_token)) + ' chars)' if refresh_token else 'missing'}, "
            f"client_id={'present (' + str(len(client_id)) + ' chars)' if client_id else 'missing'}"
        )

        if refresh_token and client_id:
            logger.info("Spotify connector: attempting token refresh to get a fresh access token")
            refreshed = _refresh_spotify_token(refresh_token, client_id)
            if refreshed:
                logger.info("Spotify connector: using freshly refreshed token")
                return refreshed
            logger.warning("Spotify connector: token refresh failed, falling back to existing token")

        if access_token:
            logger.info("Spotify connector: using existing access token from connector")
            return access_token

        logger.warning("Spotify connector: no access token available and refresh failed or not possible")
        return None
    except Exception as e:
        logger.error(f"Spotify connector error: {e}")
        return None


def _refresh_spotify_token(refresh_token: str, client_id: str) -> Optional[str]:
    import logging
    logger = logging.getLogger("rythm")
    try:
        resp = requests.post(
            "https://accounts.spotify.com/api/token",
            data={
                "grant_type": "refresh_token",
                "refresh_token": refresh_token,
                "client_id": client_id,
            },
            timeout=10,
        )
        if resp.status_code == 200:
            new_token = resp.json().get("access_token")
            logger.info("Spotify token refreshed successfully")
            return new_token
        else:
            logger.error(f"Spotify token refresh failed: {resp.status_code} {resp.text[:200]}")
            return None
    except Exception as e:
        logger.error(f"Spotify token refresh exception: {e}")
        return None


def _get_client_credentials_token() -> Optional[str]:
    if not SPOTIFY_CLIENT_ID or not SPOTIFY_CLIENT_SECRET:
        return None
    try:
        resp = requests.post(
            "https://accounts.spotify.com/api/token",
            data={"grant_type": "client_credentials"},
            auth=(SPOTIFY_CLIENT_ID, SPOTIFY_CLIENT_SECRET),
            timeout=10,
        )
        resp.raise_for_status()
        return resp.json().get("access_token")
    except Exception:
        return None


def _get_access_token() -> Optional[str]:
    token = _get_replit_access_token()
    if token:
        return token
    return _get_client_credentials_token()


def _spotify_get(endpoint: str, token: str, params: dict = None) -> Optional[dict]:
    import logging
    logger = logging.getLogger("rythm")
    try:
        url = f"https://api.spotify.com/v1/{endpoint}"
        logger.info(f"Spotify API GET: {url} params={params}")
        resp = requests.get(
            url,
            headers={"Authorization": f"Bearer {token}"},
            params=params,
            timeout=15,
        )
        if resp.status_code == 403:
            logger.error(f"Spotify API 403 Forbidden: {resp.text[:500]}")
            raise SpotifyForbiddenError("Spotify API access is restricted. The connected Spotify app may be in development mode. Please try disconnecting and reconnecting the Spotify integration, or set SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET environment variables from your own Spotify Developer app.")
        if resp.status_code == 401:
            logger.error(f"Spotify API 401 Unauthorized: token may be expired")
            raise SpotifyAuthError("Spotify token has expired. Please reconnect the Spotify integration.")
        if resp.status_code != 200:
            logger.error(f"Spotify API error: status={resp.status_code} body={resp.text[:500]}")
        resp.raise_for_status()
        return resp.json()
    except (SpotifyForbiddenError, SpotifyAuthError):
        raise
    except Exception as e:
        logger.error(f"Spotify API exception: {e}")
        return None


class SpotifyForbiddenError(Exception):
    pass

class SpotifyAuthError(Exception):
    pass


def get_track_data(spotify_link: str = None) -> Dict[str, Any]:
    token = _get_access_token()
    if not token or not spotify_link:
        return get_mock_data()

    track_id = None
    if "spotify.com/track/" in spotify_link:
        track_id = spotify_link.split("spotify.com/track/")[-1].split("?")[0]
    elif spotify_link.startswith("spotify:track:"):
        track_id = spotify_link.split("spotify:track:")[-1]

    if not track_id:
        return get_mock_data()

    data = _spotify_get(f"tracks/{track_id}", token)
    if not data:
        return get_mock_data()

    return {
        "name": data.get("name"),
        "artists": [a.get("name") for a in data.get("artists", [])],
        "album": data.get("album", {}).get("name"),
        "release_date": data.get("album", {}).get("release_date"),
        "isrc": data.get("external_ids", {}).get("isrc"),
        "popularity": data.get("popularity"),
        "duration_ms": data.get("duration_ms"),
        "preview_url": data.get("preview_url"),
        "spotify_url": data.get("external_urls", {}).get("spotify"),
        "album_art": data.get("album", {}).get("images", [{}])[0].get("url") if data.get("album", {}).get("images") else None,
    }


def get_playlist_tracks(playlist_url: str) -> List[Dict[str, Any]]:
    import logging
    logger = logging.getLogger("rythm")
    token = _get_access_token()
    if not token:
        logger.error("Spotify: No access token available")
        return []

    playlist_id = None
    if "spotify.com/playlist/" in playlist_url:
        playlist_id = playlist_url.split("spotify.com/playlist/")[-1].split("?")[0].split("/")[0]
    elif playlist_url.startswith("spotify:playlist:"):
        playlist_id = playlist_url.split("spotify:playlist:")[-1]
    else:
        playlist_id = playlist_url.strip()

    if not playlist_id:
        logger.error(f"Spotify: Could not extract playlist ID from URL: {playlist_url}")
        return []

    logger.info(f"Spotify: Fetching playlist {playlist_id} from URL: {playlist_url}")

    tracks = []
    offset = 0
    limit = 100

    while True:
        data = _spotify_get(f"playlists/{playlist_id}/tracks", token, {"offset": offset, "limit": limit})
        if not data or not data.get("items"):
            break

        for item in data["items"]:
            track = item.get("track")
            if not track or track.get("is_local"):
                continue

            artists = [a.get("name") for a in track.get("artists", [])]
            album = track.get("album", {})

            tracks.append({
                "title": track.get("name"),
                "primary_artist": artists[0] if artists else "Unknown",
                "all_artists": artists,
                "isrc": track.get("external_ids", {}).get("isrc"),
                "album_name": album.get("name"),
                "release_date": album.get("release_date"),
                "spotify_url": track.get("external_urls", {}).get("spotify"),
                "spotify_id": track.get("id"),
                "duration_ms": track.get("duration_ms"),
                "popularity": track.get("popularity"),
                "album_art": album.get("images", [{}])[0].get("url") if album.get("images") else None,
                "label": album.get("label"),
                "track_number": track.get("track_number"),
                "disc_number": track.get("disc_number"),
                "explicit": track.get("explicit"),
            })

        if not data.get("next"):
            break
        offset += limit

    return tracks


def search_tracks(query: str, limit: int = 10) -> List[Dict[str, Any]]:
    token = _get_access_token()
    if not token:
        return []

    data = _spotify_get("search", token, {"q": query, "type": "track", "limit": limit})
    if not data or not data.get("tracks", {}).get("items"):
        return []

    results = []
    for track in data["tracks"]["items"]:
        artists = [a.get("name") for a in track.get("artists", [])]
        album = track.get("album", {})
        results.append({
            "title": track.get("name"),
            "primary_artist": artists[0] if artists else "Unknown",
            "all_artists": artists,
            "isrc": track.get("external_ids", {}).get("isrc"),
            "album_name": album.get("name"),
            "release_date": album.get("release_date"),
            "spotify_url": track.get("external_urls", {}).get("spotify"),
            "spotify_id": track.get("id"),
            "popularity": track.get("popularity"),
            "album_art": album.get("images", [{}])[0].get("url") if album.get("images") else None,
        })

    return results


def get_mock_data() -> Dict[str, Any]:
    mock_file_path = os.path.join(os.path.dirname(__file__), "../../mock_data/spotify_response.json")
    try:
        with open(mock_file_path, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {
            "name": "Sample Track",
            "artists": ["Sample Artist"],
            "album": "Sample Album",
            "release_date": "2024-01-01",
            "isrc": None,
            "popularity": 50,
        }
