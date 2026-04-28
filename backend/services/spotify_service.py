import json
import os
import re
import time
import requests
from typing import Dict, Any, List, Optional


# Spotify caps the public embed page's pre-rendered trackList at exactly
# 50 entries. Larger playlists need the embed's lazy-load endpoint, which
# is intentionally out of scope for this fallback (see Task #153).
_EMBED_TRACK_CAP = 50

# A real-browser User-Agent is required — Spotify's edge serves a tiny
# JS bootstrap to most non-browser UAs, which omits the __NEXT_DATA__
# blob we need to scrape.
_EMBED_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)


class _PlaylistTracksResult(list):
    """A plain list with a single sidecar flag for embed-truncation.

    Subclassing ``list`` keeps the existing contract intact for
    ``_fetch_with_retries``, dedupe, JSON serialization and the
    frontend mapper — everything that just iterates or indexes the
    result keeps working — while letting the route layer detect
    "this came from the public-embed fallback and may be truncated"
    via ``getattr(tracks, "embed_truncated", False)``.
    """

    embed_truncated: bool = False

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


def _get_project_oauth_token() -> Optional[str]:
    """Project-owned Authorization-Code OAuth token (preferred path).

    Backed by ``spotify_oauth_tokens`` and the operator's own Spotify
    Developer app. Returns ``None`` quietly when no listener has been
    connected yet so the caller can fall back to other token sources.
    """
    import logging
    logger = logging.getLogger("cadence")
    try:
        from . import spotify_oauth as _oauth
        return _oauth.get_valid_access_token()
    except Exception as e:
        logger.error(f"Spotify project-OAuth lookup failed: {e}")
        return None


def _get_replit_access_token() -> Optional[str]:
    """Legacy: Replit Spotify connector token (kept for backward compat).

    Hard-bound to a Spotify dev app Replit owns whose Users-and-Access
    list we cannot edit, so it cannot satisfy the Development-Mode
    allowlist for our own dev app. Kept as a last-resort fallback in
    case the project-owned OAuth path is not yet connected and the
    connector still happens to work for some calls.
    """
    import logging
    logger = logging.getLogger("cadence")
    hostname = os.getenv("REPLIT_CONNECTORS_HOSTNAME")
    x_replit_token = _get_replit_connector_header()

    if not hostname:
        logger.debug("Spotify connector: REPLIT_CONNECTORS_HOSTNAME not set")
        return None
    if not x_replit_token:
        logger.debug("Spotify connector: no REPL_IDENTITY or WEB_REPL_RENEWAL token available")
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
            logger.debug("Spotify connector: no connection items found")
            return None

        settings = item.get("settings", {})
        oauth = settings.get("oauth", {})
        creds = oauth.get("credentials", {})

        access_token = settings.get("access_token") or creds.get("access_token")
        refresh_token = creds.get("refresh_token")
        client_id = creds.get("client_id")

        # The connector's stored refresh_token is an opaque Replit
        # placeholder ("REFRESH_...") that always fails directly against
        # Spotify. We try it but log the failure quietly since the
        # cached access_token is the real fallback.
        if refresh_token and client_id and not refresh_token.startswith("REFRESH_"):
            refreshed = _refresh_spotify_token(refresh_token, client_id)
            if refreshed:
                return refreshed

        if access_token:
            return access_token

        logger.debug("Spotify connector: no access token available")
        return None
    except Exception as e:
        logger.debug(f"Spotify connector error: {e}")
        return None


