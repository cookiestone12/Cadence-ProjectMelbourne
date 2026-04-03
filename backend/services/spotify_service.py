import json
import os
import requests
from typing import Dict, Any, List, Optional

def _get_spotify_client_id():
    return os.getenv("SPOTIFY_CLIENT_ID")

def _get_spotify_client_secret():
    return os.getenv("SPOTIFY_CLIENT_SECRET")


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
    logger = logging.getLogger("cadence")
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
    logger = logging.getLogger("cadence")
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
    import logging
    logger = logging.getLogger("cadence")
    client_id = _get_spotify_client_id()
    client_secret = _get_spotify_client_secret()
    if not client_id or not client_secret:
        logger.info("Spotify client credentials: SPOTIFY_CLIENT_ID or SPOTIFY_CLIENT_SECRET not set")
        return None
    try:
        resp = requests.post(
            "https://accounts.spotify.com/api/token",
            data={"grant_type": "client_credentials"},
            auth=(client_id, client_secret),
            timeout=10,
        )
        resp.raise_for_status()
        return resp.json().get("access_token")
    except Exception as e:
        logger.error(f"Spotify client credentials token request failed: {e}")
        return None


def _get_access_token() -> Optional[str]:
    import logging
    logger = logging.getLogger("cadence")
    connector_token = _get_replit_access_token()
    if connector_token:
        logger.info("Spotify: Using Replit connector token")
        return connector_token
    cc_token = _get_client_credentials_token()
    if cc_token:
        logger.info("Spotify: Using client credentials token")
        return cc_token
    logger.warning("Spotify: No access token available from any source")
    return None


class SpotifyNotFoundError(Exception):
    pass


def _spotify_get(endpoint: str, token: str, params: dict = None) -> Optional[dict]:
    import logging
    logger = logging.getLogger("cadence")
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
        if resp.status_code == 404:
            logger.error(f"Spotify API 404 Not Found: {endpoint}")
            raise SpotifyNotFoundError(f"Resource not found: {endpoint}")
        if resp.status_code != 200:
            logger.error(f"Spotify API error: status={resp.status_code} body={resp.text[:500]}")
        resp.raise_for_status()
        return resp.json()
    except (SpotifyForbiddenError, SpotifyAuthError, SpotifyNotFoundError):
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


def lookup_release_metadata(spotify_url: str) -> Dict[str, Any]:
    import logging
    logger = logging.getLogger("cadence")

    token = _get_access_token()
    if not token:
        raise SpotifyAuthError("Spotify is not connected. Please check your Spotify credentials.")

    url_type, resource_id = _extract_spotify_url_type(spotify_url)
    if not resource_id or url_type == "unknown":
        raise ValueError("Could not recognize that Spotify URL. Please paste a valid Spotify album or track link.")

    if url_type == "album":
        album_data = _spotify_get(f"albums/{resource_id}", token)
        if not album_data:
            raise SpotifyNotFoundError("Could not find this album on Spotify.")

        artists = [a.get("name") for a in album_data.get("artists", [])]
        total_tracks = album_data.get("total_tracks", 0)
        album_type = album_data.get("album_type", "album").upper()
        if album_type == "SINGLE" or total_tracks == 1:
            release_type = "SINGLE"
        elif total_tracks <= 6:
            release_type = "EP"
        else:
            release_type = "ALBUM"

        genres = album_data.get("genres", [])
        cover_art = album_data.get("images", [{}])[0].get("url") if album_data.get("images") else None
        release_date = album_data.get("release_date", "")
        copyright_entries = album_data.get("copyrights", [])
        copyright_line = copyright_entries[0].get("text", "") if copyright_entries else ""

        tracks = []
        for t in album_data.get("tracks", {}).get("items", []):
            t_artists = [a.get("name") for a in t.get("artists", [])]
            isrc = None
            try:
                track_detail = _spotify_get(f"tracks/{t.get('id')}", token)
                if track_detail:
                    isrc = track_detail.get("external_ids", {}).get("isrc")
            except Exception:
                pass
            tracks.append({
                "title": t.get("name"),
                "primary_artist": t_artists[0] if t_artists else (artists[0] if artists else ""),
                "isrc": isrc,
                "track_number": t.get("track_number"),
                "disc_number": t.get("disc_number"),
                "duration_ms": t.get("duration_ms"),
                "spotify_url": t.get("external_urls", {}).get("spotify"),
            })

        return {
            "title": album_data.get("name", ""),
            "primary_artist": artists[0] if artists else "",
            "release_type": release_type,
            "label": album_data.get("label", ""),
            "release_date": release_date,
            "genre": genres[0] if genres else "",
            "cover_art_url": cover_art,
            "copyright_line": copyright_line,
            "copyright_year": int(release_date[:4]) if release_date and len(release_date) >= 4 else None,
            "spotify_url": album_data.get("external_urls", {}).get("spotify", ""),
            "upc": album_data.get("external_ids", {}).get("upc", ""),
            "total_tracks": total_tracks,
            "tracks": tracks,
        }

    elif url_type == "track":
        track_data = _spotify_get(f"tracks/{resource_id}", token)
        if not track_data:
            raise SpotifyNotFoundError("Could not find this track on Spotify.")

        artists = [a.get("name") for a in track_data.get("artists", [])]
        album = track_data.get("album", {})
        album_artists = [a.get("name") for a in album.get("artists", [])]
        cover_art = album.get("images", [{}])[0].get("url") if album.get("images") else None
        release_date = album.get("release_date", "")

        album_id = album.get("id")
        label = ""
        copyright_line = ""
        upc = ""
        genres = []
        if album_id:
            try:
                full_album = _spotify_get(f"albums/{album_id}", token)
                if full_album:
                    label = full_album.get("label", "")
                    copyright_entries = full_album.get("copyrights", [])
                    copyright_line = copyright_entries[0].get("text", "") if copyright_entries else ""
                    upc = full_album.get("external_ids", {}).get("upc", "")
                    genres = full_album.get("genres", [])
            except Exception:
                pass

        isrc = track_data.get("external_ids", {}).get("isrc", "")

        return {
            "title": track_data.get("name", ""),
            "primary_artist": artists[0] if artists else "",
            "release_type": "SINGLE",
            "label": label,
            "release_date": release_date,
            "genre": genres[0] if genres else "",
            "cover_art_url": cover_art,
            "copyright_line": copyright_line,
            "copyright_year": int(release_date[:4]) if release_date and len(release_date) >= 4 else None,
            "spotify_url": track_data.get("external_urls", {}).get("spotify", ""),
            "upc": upc,
            "total_tracks": 1,
            "tracks": [{
                "title": track_data.get("name"),
                "primary_artist": artists[0] if artists else "",
                "isrc": isrc,
                "track_number": track_data.get("track_number"),
                "disc_number": track_data.get("disc_number"),
                "duration_ms": track_data.get("duration_ms"),
                "spotify_url": track_data.get("external_urls", {}).get("spotify"),
            }],
        }

    else:
        raise ValueError("Please paste a Spotify album or track URL to populate release data.")


