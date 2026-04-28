"""Task #153 — Spotify playlist embed-fallback contract tests.

When Spotify's Web API blocks /playlists/{id}/tracks with 403 (the
default for any app stuck in Development Mode that doesn't own the
playlist), spotify_service falls back to scraping the public embed
page at open.spotify.com/embed/playlist/{id}. These tests pin:

1. The __NEXT_DATA__ regex tolerates arbitrary attribute order, so a
   minor markup tweak from Spotify (e.g. id/type swap, extra nonce)
   doesn't silently break imports.
2. trackList parsing extracts the spotify_id, title, primary_artist,
   all_artists, duration_ms, explicit, and album_art fields the
   downstream import flow expects.
3. An empty/missing trackList raises SpotifyForbiddenError with a
   user-readable message (so the route surfaces the helpful banner
   instead of a 500).
4. The full playlist fetch flow flips embed_truncated to True only
   when the embed returns exactly _EMBED_TRACK_CAP tracks, never
   when fewer.
"""
import json
from unittest.mock import MagicMock, patch

import pytest

from backend.services.spotify_service import (
    _EMBED_TRACK_CAP,
    _PlaylistTracksResult,
    _scrape_playlist_embed,
    SpotifyForbiddenError,
)


def _make_embed_html(tracks, *, attr_order="id_first"):
    """Build a fake Spotify embed page wrapping the given tracks in
    the same __NEXT_DATA__ shape Spotify ships in production.
    attr_order toggles between the two known good script-tag layouts
    so we can exercise the regex tolerance.
    """
    payload = {
        "props": {
            "pageProps": {
                "state": {
                    "data": {
                        "entity": {
                            "trackList": tracks,
                        }
                    }
                }
            }
        }
    }
    blob = json.dumps(payload)
    if attr_order == "id_first":
        tag = '<script id="__NEXT_DATA__" type="application/json">'
    elif attr_order == "type_first":
        tag = '<script type="application/json" id="__NEXT_DATA__">'
    elif attr_order == "with_nonce":
        tag = '<script nonce="abc123" id="__NEXT_DATA__" type="application/json" crossorigin="anonymous">'
    else:
        raise ValueError(attr_order)
    return f"<html><body>{tag}{blob}</script></body></html>"


def _track(idx, *, artists="Test Artist", explicit=False):
    return {
        "uri": f"spotify:track:track{idx:03d}",
        "title": f"Song {idx}",
        "subtitle": artists,
        "duration": 180000 + idx,
        "isExplicit": explicit,
        "visualIdentity": {"image": [{"url": f"https://i.scdn.co/cover{idx}.jpg"}]},
    }


def _mock_response(text, status_code=200):
    resp = MagicMock()
    resp.status_code = status_code
    resp.text = text
    return resp


@pytest.mark.parametrize("attr_order", ["id_first", "type_first", "with_nonce"])
def test_scrape_tolerates_script_attribute_reorder(attr_order):
    """The regex must accept id-first, type-first, AND nonce-prefixed
    script tags so a Next.js framework bump on Spotify's side doesn't
    silently kill playlist imports."""
    html = _make_embed_html([_track(1)], attr_order=attr_order)
    with patch("backend.services.spotify_service.requests.get", return_value=_mock_response(html)):
        tracks = _scrape_playlist_embed("dummy_playlist_id", logger=MagicMock())
    assert len(tracks) == 1
    assert tracks[0]["spotify_id"] == "track001"


