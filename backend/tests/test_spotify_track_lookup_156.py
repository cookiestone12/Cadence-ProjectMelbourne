"""Task #156 — Spotify per-track fallback for bulk-track lookup.

Locks in the four acceptance criteria for
`spotify_service._batch_or_individual_track_lookup`:

  (a) Bulk `/v1/tracks?ids=` is used when Spotify returns 200.
  (b) Per-ID `/v1/tracks/{id}` fallback is used when bulk returns 403.
  (c) The returned dict is keyed by Spotify track ID.
  (d) Hard auth errors (`SpotifyAuthError`) propagate from per-ID
      fallback — the helper does not silently swallow them.

These tests guard the real production fix that restored the Credits
tab from "Total Estimated Streams: 0" by routing around Spotify's
Development-Mode block on the bulk endpoint.
"""
import logging
import pytest

from backend.services import spotify_service
from backend.services.spotify_service import (
    SpotifyAuthError,
    SpotifyForbiddenError,
    _batch_or_individual_track_lookup,
)


_LOG = logging.getLogger("test_156")


def _track_record(track_id: str, popularity: int = 80) -> dict:
    return {
        "id": track_id,
        "name": f"Track {track_id}",
        "popularity": popularity,
        "external_ids": {"isrc": f"ISRC{track_id}"},
        "album": {"name": f"Album {track_id}", "release_date": "2024-01-01", "images": []},
        "artists": [{"name": "Artist"}],
    }


def test_bulk_path_used_when_spotify_returns_200(monkeypatch):
    """Acceptance (a): happy path — bulk endpoint succeeds, no per-ID fallback."""
    calls = []

    def fake_get(endpoint, token, params=None):
        calls.append((endpoint, params))
        assert endpoint == "tracks", "Bulk path must use the collection endpoint"
        ids = params["ids"].split(",")
        return {"tracks": [_track_record(tid) for tid in ids]}

    monkeypatch.setattr(spotify_service, "_spotify_get", fake_get)

    result = _batch_or_individual_track_lookup(["aaa111", "bbb222", "ccc333"], "token", _LOG)

    assert set(result.keys()) == {"aaa111", "bbb222", "ccc333"}
    assert all(r["popularity"] == 80 for r in result.values())
    # Exactly one bulk call. No per-track fallback fired.
    assert len(calls) == 1
    assert calls[0][0] == "tracks"
    assert calls[0][1] == {"ids": "aaa111,bbb222,ccc333"}


def test_per_id_fallback_used_when_bulk_returns_403(monkeypatch):
    """Acceptance (b): bulk 403 triggers per-ID lookup loop."""
    calls = []

    def fake_get(endpoint, token, params=None):
        calls.append(endpoint)
        if endpoint == "tracks":
            raise SpotifyForbiddenError("dev-mode bulk block")
        # endpoint is "tracks/{id}"
        tid = endpoint.split("/", 1)[1]
        return _track_record(tid, popularity=55)

    monkeypatch.setattr(spotify_service, "_spotify_get", fake_get)

    result = _batch_or_individual_track_lookup(["x", "y", "z"], "token", _LOG)

    # Bulk attempted once, then three per-ID lookups.
    assert calls[0] == "tracks"
    assert sorted(calls[1:]) == ["tracks/x", "tracks/y", "tracks/z"]


def test_result_is_keyed_by_track_id(monkeypatch):
    """Acceptance (c): the dict is keyed by Spotify track ID."""

    def fake_get(endpoint, token, params=None):
        ids = params["ids"].split(",")
        # Return them in REVERSE order on purpose — the helper must key
        # off `record["id"]`, not the order Spotify returns records in.
        return {"tracks": [_track_record(tid) for tid in reversed(ids)]}

    monkeypatch.setattr(spotify_service, "_spotify_get", fake_get)

    result = _batch_or_individual_track_lookup(["A", "B", "C"], "token", _LOG)

    assert result["A"]["id"] == "A"
    assert result["B"]["id"] == "B"
    assert result["C"]["id"] == "C"