def _refresh_spotify_token(refresh_token: str, client_id: str) -> Optional[str]:
    """Legacy connector-token refresh. Quietly logs failures.

    The Replit connector stores an opaque placeholder where a real
    Spotify refresh_token would go, so direct refresh almost always
    returns ``invalid_grant``. We keep this path as a defensive try
    but log at DEBUG to avoid filling logs with alarming errors that
    aren't actionable.
    """
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
            return new_token
        logger.debug(f"Spotify connector refresh failed: {resp.status_code}")
        return None
    except Exception as e:
        logger.debug(f"Spotify connector refresh exception: {e}")
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
    """Resolve a Spotify bearer token in priority order.

    1. Project-owned Authorization-Code OAuth (preferred — uses the
       operator's own dev app, satisfies allowlist requirements and
       sidesteps the dev-app-owner-must-have-Premium gate).
    2. Replit Spotify connector token (legacy fallback).
    3. Client-credentials grant (last resort; fails 403 if the dev
       app's owner Spotify account doesn't have Premium).
    """
    import logging
    logger = logging.getLogger("cadence")

    project_token = _get_project_oauth_token()
    if project_token:
        logger.info("Spotify: Using project-owned OAuth token")
        return project_token

    connector_token = _get_replit_access_token()
    if connector_token:
        logger.info("Spotify: Using Replit connector token (legacy fallback)")
        return connector_token

    cc_token = _get_client_credentials_token()
    if cc_token:
        logger.info("Spotify: Using client credentials token")
        return cc_token

    logger.warning("Spotify: No access token available from any source")
    return None


class SpotifyNotFoundError(Exception):
    pass


_THROTTLE_SHORT_RETRY_CAP_SECONDS = 30.0
_THROTTLE_BREAKER_MAX_SECONDS = 7200.0
_spotify_throttled_until: float = 0.0


def is_spotify_throttled() -> bool:
    """True when Spotify is in a known long-throttle window.

    Set by :func:`_spotify_get` whenever Spotify returns HTTP 429 with a
    ``Retry-After`` header longer than :data:`_THROTTLE_SHORT_RETRY_CAP_SECONDS`
    (typical for daily-quota exhaustion on Development-Mode dev apps,
    where ``Retry-After`` comes back in the tens of thousands of
    seconds). Callers can inspect this to decide whether to fall back to
    cached data instead of making a doomed network call.
    """
    return time.time() < _spotify_throttled_until


def spotify_throttled_until() -> float:
    """Unix timestamp at which the circuit breaker will reset (0 if not tripped)."""
    return _spotify_throttled_until


