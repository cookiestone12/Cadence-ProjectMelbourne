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


@pytest.fixture(autouse=True)
def _reset_spotify_throttle():
    """Reset the module-level Spotify circuit breaker before each test.

    `_spotify_get` sets `spotify_service._spotify_throttled_until` whenever
    Spotify returns a 429 with a long Retry-After (daily-quota path), and
    that timestamp persists for the rest of the process. Without this
    fixture, the first test that trips the breaker causes every later
    test in the file to short-circuit the API path and observe empty
    results.
    """
    spotify_service._spotify_throttled_until = 0.0
    yield
    spotify_service._spotify_throttled_until = 0.0


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


def test_per_id_fallback_used_when_bulk_returns_silent_nulls(monkeypatch):
    """Task #157: Spotify Dev Mode does NOT 403 the bulk endpoint for
    blocked tracks — it returns HTTP 200 with `{"tracks": [null, …]}`.
    The helper must detect that and fall back to per-ID lookup, just
    like it does for an explicit 403.

    This is the production symptom that bit creator 38 ("Killah B")
    even after Task #156 shipped: every popularity came back null,
    `by_id` stayed empty, fallback never fired, Credits tab showed
    Total Estimated Streams: 0 for all 21 fully-linked songs.
    """
    calls = []

    def fake_get(endpoint, token, params=None):
        calls.append(endpoint)
        if endpoint == "tracks":
            # Bulk responds 200 with all-null tracks (Dev Mode policy).
            return {"tracks": [None, None, None]}
        # endpoint is "tracks/{id}" — single-track endpoint works fine.
        tid = endpoint.split("/", 1)[1]
        return _track_record(tid, popularity=66)

    monkeypatch.setattr(spotify_service, "_spotify_get", fake_get)

    result = _batch_or_individual_track_lookup(["x", "y", "z"], "token", _LOG)

    # All three resolved via per-ID fallback.
    assert set(result.keys()) == {"x", "y", "z"}
    assert all(r["popularity"] == 66 for r in result.values())
    # Bulk attempted once, then three per-ID lookups for the unresolved IDs.
    assert calls[0] == "tracks"
    assert sorted(calls[1:]) == ["tracks/x", "tracks/y", "tracks/z"]


def test_partial_silent_nulls_only_fall_back_for_unresolved(monkeypatch):
    """Task #157: when the bulk endpoint returns a mix of real records
    and nulls (e.g. one track the listener owns + two they don't), the
    per-ID fallback must only re-fetch the IDs Spotify nulled — not
    the ones already resolved by bulk."""
    calls = []

    def fake_get(endpoint, token, params=None):
        calls.append(endpoint)
        if endpoint == "tracks":
            ids = params["ids"].split(",")
            assert ids == ["a", "b", "c"]
            # Spotify resolves "a" but nulls "b" and "c".
            return {"tracks": [_track_record("a", popularity=42), None, None]}
        tid = endpoint.split("/", 1)[1]
        return _track_record(tid, popularity=77)

    monkeypatch.setattr(spotify_service, "_spotify_get", fake_get)

    result = _batch_or_individual_track_lookup(["a", "b", "c"], "token", _LOG)

    # All three resolved — "a" via bulk, "b" and "c" via per-ID.
    assert set(result.keys()) == {"a", "b", "c"}
    assert result["a"]["popularity"] == 42  # preserved from bulk
    assert result["b"]["popularity"] == 77  # rescued by per-ID
    assert result["c"]["popularity"] == 77  # rescued by per-ID
    # Crucially: per-ID loop did NOT re-fetch "a".
    per_id_calls = [c for c in calls if c.startswith("tracks/")]
    assert sorted(per_id_calls) == ["tracks/b", "tracks/c"]