def test_scrape_extracts_full_track_shape():
    """Pin the field shape downstream import code consumes."""
    raw = [
        _track(1, artists="Drake, Future"),
        _track(2, artists="Solo Artist · Featured Artist"),
        _track(3, artists="Single Artist", explicit=True),
    ]
    html = _make_embed_html(raw)
    with patch("backend.services.spotify_service.requests.get", return_value=_mock_response(html)):
        tracks = _scrape_playlist_embed("p", logger=MagicMock())

    assert len(tracks) == 3

    assert tracks[0]["title"] == "Song 1"
    assert tracks[0]["primary_artist"] == "Drake"
    assert tracks[0]["all_artists"] == ["Drake", "Future"]
    assert tracks[0]["duration_ms"] == 180001
    assert tracks[0]["explicit"] is False
    assert tracks[0]["spotify_url"] == "https://open.spotify.com/track/track001"
    assert tracks[0]["album_art"] == "https://i.scdn.co/cover1.jpg"
    assert tracks[0]["isrc"] is None  # filled in by enrichment, not embed

    # " · " delimiter must round-trip the same way ", " does
    assert tracks[1]["all_artists"] == ["Solo Artist", "Featured Artist"]
    assert tracks[1]["primary_artist"] == "Solo Artist"

    assert tracks[2]["explicit"] is True


def test_scrape_empty_tracklist_raises_forbidden():
    """A private/empty playlist returns an empty trackList — surface
    a SpotifyForbiddenError so the route renders the user-readable
    fallback banner instead of bubbling a 500."""
    html = _make_embed_html([])
    with patch("backend.services.spotify_service.requests.get", return_value=_mock_response(html)):
        with pytest.raises(SpotifyForbiddenError):
            _scrape_playlist_embed("p", logger=MagicMock())


def test_scrape_missing_next_data_raises_forbidden():
    """If Spotify changes the embed page format and __NEXT_DATA__ is
    missing entirely, fail loudly with a SpotifyForbiddenError so the
    route can surface a useful banner."""
    html = "<html><body>no next data here</body></html>"
    with patch("backend.services.spotify_service.requests.get", return_value=_mock_response(html)):
        with pytest.raises(SpotifyForbiddenError):
            _scrape_playlist_embed("p", logger=MagicMock())


def test_embed_truncated_flag_is_strict_equal_to_cap():
    """embed_truncated must be True if and only if the embed returned
    EXACTLY _EMBED_TRACK_CAP tracks. Below the cap = playlist actually
    that small (no banner). At the cap = could continue past what the
    embed surfaced (show the banner)."""
    # Below the cap: no truncation flag.
    short_html = _make_embed_html([_track(i) for i in range(1, _EMBED_TRACK_CAP)])
    with patch("backend.services.spotify_service.requests.get", return_value=_mock_response(short_html)):
        short = _scrape_playlist_embed("p", logger=MagicMock())
    short_result = _PlaylistTracksResult(short)
    short_result.embed_truncated = len(short) == _EMBED_TRACK_CAP
    assert short_result.embed_truncated is False
    assert len(short_result) == _EMBED_TRACK_CAP - 1

    # Exactly at the cap: truncation flag flips on.
    full_html = _make_embed_html([_track(i) for i in range(1, _EMBED_TRACK_CAP + 1)])
    with patch("backend.services.spotify_service.requests.get", return_value=_mock_response(full_html)):
        full = _scrape_playlist_embed("p", logger=MagicMock())
    full_result = _PlaylistTracksResult(full)
    full_result.embed_truncated = len(full) == _EMBED_TRACK_CAP
    assert full_result.embed_truncated is True
    assert len(full_result) == _EMBED_TRACK_CAP