def _spotify_get(endpoint: str, token: str, params: dict = None) -> Optional[dict]:
    global _spotify_throttled_until
    import logging
    logger = logging.getLogger("cadence")

    # Circuit breaker: if Spotify recently told us to come back in N hours
    # (typical of daily-quota exhaustion in Development Mode), don't burn
    # any more quota or worker time on guaranteed-429 calls. Just bail.
    now = time.time()
    if now < _spotify_throttled_until:
        seconds_left = _spotify_throttled_until - now
        logger.debug(
            f"Spotify circuit breaker active ({seconds_left:.0f}s remaining); "
            f"skipping {endpoint}"
        )
        return None

    try:
        url = f"https://api.spotify.com/v1/{endpoint}"
        logger.info(f"Spotify API GET: {url} params={params}")
        resp = requests.get(
            url,
            headers={"Authorization": f"Bearer {token}"},
            params=params,
            timeout=15,
        )
        if resp.status_code == 429:
            # Spotify rate-limited us. Two regimes:
            #
            #   * Short ``Retry-After`` (<= 30s): a per-second burst limit.
            #     Sleep the requested duration and retry once.
            #
            #   * Long ``Retry-After`` (> 30s): daily-quota exhaustion
            #     (Development Mode dev apps cap at ~1k Web API calls per
            #     rolling 24h window; a 100-credit creator's Credits tab
            #     burns this in one refresh). Spotify returns
            #     ``Retry-After`` in the tens of thousands of seconds — we
            #     cannot sleep that long inside a request handler, and
            #     retrying within the window only burns more of our
            #     remaining quota. Trip the circuit breaker and bail.
            retry_after_raw = resp.headers.get("Retry-After", "1")
            try:
                retry_after = float(retry_after_raw)
            except (TypeError, ValueError):
                retry_after = 1.0

            if retry_after > _THROTTLE_SHORT_RETRY_CAP_SECONDS:
                breaker_seconds = min(retry_after, _THROTTLE_BREAKER_MAX_SECONDS)
                # Monotonic update: never shorten an existing breaker window.
                # Prevents a concurrent call observing a smaller Retry-After
                # (because more wall-clock time has passed) from racing in
                # and reducing the deadline a sibling call already set.
                _spotify_throttled_until = max(
                    _spotify_throttled_until,
                    time.time() + breaker_seconds,
                )
                logger.warning(
                    f"Spotify 429 on {endpoint} with long Retry-After={retry_after_raw}s "
                    f"(daily quota likely exhausted); tripping circuit breaker for "
                    f"{breaker_seconds:.0f}s. Subsequent Spotify calls will short-circuit "
                    f"to cached values until reset."
                )
                return None

            wait = max(0.5, retry_after)
            logger.warning(
                f"Spotify 429 on {endpoint} (Retry-After={retry_after_raw}); "
                f"sleeping {wait:.1f}s and retrying once."
            )
            time.sleep(wait)
            resp = requests.get(
                url,
                headers={"Authorization": f"Bearer {token}"},
                params=params,
                timeout=15,
            )
            if resp.status_code == 429:
                # Second 429 in a row — treat as the long regime regardless
                # of header so we stop hammering for this request cycle.
                second_retry_raw = resp.headers.get("Retry-After", "60")
                try:
                    second_retry = float(second_retry_raw)
                except (TypeError, ValueError):
                    second_retry = 60.0
                breaker_seconds = min(max(second_retry, 60.0), _THROTTLE_BREAKER_MAX_SECONDS)
                _spotify_throttled_until = max(
                    _spotify_throttled_until,
                    time.time() + breaker_seconds,
                )
                logger.warning(
                    f"Spotify 429 on {endpoint} after retry "
                    f"(Retry-After={second_retry_raw}); tripping circuit breaker for "
                    f"{breaker_seconds:.0f}s."
                )
                return None
        if resp.status_code == 403:
            logger.error(f"Spotify API 403 Forbidden on {endpoint}: {resp.text[:500]}")
            # Spotify's Web API blocks /playlists/{id}/tracks for any
            # app in Development Mode that doesn't own the playlist —
            # OAuth scopes don't matter. Only Extended Quota Mode lifts
            # this. Surface a clear, actionable message instead of the
            # generic "Premium required" copy that misleads users into
            # disconnecting their working OAuth.
            if "playlists/" in endpoint and "/tracks" in endpoint:
                raise SpotifyForbiddenError(
                    "Spotify is blocking playlist track imports. This is a Spotify policy "
                    "for apps in Development Mode and does NOT mean your Cadence connection is broken. "
                    "Workarounds: paste an album, artist, or single track URL instead — those all work. "
                    "To enable playlist imports, request Extended Quota Mode for your Spotify Developer "
                    "app at developer.spotify.com (review takes a few weeks)."
                )
            raise SpotifyForbiddenError(
                "Spotify API access is restricted for this request. "
                "If you've connected Spotify under Admin → API Configuration, this usually means "
                "Spotify is rate-limiting or policy-blocking the specific endpoint. "
                "Try again in a moment, or paste an album/track URL instead."
            )
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