def test_spotify_get_honors_retry_after_on_429(monkeypatch):
    """Spotify's per-track endpoint rate-limits us when the per-ID
    fallback fires for a 100-credit creator. Without 429 handling
    every retry returns None and popularity stays at 0 across the
    Credits tab. The 429-with-Retry-After path must wait the requested
    seconds (capped) and retry once.

    This is the regression that tripped creator 98 ('100 credits') on
    the production Credits tab right after Task #157 deployed: bulk
    silent-null detection worked correctly, but the per-ID fallback
    burst-fired ~200 calls in <1s and Spotify throttled all but the
    first ~10.
    """
    from backend.services import spotify_service as svc

    sleeps = []
    monkeypatch.setattr(svc.time, "sleep", lambda s: sleeps.append(s))

    class _Resp:
        def __init__(self, status, json_body=None, headers=None):
            self.status_code = status
            self._json = json_body or {}
            self.headers = headers or {}
            self.text = ""
        def json(self):
            return self._json
        def raise_for_status(self):
            if self.status_code >= 400:
                from requests import HTTPError
                raise HTTPError(f"HTTP {self.status_code}")

    call_log = []

    def fake_requests_get(url, headers=None, params=None, timeout=None):
        call_log.append(url)
        if len(call_log) == 1:
            return _Resp(429, headers={"Retry-After": "2"})
        return _Resp(200, json_body={"id": "abc", "popularity": 88})

    monkeypatch.setattr(svc.requests, "get", fake_requests_get)

    result = svc._spotify_get("tracks/abc", token="t")

    # Retried exactly once.
    assert len(call_log) == 2
    # Honored the Retry-After header (capped at 10s).
    assert sleeps == [2.0]
    # Returned the recovered payload.
    assert result == {"id": "abc", "popularity": 88}


def test_spotify_get_429_long_retry_after_trips_circuit_breaker(monkeypatch):
    """A long Retry-After (daily-quota exhaustion) must NOT sleep-and-retry.

    Spotify's Development-Mode dev apps cap at ~1k Web API calls per
    rolling 24h, and when exhausted return 429 with Retry-After in the
    tens of thousands of seconds. Sleeping and retrying inside a request
    handler is futile — the second call gets the same 429 and we've
    burned another quota slot for nothing. Instead the helper trips a
    process-wide circuit breaker and bails immediately, so the rest of
    the request can fall back to cached values.
    """
    from backend.services import spotify_service as svc

    sleeps = []
    monkeypatch.setattr(svc.time, "sleep", lambda s: sleeps.append(s))

    class _Resp:
        def __init__(self, status, json_body=None, headers=None):
            self.status_code = status
            self._json = json_body or {}
            self.headers = headers or {}
            self.text = ""
        def json(self): return self._json
        def raise_for_status(self):
            if self.status_code >= 400:
                from requests import HTTPError
                raise HTTPError(f"HTTP {self.status_code}")

    calls = [0]
    def fake_requests_get(url, headers=None, params=None, timeout=None):
        calls[0] += 1
        # Long Retry-After indicates daily-quota exhaustion. Should NOT retry.
        return _Resp(429, headers={"Retry-After": "27267"})

    monkeypatch.setattr(svc.requests, "get", fake_requests_get)
    result = svc._spotify_get("tracks/x", token="t")

    # No sleep, no retry — bailed immediately.
    assert sleeps == []
    assert calls[0] == 1
    assert result is None
    # Circuit breaker is now tripped — subsequent calls short-circuit.
    assert svc.is_spotify_throttled() is True
    # And next call doesn't hit the network at all.
    result2 = svc._spotify_get("tracks/y", token="t")
    assert result2 is None
    assert calls[0] == 1  # still 1, no second HTTP call made