def test_auth_error_propagates_from_per_id_fallback(monkeypatch):
    """Acceptance (d): SpotifyAuthError is re-raised, never swallowed.

    Forces bulk to 403 (so we go into the per-ID loop), then makes
    the very first per-ID call raise SpotifyAuthError. The helper
    must let it bubble up so callers can surface "reconnect required"
    instead of degrading to a misleading empty result.
    """

    def fake_get(endpoint, token, params=None):
        if endpoint == "tracks":
            raise SpotifyForbiddenError("dev-mode bulk block")
        raise SpotifyAuthError("token expired")

    monkeypatch.setattr(spotify_service, "_spotify_get", fake_get)

    with pytest.raises(SpotifyAuthError):
        _batch_or_individual_track_lookup(["x", "y"], "token", _LOG)


def test_mid_batch_403_preserves_already_resolved(monkeypatch):
    """Bonus: when bulk succeeds for chunk 1 but 403s on chunk 2, the
    per-ID fallback must not re-fetch the IDs we already have.

    This is the partial-success contract the architect highlighted —
    we don't want a 403 mid-run to wipe out chunk-1 results.
    """
    track_ids = [f"id{i:02d}" for i in range(60)]  # forces TWO chunks (50 + 10)
    bulk_calls = []
    per_id_calls = []

    def fake_get(endpoint, token, params=None):
        if endpoint == "tracks":
            bulk_calls.append(params["ids"].split(","))
            ids = params["ids"].split(",")
            if len(bulk_calls) == 1:
                # Chunk 1 succeeds.
                return {"tracks": [_track_record(tid) for tid in ids]}
            # Chunk 2 hits the dev-mode block.
            raise SpotifyForbiddenError("dev-mode bulk block")
        # Per-ID fallback path.
        tid = endpoint.split("/", 1)[1]
        per_id_calls.append(tid)
        return _track_record(tid)

    monkeypatch.setattr(spotify_service, "_spotify_get", fake_get)

    result = _batch_or_individual_track_lookup(track_ids, "token", _LOG)

    # All 60 tracks resolved — 50 from the successful bulk chunk,
    # 10 via per-ID fallback after chunk-2 was blocked.
    assert set(result.keys()) == set(track_ids)
    # Per-ID loop only re-fetched the 10 IDs from the blocked chunk,
    # not the 50 already-resolved ones.
    assert sorted(per_id_calls) == sorted(track_ids[50:])


def test_empty_inputs_short_circuit(monkeypatch):
    """Defensive: empty ID list or empty token returns {} without any HTTP."""

    def fake_get(*a, **kw):
        raise AssertionError("Should not call Spotify when inputs are empty")

    monkeypatch.setattr(spotify_service, "_spotify_get", fake_get)

    assert _batch_or_individual_track_lookup([], "token", _LOG) == {}
    assert _batch_or_individual_track_lookup(["x"], "", _LOG) == {}


# ---------------------------------------------------------------------------
# Codifies the credits-service degrade contract on SpotifyAuthError.
# Per the architect review: the helper re-raises auth errors, but the
# Credits-tab caller intentionally catches them and degrades to an empty
# popularity map so the page still renders. This test locks in that UX —
# if we ever want to bubble auth errors up to the user instead, this test
# is the place to flip it (and a corresponding "reconnect required" UX
# would land in the same change).
# ---------------------------------------------------------------------------
class _StubSong:
    def __init__(self, spotify_link):
        self.spotify_link = spotify_link
        self.title = "T"
        self.primary_artist = "A"


def test_credits_batch_fetch_degrades_on_spotify_auth_error(monkeypatch):
    from backend.services import credits_service

    monkeypatch.setattr(spotify_service, "_get_access_token", lambda: "token")

    def boom(track_ids, token, logger):
        raise SpotifyAuthError("token expired mid-run")

    monkeypatch.setattr(spotify_service, "_batch_or_individual_track_lookup", boom)
    # Block the search-fallback branch from doing any real HTTP either.
    monkeypatch.setattr(spotify_service, "_spotify_get", lambda *a, **kw: None)

    songs = {1: _StubSong("https://open.spotify.com/track/abc123XYZ")}

    # The function holds a Session reference but only uses it for the
    # DSP-link fallback; with spotify_link set we never reach it.
    result = credits_service._batch_fetch_spotify_popularity(songs, db=None)

    # Degrade contract: empty result, no crash. If we ever decide to
    # surface "reconnect required" to the UI, this assertion (and the
    # corresponding except-block in credits_service) flip together.
    assert result == {}