def _scrape_playlist_embed(playlist_id: str, logger) -> List[Dict[str, Any]]:
    """Fetch the public Spotify embed page and parse its trackList.

    Spotify's Web API blocks ``/playlists/{id}/tracks`` for any app in
    Development Mode that doesn't own the playlist (Extended Quota Mode
    lifts this but is unreachable for B2B catalog tools). The public
    embed page at ``open.spotify.com/embed/playlist/{id}``, however,
    ships the full track list inside a ``__NEXT_DATA__`` JSON blob with
    no auth required — same technique Soundiiz, TuneMyMusic and
    Exportify have used for years.

    Returns the raw embed track records (Spotify track ID, title,
    artist subtitle, duration, explicit flag, cover art). ISRC is *not*
    in the embed payload — call :func:`_enrich_tracks_via_api` on the
    track IDs to fill it in via ``/v1/tracks?ids=…``, which works on
    any of our token sources.

    Raises :class:`SpotifyForbiddenError` if the embed HTML can't be
    fetched, parsed, or contains no tracks (e.g. format change,
    private playlist, network error). Surfacing a forbidden-shape
    error keeps the route's error handling path consistent.
    """
    embed_url = f"https://open.spotify.com/embed/playlist/{playlist_id}"
    logger.info(f"Spotify: scraping public embed page for playlist {playlist_id}")
    try:
        resp = requests.get(
            embed_url,
            headers={
                "User-Agent": _EMBED_USER_AGENT,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9",
            },
            timeout=15,
        )
    except requests.RequestException as e:
        logger.error(f"Spotify embed scrape: HTTP error for {playlist_id}: {e}")
        raise SpotifyForbiddenError(
            "Couldn't reach Spotify to load this playlist. Please check your network "
            "and try again in a moment."
        )

    if resp.status_code == 404:
        raise SpotifyNotFoundError(
            "That Spotify playlist couldn't be found. Please double-check the URL."
        )
    if resp.status_code != 200:
        logger.error(
            f"Spotify embed scrape: unexpected {resp.status_code} for {playlist_id}: "
            f"{resp.text[:300]}"
        )
        raise SpotifyForbiddenError(
            "Spotify wouldn't return this playlist's track list. The playlist may be "
            "private or temporarily unavailable. Try pasting an album or single-track URL instead."
        )

    html = resp.text

    # The embed page renders Next.js with the standard
    # <script id="__NEXT_DATA__" type="application/json">…</script>
    # blob. The opening-tag regex tolerates arbitrary attribute order
    # (id and type can swap) and any extra attrs Spotify might add
    # (nonce, crossorigin, etc.) so a minor markup tweak doesn't
    # silently break the scraper.
    match = re.search(
        r'<script\b[^>]*\bid="__NEXT_DATA__"[^>]*>(.*?)</script>',
        html,
        flags=re.DOTALL,
    )
    if not match:
        logger.error(
            f"Spotify embed scrape: __NEXT_DATA__ blob missing from HTML for {playlist_id} "
            f"(len={len(html)}); Spotify may have changed the embed page format."
        )
        raise SpotifyForbiddenError(
            "Spotify changed the format of their playlist preview page. Cadence can't "
            "read this playlist right now. Please paste an album or single-track URL, "
            "or contact support."
        )

    try:
        payload = json.loads(match.group(1))
    except (json.JSONDecodeError, ValueError) as e:
        logger.error(f"Spotify embed scrape: __NEXT_DATA__ JSON parse failed for {playlist_id}: {e}")
        raise SpotifyForbiddenError(
            "Spotify returned a playlist preview that Cadence couldn't read. "
            "Please try again, or paste an album or single-track URL."
        )

    try:
        entity = (
            payload.get("props", {})
            .get("pageProps", {})
            .get("state", {})
            .get("data", {})
            .get("entity", {})
        )
        track_list = entity.get("trackList") or []
    except AttributeError:
        track_list = []

    if not track_list:
        logger.warning(
            f"Spotify embed scrape: empty trackList for {playlist_id} — "
            "likely a private/empty playlist or an embed format change."
        )
        raise SpotifyForbiddenError(
            "Spotify didn't return any tracks for this playlist. The playlist may be "
            "empty, private, or region-locked. Try pasting an album or single-track URL instead."
        )

    raw_tracks = []
    for entry in track_list:
        if not isinstance(entry, dict):
            continue

        # uri looks like "spotify:track:6rqhFgbbKwnb9MLmUQDhG6". Split
        # off the bare ID so we can batch-enrich via /v1/tracks?ids=.
        uri = entry.get("uri") or ""
        track_id = ""
        if uri.startswith("spotify:track:"):
            track_id = uri.split(":", 2)[2]
        elif entry.get("id"):
            track_id = str(entry.get("id"))

        if not track_id:
            continue

        # The embed's "subtitle" is a comma-separated string of artist
        # names — usually "Drake, Future" — sometimes joined with " · ".
        # Both delimiters round-trip cleanly to the same all_artists list.
        subtitle = (entry.get("subtitle") or "").strip()
        if " · " in subtitle:
            artists = [a.strip() for a in subtitle.split(" · ") if a.strip()]
        else:
            artists = [a.strip() for a in subtitle.split(",") if a.strip()]
        primary_artist = artists[0] if artists else "Unknown"

        cover_url = None
        visual = entry.get("visualIdentity") or {}
        images = visual.get("image") if isinstance(visual, dict) else None
        if isinstance(images, list) and images:
            cover_url = images[0].get("url")
        if not cover_url and entry.get("imageUrl"):
            cover_url = entry.get("imageUrl")

        raw_tracks.append({
            "spotify_id": track_id,
            "title": entry.get("title") or "",
            "primary_artist": primary_artist,
            "all_artists": artists if artists else [primary_artist],
            "duration_ms": entry.get("duration") or None,
            "explicit": bool(entry.get("isExplicit")),
            "spotify_url": f"https://open.spotify.com/track/{track_id}",
            "album_art": cover_url,
            # Filled in by _enrich_tracks_via_api:
            "isrc": None,
            "album_name": None,
            "release_date": None,
            "popularity": None,
            "label": None,
            "track_number": None,
            "disc_number": None,
        })

    logger.info(
        f"Spotify embed scrape: parsed {len(raw_tracks)} track(s) for playlist {playlist_id}"
    )
    return raw_tracks