def test_spotify_get_429_handles_malformed_or_missing_retry_after(monkeypatch):
    """`Retry-After` is sometimes missing entirely or non-numeric.
    The helper must default to 1s wait (clamped to the 0.5s floor)
    rather than crashing or sleeping forever."""
    from backend.services import spotify_service as svc

    sleeps = []
    monkeypatch.setattr(svc.time, "sleep", lambda s: sleeps.append(s))

    class _Resp:
        def __init__(self, status, json_body=None, headers=None):
            self.status_code = status
            self._json = json_body or {}
            self.headers = headers or {}
            self.text = ""
        def json(self): return self._json
        def raise_for_status(self):
            if self.status_code >= 400:
                from requests import HTTPError
                raise HTTPError(f"HTTP {self.status_code}")

    # --- Case 1: header missing entirely.
    calls = [0]
    def missing_header_get(url, headers=None, params=None, timeout=None):
        calls[0] += 1
        if calls[0] == 1:
            return _Resp(429, headers={})  # no Retry-After at all
        return _Resp(200, json_body={"id": "x"})
    monkeypatch.setattr(svc.requests, "get", missing_header_get)
    sleeps.clear()
    svc._spotify_get("tracks/x", token="t")
    assert sleeps == [1.0]  # default 1s, above the 0.5s floor

    # --- Case 2: header present but garbage.
    calls[0] = 0
    def garbage_header_get(url, headers=None, params=None, timeout=None):
        calls[0] += 1
        if calls[0] == 1:
            return _Resp(429, headers={"Retry-After": "not-a-number"})
        return _Resp(200, json_body={"id": "x"})
    monkeypatch.setattr(svc.requests, "get", garbage_header_get)
    sleeps.clear()
    svc._spotify_get("tracks/x", token="t")
    assert sleeps == [1.0]


def test_per_id_loop_paces_calls_with_50ms_breather(monkeypatch):
    """The per-ID fallback must insert a 50ms breather between calls
    (skipping the first), so a 100-credit catalog issues ~20 req/s
    instead of 200/s and stops tripping Spotify's rate limiter."""
    pace_sleeps = []

    def fake_sleep(s):
        pace_sleeps.append(s)

    monkeypatch.setattr(spotify_service.time, "sleep", fake_sleep)

    def fake_get(endpoint, token, params=None):
        if endpoint == "tracks":
            # Force the silent-null path so per-ID fallback runs for all 5 IDs.
            return {"tracks": [None, None, None, None, None]}
        tid = endpoint.split("/", 1)[1]
        return _track_record(tid)

    monkeypatch.setattr(spotify_service, "_spotify_get", fake_get)

    _batch_or_individual_track_lookup(["a", "b", "c", "d", "e"], "token", _LOG)

    # 5 IDs in the per-ID loop → 4 breathers (skip the first).
    assert pace_sleeps == [0.05, 0.05, 0.05, 0.05]


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


class _StubQuery:
    def query(self, *a, **kw): return self
    def filter(self, *a, **kw): return self
    def first(self): return None


def test_credits_search_branch_confirms_zero_popularity_via_tracks_endpoint(monkeypatch):
    """Search returns popularity=0 in Spotify Development Mode for every
    hit, but `tracks/{id}` returns the real value. The credits search
    branch must rescue the popularity by issuing one confirmation call
    per zero-pop hit. Without this rescue the Credits tab silently
    showed 0 streams for every song without a direct Spotify link.
    """
    from backend.services import credits_service

    # Song with no Spotify link → falls into the search branch (after
    # the SongDSPLink fallback also returns None).
    song = _StubSong(spotify_link=None)
    songs = {42: song}
    db = _StubQuery()

    monkeypatch.setattr(spotify_service, "_get_access_token", lambda: "token")

    calls = []

    def fake_spotify_get(endpoint, token, params=None):
        calls.append((endpoint, params))
        if endpoint == "search":
            # Spotify dev-mode degraded search: real metadata but pop=0.
            return {
                "tracks": {
                    "items": [
                        {
                            "id": "rescue_me_id",
                            "name": "Rescue Me",
                            "popularity": 0,  # the lie we need to confirm
                            "album": {"images": [{"url": "https://img/x.jpg"}]},
                        }
                    ]
                }
            }
        if endpoint == "tracks/rescue_me_id":
            # The single-track endpoint returns the truth.
            return {"id": "rescue_me_id", "popularity": 73}
        raise AssertionError(f"unexpected endpoint {endpoint}")

    monkeypatch.setattr(spotify_service, "_spotify_get", fake_spotify_get)

    result = credits_service._batch_fetch_spotify_popularity(songs, db=db)

    # Rescue worked: real popularity adopted.
    assert result == {42: {"popularity": 73, "album_art": "https://img/x.jpg"}}
    # We did exactly one search and one confirmation lookup.
    assert [c[0] for c in calls] == ["search", "tracks/rescue_me_id"]