def _fetch_playlist_with_token(playlist_id: str, token: str, logger) -> List[Dict[str, Any]]:
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


def _extract_spotify_url_type(url: str):
    import re
    url = url.strip()

    web_pattern = re.compile(r'spotify\.com/(?:[a-z]{2}(?:-[a-z]{2})?/)?(?:intl-[a-z]+/)?(playlist|artist|album|track)/([A-Za-z0-9]+)')
    m = web_pattern.search(url)
    if m:
        return m.group(1), m.group(2)

    uri_pattern = re.compile(r'^spotify:(playlist|artist|album|track):([A-Za-z0-9]+)$')
    m = uri_pattern.match(url)
    if m:
        return m.group(1), m.group(2)

    if re.match(r'^[A-Za-z0-9]{22}$', url):
        return "playlist", url

    return "unknown", None


def _fetch_artist_tracks(artist_id: str, token: str, logger) -> List[Dict[str, Any]]:
    artist_data = _spotify_get(f"artists/{artist_id}", token)
    artist_name = artist_data.get("name", "Unknown") if artist_data else "Unknown"

    all_albums = []
    offset = 0
    while True:
        albums_data = _spotify_get(f"artists/{artist_id}/albums", token, {
            "include_groups": "album,single",
            "limit": 50,
            "offset": offset,
        })
        if not albums_data or not albums_data.get("items"):
            break
        all_albums.extend(albums_data["items"])
        if not albums_data.get("next"):
            break
        offset += 50

    if not all_albums:
        return []

    tracks = []
    seen_names = set()
    for album in all_albums:
        album_id = album.get("id")
        album_name = album.get("name", "")
        release_date = album.get("release_date", "")
        album_art = album.get("images", [{}])[0].get("url") if album.get("images") else None

        album_detail = _spotify_get(f"albums/{album_id}", token)
        if not album_detail:
            continue

        label = album_detail.get("label", "")

        for t in album_detail.get("tracks", {}).get("items", []):
            track_name = t.get("name", "")
            dedup_key = f"{track_name.lower().strip()}|{artist_name.lower().strip()}"
            if dedup_key in seen_names:
                continue
            seen_names.add(dedup_key)

            artists = [a.get("name") for a in t.get("artists", [])]
            spotify_url = t.get("external_urls", {}).get("spotify")

            tracks.append({
                "title": track_name,
                "primary_artist": artists[0] if artists else artist_name,
                "all_artists": artists if artists else [artist_name],
                "isrc": None,
                "album_name": album_name,
                "release_date": release_date,
                "spotify_url": spotify_url,
                "spotify_id": t.get("id"),
                "duration_ms": t.get("duration_ms"),
                "popularity": None,
                "album_art": album_art,
                "label": label,
                "track_number": t.get("track_number"),
                "disc_number": t.get("disc_number"),
                "explicit": t.get("explicit"),
            })

    return tracks