def _batch_or_individual_track_lookup(
    track_ids: List[str], token: str, logger
) -> Dict[str, Dict[str, Any]]:
    """Look up a list of Spotify track IDs, with per-ID fallback.

    Tries the bulk ``GET /v1/tracks?ids=`` endpoint first (50 IDs per
    call). Falls back to looping ``GET /v1/tracks/{id}`` one ID at a
    time when **either** of the two Development-Mode failure modes
    fires:

    1. **HTTP 403** on the bulk call — explicit policy block.
    2. **HTTP 200 with ``{"tracks": [null, null, …]}``** — Spotify's
       silent-null policy, where the bulk endpoint returns one ``null``
       per track the listener can't read instead of erroring. This is
       the path that bit production creator 38 ("Killah B") even after
       Task #156's fix shipped: OAuth was healthy, songs all had
       Spotify links, but every popularity came back ``null``, leaving
       ``Total Estimated Streams: 0`` on the Credits tab.

    The single-track ``/v1/tracks/{id}`` endpoint is not subject to
    either failure mode and still returns real popularity, ISRC, album
    metadata, etc. for accounts whose dev app hasn't been granted
    Extended Quota Mode.

    Returns a dict keyed by Spotify track ID with the same record
    shape the bulk endpoint returns
    (``{id, popularity, external_ids, album, artists, ...}``). Tracks
    we couldn't resolve at all are simply omitted from the dict; the
    caller can detect those by ``set(track_ids) - by_id.keys()``.

    Hard auth/policy errors (``SpotifyAuthError``) are intentionally
    re-raised so the caller can surface a useful message instead of
    silently degrading to empty results.
    """
    by_id: Dict[str, Dict[str, Any]] = {}
    if not track_ids or not token:
        return by_id

    bulk_blocked = False
    for chunk_start in range(0, len(track_ids), 50):
        chunk = track_ids[chunk_start:chunk_start + 50]
        if bulk_blocked:
            break
        logger.info(f"Spotify track lookup: bulk /v1/tracks for {len(chunk)} IDs")
        try:
            data = _spotify_get("tracks", token, {"ids": ",".join(chunk)})
        except SpotifyForbiddenError as e:
            logger.info(
                f"Spotify bulk /v1/tracks 403 by Development Mode policy ({e}); "
                f"falling back to per-track lookup for the remaining {len(track_ids) - chunk_start} ID(s)."
            )
            bulk_blocked = True
            break
        except SpotifyAuthError:
            raise
        except SpotifyNotFoundError as e:
            logger.warning(f"Spotify bulk /v1/tracks 404 ({e}); skipping chunk.")
            continue
        except Exception as e:
            logger.warning(
                f"Spotify bulk /v1/tracks error ({e}); will retry IDs individually."
            )
            bulk_blocked = True
            break

        raw_records = (data or {}).get("tracks", []) or []
        real_in_chunk = 0
        for record in raw_records:
            if not isinstance(record, dict) or not record.get("id"):
                continue
            by_id[record["id"]] = record
            real_in_chunk += 1

        if real_in_chunk < len(chunk):
            # Spotify Dev Mode silent-null policy: bulk endpoint
            # returned 200 OK but with `null` for tracks the listener
            # can't read. The exception-based 403 trigger above never
            # fires in this case, so detect it by counting real records
            # against requested IDs and fall through to per-ID lookup
            # for the unresolved ones. The existing
            # `remaining = [tid for tid in track_ids if tid not in by_id]`
            # handles partial preservation across chunks.
            logger.info(
                f"Spotify bulk /v1/tracks returned {real_in_chunk}/{len(chunk)} real records "
                f"on a 200 response (Dev Mode silent-null policy); falling back to per-track "
                f"lookup for unresolved ID(s)."
            )
            bulk_blocked = True

    if bulk_blocked:
        # Per-ID fallback. Sequential by design — the per-track endpoint
        # has its own per-second quota and we'd rather be slow than
        # rate-limited. Skip IDs already resolved by an earlier bulk
        # chunk that succeeded before the block kicked in.
        remaining = [tid for tid in track_ids if tid not in by_id]
        logger.info(
            f"Spotify per-track fallback: looking up {len(remaining)} ID(s) individually."
        )
        for idx, tid in enumerate(remaining):
            if idx > 0:
                # Tiny breather between per-ID calls so a 100-song catalog
                # doesn't fire all 100 lookups in <1s and trip Spotify's
                # rate limiter. 50ms ≈ 20 req/s — well under any per-second
                # cap, and the 429-with-Retry-After handler in _spotify_get
                # rescues us if we still hit it.
                time.sleep(0.05)
            try:
                record = _spotify_get(f"tracks/{tid}", token)
            except SpotifyAuthError:
                raise
            except SpotifyNotFoundError:
                continue
            except SpotifyForbiddenError as e:
                # If even the single-track endpoint 403s, stop hammering
                # Spotify. Caller will see a partial result.
                logger.warning(
                    f"Spotify per-track lookup also blocked for {tid} ({e}); "
                    "aborting fallback loop to avoid rate-limit penalties."
                )
                break
            except Exception as e:
                logger.warning(f"Spotify per-track lookup failed for {tid}: {e}")
                continue
            if isinstance(record, dict) and record.get("id"):
                by_id[record["id"]] = record

    return by_id