def test_dispatcher_falls_back_from_403_to_embed_with_enrichment():
    """End-to-end dispatcher contract: when the Web API
    /playlists/{id}/tracks returns 403 (the everyday Development Mode
    blocker), _fetch_playlist_with_token must (a) catch
    SpotifyForbiddenError, (b) scrape the embed, (c) enrich each track
    via /v1/tracks?ids=... so ISRC/album/release_date/popularity/label
    land in the response, and (d) flip embed_truncated correctly. This
    is the regression guard for the whole import flow shipping in
    Task #153.
    """
    from backend.services import spotify_service

    # Embed page returns exactly the cap so embed_truncated must be True.
    embed_payload = [_track(i) for i in range(1, _EMBED_TRACK_CAP + 1)]
    embed_html = _make_embed_html(embed_payload)

    # Build a fake /v1/tracks?ids=... enrichment response keyed by id.
    def _enriched(idx):
        tid = f"track{idx:03d}"
        return {
            "id": tid,
            "external_ids": {"isrc": f"USRC1700{idx:04d}"},
            "album": {
                "name": f"Album {idx}",
                "release_date": "2024-01-15",
                "label": "Test Label",
                "images": [{"url": f"https://i.scdn.co/album{idx}.jpg"}],
            },
            "popularity": 50 + idx % 10,
        }

    def _spotify_get_stub(endpoint, token, params=None):
        # Playlist endpoint: simulate Development Mode 403.
        if endpoint.startswith("playlists/"):
            raise SpotifyForbiddenError(
                "Spotify denied access to this playlist's tracks. (test stub)"
            )
        # Enrichment endpoint: return matching track records.
        if endpoint == "tracks":
            ids = (params or {}).get("ids", "").split(",")
            tracks = []
            for tid in ids:
                if tid.startswith("track"):
                    idx = int(tid.replace("track", ""))
                    tracks.append(_enriched(idx))
            return {"tracks": tracks}
        return None

    with patch("backend.services.spotify_service.requests.get", return_value=_mock_response(embed_html)), \
         patch("backend.services.spotify_service._spotify_get", side_effect=_spotify_get_stub):
        result = spotify_service._fetch_playlist_with_token(
            "p_dev_mode_403", "fake_token", MagicMock()
        )

    # Returned the list-subclass with the truncation flag.
    assert isinstance(result, _PlaylistTracksResult)
    assert result.embed_truncated is True
    assert len(result) == _EMBED_TRACK_CAP

    # Embed-derived fields preserved.
    first = result[0]
    assert first["spotify_id"] == "track001"
    assert first["title"] == "Song 1"
    assert first["primary_artist"] == "Test Artist"

    # Enrichment-derived fields filled in via /v1/tracks?ids=...
    # (label is on /v1/albums only, not /v1/tracks, so we don't assert it.)
    assert first["isrc"] == "USRC17000001"
    assert first["album_name"] == "Album 1"
    assert first["release_date"] == "2024-01-15"
    assert first["popularity"] is not None


def test_dispatcher_does_not_swallow_auth_errors():
    """A SpotifyAuthError from /playlists/{id}/tracks (token expired
    / revoked) must NOT trigger the embed fallback — it must propagate
    so the higher-level token-rotation logic in _fetch_with_retries
    can swap tokens and the user sees a reconnect prompt instead of
    silently downgraded data.
    """
    from backend.services import spotify_service
    from backend.services.spotify_service import SpotifyAuthError

    def _raise_auth(endpoint, token, params=None):
        raise SpotifyAuthError("token expired (test stub)")

    with patch("backend.services.spotify_service._spotify_get", side_effect=_raise_auth), \
         patch("backend.services.spotify_service.requests.get") as scrape_get:
        with pytest.raises(SpotifyAuthError):
            spotify_service._fetch_playlist_with_token("p_auth_fail", "stale_token", MagicMock())
        # Embed fallback path must not have been touched.
        scrape_get.assert_not_called()


def test_playlist_tracks_result_serializes_as_plain_list():
    """The list-subclass carries the embed_truncated sidecar without
    breaking downstream consumers that expect a vanilla list (json
    serialization, list comprehension, etc.)."""
    result = _PlaylistTracksResult([{"spotify_id": "abc"}])
    result.embed_truncated = True

    # Iteration / indexing still work
    assert result[0]["spotify_id"] == "abc"
    assert list(result) == [{"spotify_id": "abc"}]

    # Standard json encoder treats list subclasses as lists — the flag
    # is intentionally NOT serialized (the route surfaces it explicitly
    # via getattr).
    assert json.loads(json.dumps(result)) == [{"spotify_id": "abc"}]
    assert result.embed_truncated is True