def _fetch_album_tracks(album_id: str, token: str, logger) -> List[Dict[str, Any]]:
    album_detail = _spotify_get(f"albums/{album_id}", token)
    if not album_detail:
        return []

    album_name = album_detail.get("name", "")
    release_date = album_detail.get("release_date", "")
    label = album_detail.get("label", "")
    album_art = album_detail.get("images", [{}])[0].get("url") if album_detail.get("images") else None
    album_artists = [a.get("name") for a in album_detail.get("artists", [])]

    tracks = []
    for t in album_detail.get("tracks", {}).get("items", []):
        artists = [a.get("name") for a in t.get("artists", [])]
        track_name = t.get("name", "")
        primary = artists[0] if artists else (album_artists[0] if album_artists else "Unknown")

        isrc = None
        try:
            search_results = _spotify_get("search", token, {"q": f"track:{track_name} artist:{primary}", "type": "track", "limit": 1})
            if search_results and search_results.get("tracks", {}).get("items"):
                sr = search_results["tracks"]["items"][0]
                isrc = sr.get("external_ids", {}).get("isrc")
        except Exception:
            pass

        tracks.append({
            "title": track_name,
            "primary_artist": primary,
            "all_artists": artists if artists else album_artists,
            "isrc": isrc,
            "album_name": album_name,
            "release_date": release_date,
            "spotify_url": t.get("external_urls", {}).get("spotify"),
            "spotify_id": t.get("id"),
            "duration_ms": t.get("duration_ms"),
            "popularity": None,
            "album_art": album_art,
            "label": label,
            "track_number": t.get("track_number"),
            "disc_number": t.get("disc_number"),
            "explicit": t.get("explicit"),
        })

    return tracks


def _fetch_with_retries(fetch_fn, resource_type: str, resource_id: str, tokens, logger, max_retries=3):
    import time
    last_error = None

    for attempt in range(1, max_retries + 1):
        all_404 = True
        for token_name, token in tokens:
            try:
                logger.info(f"Spotify: Attempt {attempt}/{max_retries} - fetching {resource_type} with {token_name} token")
                tracks = fetch_fn(resource_id, token, logger)
                all_404 = False
                if tracks:
                    logger.info(f"Spotify: Got {len(tracks)} tracks from {resource_type} on attempt {attempt}")
                    return tracks
            except SpotifyNotFoundError as e:
                logger.warning(f"Spotify: {token_name} got 404 for {resource_type} {resource_id} (attempt {attempt}): {e}")
                last_error = e
                continue
            except (SpotifyForbiddenError, SpotifyAuthError) as e:
                all_404 = False
                last_error = e
                logger.warning(f"Spotify: {token_name} failed for {resource_type}: {e}")
                continue
            except Exception as e:
                all_404 = False
                last_error = e
                logger.warning(f"Spotify: {token_name} error for {resource_type}: {e}")
                continue

        if not all_404:
            break

        if attempt < max_retries:
            delay = attempt * 1.5
            logger.info(f"Spotify: All tokens got 404, retrying in {delay}s (attempt {attempt}/{max_retries})")
            time.sleep(delay)

    return None, last_error, all_404


def get_playlist_tracks(playlist_url: str) -> List[Dict[str, Any]]:
    import logging
    logger = logging.getLogger("cadence")

    url_type, resource_id = _extract_spotify_url_type(playlist_url)

    if not resource_id or url_type == "unknown":
        raise ValueError("Could not recognize that Spotify URL. Please paste a valid Spotify playlist, artist, or album link.")

    if url_type == "track":
        raise ValueError("That looks like a single track URL. Please paste a playlist, artist, or album link to import multiple tracks.")

    logger.info(f"Spotify: Detected URL type '{url_type}' with ID '{resource_id}' from: {playlist_url}")

    cc_token = _get_client_credentials_token()
    connector_token = _get_replit_access_token()

    tokens = [(n, t) for n, t in [("client_credentials", cc_token), ("connector", connector_token)] if t]

    if not tokens:
        raise SpotifyAuthError("Spotify is not connected. Please check your Spotify credentials.")

    if url_type == "artist":
        result = _fetch_with_retries(_fetch_artist_tracks, "artist", resource_id, tokens, logger)
        if isinstance(result, tuple):
            raise SpotifyNotFoundError("Could not find this artist on Spotify. Please check the URL and try again.")
        return result

    if url_type == "album":
        result = _fetch_with_retries(_fetch_album_tracks, "album", resource_id, tokens, logger)
        if isinstance(result, tuple):
            raise SpotifyNotFoundError("Could not find this album on Spotify. Please check the URL and try again.")
        return result

    result = _fetch_with_retries(_fetch_playlist_with_token, "playlist", resource_id, tokens, logger)
    if isinstance(result, tuple):
        tracks_result, last_error, all_404 = result
        if all_404:
            raise SpotifyNotFoundError(
                "Could not fetch this playlist from Spotify after multiple attempts. "
                "The Spotify API sometimes has intermittent issues. "
                "Please wait a moment and try again, or try pasting an artist or album URL instead."
            )
        return []
    return result


def search_tracks(query: str, limit: int = 10) -> List[Dict[str, Any]]:
    token = _get_access_token()
    if not token:
        raise SpotifyAuthError("No Spotify credentials available. Please connect the Spotify integration or set SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET.")

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