def _enrich_tracks_via_api(tracks: List[Dict[str, Any]], token: str, logger) -> None:
    """Fill in ISRC, album, release date, label, popularity in place.

    Uses :func:`_batch_or_individual_track_lookup` which tries the
    bulk ``/v1/tracks?ids=`` endpoint first and falls back to per-ID
    ``/v1/tracks/{id}`` calls when Spotify's Development Mode policy
    blocks the bulk read. This keeps embed-scraped playlists fully
    enriched (ISRC, album, release date, popularity) even on dev-app
    accounts without Extended Quota Mode. If enrichment fails for any
    reason we keep the embed-scraped basics rather than failing the
    whole import — the user can still see and select tracks; they'll
    just be missing ISRC and album metadata, which downstream code
    already tolerates.
    """
    track_ids = [t.get("spotify_id") for t in tracks if t.get("spotify_id")]
    if not track_ids or not token:
        return

    try:
        by_id = _batch_or_individual_track_lookup(track_ids, token, logger)
    except SpotifyAuthError as e:
        logger.warning(
            f"Spotify embed enrichment: auth failed ({e}); "
            "continuing with embed-only metadata."
        )
        return
    except Exception as e:
        logger.warning(
            f"Spotify embed enrichment: lookup error ({e}); "
            "continuing with embed-only metadata."
        )
        return

    if not by_id:
        logger.warning(
            "Spotify embed enrichment: no enriched records returned; "
            "tracks will be imported with embed-only metadata."
        )
        return

    for t in tracks:
        rec = by_id.get(t.get("spotify_id"))
        if not rec:
            continue
        album = rec.get("album", {}) or {}
        artists = [a.get("name") for a in rec.get("artists", []) if a.get("name")]
        album_images = album.get("images") or []
        cover = album_images[0].get("url") if album_images else None

        if rec.get("name"):
            t["title"] = rec.get("name")
        if artists:
            t["all_artists"] = artists
            t["primary_artist"] = artists[0]
        t["isrc"] = rec.get("external_ids", {}).get("isrc") or t.get("isrc")
        t["album_name"] = album.get("name") or t.get("album_name")
        t["release_date"] = album.get("release_date") or t.get("release_date")
        t["popularity"] = rec.get("popularity") if rec.get("popularity") is not None else t.get("popularity")
        t["track_number"] = rec.get("track_number") or t.get("track_number")
        t["disc_number"] = rec.get("disc_number") or t.get("disc_number")
        t["explicit"] = bool(rec.get("explicit")) if "explicit" in rec else t.get("explicit", False)
        if rec.get("duration_ms"):
            t["duration_ms"] = rec.get("duration_ms")
        if cover:
            t["album_art"] = cover
        if rec.get("external_urls", {}).get("spotify"):
            t["spotify_url"] = rec["external_urls"]["spotify"]


