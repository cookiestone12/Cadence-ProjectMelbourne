import json
import os
import requests
from typing import Dict, Any, List, Optional

SPOTIFY_CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
SPOTIFY_CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")


def _get_replit_access_token() -> Optional[str]:
    hostname = os.getenv("REPLIT_CONNECTORS_HOSTNAME")
    repl_identity = os.getenv("REPL_IDENTITY")
    web_repl_renewal = os.getenv("WEB_REPL_RENEWAL")

    if repl_identity:
        x_replit_token = f"repl {repl_identity}"
    elif web_repl_renewal:
        x_replit_token = f"depl {web_repl_renewal}"
    else:
        return None

    if not hostname:
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
            return None

        settings = item.get("settings", {})
        access_token = settings.get("access_token")
        if not access_token:
            oauth = settings.get("oauth", {})
            creds = oauth.get("credentials", {})
            access_token = creds.get("access_token")

        return access_token
    except Exception:
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
    try:
        resp = requests.get(
            f"https://api.spotify.com/v1/{endpoint}",
            headers={"Authorization": f"Bearer {token}"},
            params=params,
            timeout=15,
        )
        resp.raise_for_status()
        return resp.json()
    except Exception:
        return None


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
    token = _get_access_token()
    if not token:
        return []

    playlist_id = None
    if "spotify.com/playlist/" in playlist_url:
        playlist_id = playlist_url.split("spotify.com/playlist/")[-1].split("?")[0]
    elif playlist_url.startswith("spotify:playlist:"):
        playlist_id = playlist_url.split("spotify:playlist:")[-1]
    else:
        playlist_id = playlist_url

    if not playlist_id:
        return []

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