def _fetch_playlist_with_token(playlist_id: str, token: str, logger) -> List[Dict[str, Any]]:
    tracks = _PlaylistTracksResult()
    offset = 0
    limit = 100

    try:
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

        if tracks:
            logger.info(f"Spotify: playlist {playlist_id} loaded via Web API ({len(tracks)} tracks)")
        return tracks
    except SpotifyForbiddenError as web_api_err:
        # The Web API blocks /playlists/{id}/tracks for any app in
        # Development Mode that doesn't own the playlist. Fall back to
        # scraping the public embed page (no auth needed) and enrich
        # each track via /v1/tracks?ids=… which still works.
        logger.warning(
            f"Spotify Web API forbade playlist {playlist_id} ({web_api_err}); "
            "falling back to public embed scrape."
        )
        embed_tracks = _scrape_playlist_embed(playlist_id, logger)
        _enrich_tracks_via_api(embed_tracks, token, logger)

        result = _PlaylistTracksResult(embed_tracks)
        # Spotify's pre-rendered embed page caps the trackList at exactly
        # _EMBED_TRACK_CAP entries. A shorter list means the playlist
        # really is that small and there is nothing more to load; a list
        # exactly at the cap is the only signal we have that the playlist
        # may continue past what the embed surfaced.
        result.embed_truncated = len(embed_tracks) == _EMBED_TRACK_CAP
        logger.info(
            f"Spotify: playlist {playlist_id} loaded via embed fallback "
            f"({len(result)} tracks, truncated={result.embed_truncated})"
        )
        return result


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

    if isinstance(last_error, (SpotifyForbiddenError, SpotifyAuthError)):
        raise last_error

    return None, last_error, all_404


def get_playlist_tracks(playlist_url: str) -> List[Dict[str, Any]]:
    import logging
    logger = logging.getLogger("cadence")

    url_type, resource_id = _extract_spotify_url_type(playlist_url)

    if not resource_id or url_type == "unknown":
        raise ValueError("Could not recognize that Spotify URL. Please paste a valid Spotify track, playlist, artist, or album link.")

    if url_type == "track":
        logger.info(f"Spotify: Detected single track URL with ID '{resource_id}' from: {playlist_url}")

        # Try project-owned OAuth first — it's the only path that
        # works against the operator's own dev app without the
        # Premium-required gate that blocks client_credentials.
        project_token = _get_project_oauth_token()
        cc_token = _get_client_credentials_token()
        connector_token = _get_replit_access_token()
        tokens = [
            (n, t) for n, t in [
                ("project_oauth", project_token),
                ("client_credentials", cc_token),
                ("connector", connector_token),
            ] if t
        ]

        if not tokens:
            raise SpotifyAuthError("Spotify is not connected. Please check your Spotify credentials.")

        last_error = None
        for token_name, token in tokens:
            try:
                track_data = _spotify_get(f"tracks/{resource_id}", token)
                if track_data:
                    artists = [a.get("name") for a in track_data.get("artists", [])]
                    album = track_data.get("album", {})
                    album_art = album.get("images", [{}])[0].get("url") if album.get("images") else None

                    label = ""
                    album_id = album.get("id")
                    if album_id:
                        try:
                            full_album = _spotify_get(f"albums/{album_id}", token)
                            if full_album:
                                label = full_album.get("label", "")
                        except Exception:
                            pass

                    return [{
                        "title": track_data.get("name", ""),
                        "primary_artist": artists[0] if artists else "Unknown",
                        "all_artists": artists,
                        "isrc": track_data.get("external_ids", {}).get("isrc"),
                        "album_name": album.get("name", ""),
                        "release_date": album.get("release_date", ""),
                        "spotify_url": track_data.get("external_urls", {}).get("spotify"),
                        "spotify_id": track_data.get("id"),
                        "duration_ms": track_data.get("duration_ms"),
                        "popularity": track_data.get("popularity"),
                        "album_art": album_art,
                        "label": label,
                        "track_number": track_data.get("track_number"),
                        "disc_number": track_data.get("disc_number"),
                        "explicit": track_data.get("explicit"),
                    }]
            except (SpotifyForbiddenError, SpotifyAuthError) as e:
                logger.warning(f"Spotify: {token_name} auth/forbidden for single track: {e}")
                last_error = e
                continue
            except SpotifyNotFoundError as e:
                logger.warning(f"Spotify: {token_name} got 404 for single track {resource_id}: {e}")
                last_error = e
                continue
            except Exception as e:
                logger.warning(f"Spotify: {token_name} failed for single track: {e}")
                last_error = e
                continue

        if isinstance(last_error, SpotifyAuthError):
            raise last_error
        if isinstance(last_error, SpotifyForbiddenError):
            raise last_error
        raise SpotifyNotFoundError("Could not find this track on Spotify. Please check the URL and try again.")

    logger.info(f"Spotify: Detected URL type '{url_type}' with ID '{resource_id}' from: {playlist_url}")

    # Project-owned OAuth first; the other two are kept as backstops.
    project_token = _get_project_oauth_token()
    cc_token = _get_client_credentials_token()
    connector_token = _get_replit_access_token()

    tokens = [
        (n, t) for n, t in [
            ("project_oauth", project_token),
            ("client_credentials", cc_token),
            ("connector", connector_token),
        ] if t
    ]

    if not tokens:
        raise SpotifyAuthError("Spotify is not connected. Please check your Spotify credentials.")

    def _check_tuple_error(result):
        if isinstance(result, tuple):
            _, err, _ = result
            if isinstance(err, (SpotifyForbiddenError, SpotifyAuthError)):
                raise err

    if url_type == "artist":
        result = _fetch_with_retries(_fetch_artist_tracks, "artist", resource_id, tokens, logger)
        if isinstance(result, tuple):
            _check_tuple_error(result)
            raise SpotifyNotFoundError("Could not find this artist on Spotify. Please check the URL and try again.")
        return result

    if url_type == "album":
        result = _fetch_with_retries(_fetch_album_tracks, "album", resource_id, tokens, logger)
        if isinstance(result, tuple):
            _check_tuple_error(result)
            raise SpotifyNotFoundError("Could not find this album on Spotify. Please check the URL and try again.")
        return result

    result = _fetch_with_retries(_fetch_playlist_with_token, "playlist", resource_id, tokens, logger)
    if isinstance(result, tuple):
        _check_tuple_error(result)
        _, last_error, all_404 = result
        if all_404:
            raise SpotifyNotFoundError(
                "Could not fetch this playlist from Spotify after multiple attempts. "
                "The Spotify API sometimes has intermittent issues. "
                "Please wait a moment and try again, or try pasting an artist or album URL instead."
            )
        raise ValueError(
            "Could not fetch playlist tracks. The playlist may be empty or temporarily unavailable. "
            "Please try again in a moment."
        )
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
