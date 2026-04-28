# Cadence - Catalog Intelligence - Multi-Tenant Rights & Catalog Administration

## Overview
Cadence is a multi-tenant platform for music industry professionals designed to manage music catalogs, rights, and creator relationships. It offers tools for catalog valuation, rights administration, creator management, and placement tracking, providing insights into catalog performance and value. The platform aims for an intuitive user interface, inspired by Apple Music, to serve as a comprehensive solution for maximizing catalog value and streamlining operations in the music industry.

## User Preferences
### Coding Style
- Python: PEP 8 style, type hints, SQLAlchemy ORM patterns
- JavaScript/React: Functional components, hooks, modern ES6+
- CSS: Tailwind utility classes with gradient themes
- Imports: Absolute imports for backend modules

## System Architecture
Cadence utilizes a modern tech stack comprising React 18 with Tailwind CSS for the frontend, and FastAPI with SQLAlchemy and PostgreSQL for the backend.

### UI/UX Decisions
The frontend features an Apple Music-style aesthetic, including a collapsible sidebar, gradient headers, rounded cards, and smooth transitions. It is optimized for mobile devices with a primary sage-green color scheme. Key dashboards cover Creator Roster, Creator Profiles, Catalog View, Placement Tracking Timeline, Reports with Recharts, and Catalog Valuation. User experience is enhanced with modular widget dashboards and grid/list view toggles.

### Technical Implementations
- **Multi-Tenant Architecture**: Ensures data isolation and organization-scoped access control.
- **Authentication**: JWT-based authentication with bcrypt for password hashing.
- **Data Models**: Comprehensive schema for various entities including Organizations, Users, Creators, Songs, Works, Releases, Contracts, Placements, and Royalty data.
- **Rights & Contract Tracking**: Supports deal-level contracts, asset-to-contract linking, and validates per-asset rights splits. Song-level publishing and master percentages are derived from credit-level splits.
- **Multi-Client Song Grouping**: Facilitates shared song management across multiple clients.
- **Catalog Valuation Tool**: Uses a weighted average of industry metrics and a proprietary Black Box Algorithm, including an underwriting engine for statement-driven valuations.
- **AI-Powered Data Ingestion**: Employs OpenAI for intelligent column mapping in CSV imports, parsing PDF/Word Schedule A documents, and extracting key contract terms.
- **Notification & Action Items System**: Provides customizable in-app and email notifications and manages proactive, deadline-driven action items.
- **Placement Management**: Tracks sync licensing placements through a status pipeline.
- **Cross-Organization Client Sharing**: Implements a secure sharing workflow with email invitations, role-based catalog synchronization, and granular permissions.
- **Royalty Accounting System**: A financial engine for statement ingestion, asset matching, royalty calculation, and payment management, supporting multi-currency and PRO statements with a focus on data reconciliation.
- **Release Delivery & Distribution Readiness**: Includes validation checks for release and track metadata.
- **Cloud Storage Integration**: Multi-provider integration (Dropbox, Google Drive) for linking audio files, featuring AI audio analysis and an organization-wide audio linking pipeline.
- **Client Portal**: An organization-managed client login system for creators with full catalog management capabilities.
- **Streaming Credits & Intelligence**: A system inspired by Muso.ai for streaming intelligence, including chart data ingestion and cross-platform stream estimation.
- **Progressive Web App (PWA)**: Includes a web manifest and service worker for offline caching and push notifications.
- **Universal Document & Item Sharing**: Allows sharing various items via email or directly to other Cadence accounts.
- **Catalog Refactor — Released/Unreleased Model**: Introduces "Unreleased" catalog sections and associated statuses.
- **Comprehensive Audit Logging**: Provides an organization-scoped audit trail for critical actions, including song edit history.
- **AI Assistant Chat**: A floating chat button powered by OpenAI `gpt-4o-mini` for natural language guidance within the app.
- **Production Infrastructure Foundation**: Features APP_ENV-driven environment separation, `/health` endpoint, hardened CORS, per-request `X-Request-ID` for structured JSON logs, HTTPS enforcement, and global exception handlers. Deployment targets a Reserved VM to ensure continuous operation of APScheduler jobs. The application's boot critical path is optimized to ensure fast startup times.
- **Spotify Integration (project-owned OAuth, 2026-04-28)**: Cadence now talks to Spotify through a single operator-owned Spotify Developer app via two call modes that share the same `SPOTIFY_CLIENT_ID` / `SPOTIFY_CLIENT_SECRET`: (1) **Authorization-Code OAuth** for listener-authenticated calls (playlist import, release lookup, pasted-URL track auto-fill), with tokens persisted in the `spotify_oauth_tokens` singleton table and managed by `backend/services/spotify_oauth.py` (auto-refresh <60s before expiry, signed HMAC state cookie, redirect URI resolves to `SPOTIFY_REDIRECT_URI` env if set, else always `https://cadence-ci.com/api/spotify/oauth/callback` — the dev workspace deliberately reuses the production URL because the Vite dev server doesn't proxy `/api/*` to FastAPI and a callback landing on `*.picard.replit.dev` would just hit Replit's "Run this app" splash; the popup completes against prod and `postMessage`s the result cross-origin back to the opener regardless of where Connect was clicked from); and (2) **client-credentials** for unauthenticated catalog/search calls. The new OAuth flow is wired through `backend/routes/spotify_oauth.py` (`/start`, `/callback`, `/status`, `/disconnect`) and surfaced in Admin → API Configuration → Spotify with Connect / Reconnect / Disconnect buttons plus a copy-able redirect URI. `spotify_service._get_access_token()` priority is now project_oauth → connector (legacy fallback) → client_credentials. The Replit Spotify connector path is retained as a fallback but is no longer primary, which removes the Replit-managed-dev-app allowlist gate that broke the prior rotation. The dev-app owner still needs Premium for the client-credentials half, and (while the dev app is in Development Mode) the OAuth listener account must be on the dev app's *Users and Access* list. See `DEPLOYMENT.md` §4 "Spotify rotation runbook" for the full procedure.
- **Spotify Playlist Import — Public Embed Fallback (2026-04-28, Task #153)**: Spotify's Web API blocks `/playlists/{id}/tracks` for any app in Development Mode that doesn't own the playlist (Extended Quota Mode requires 250k MAU and is unreachable for B2B catalog tools). When the Web API call raises `SpotifyForbiddenError`, `_fetch_playlist_with_token` automatically falls back to scraping `https://open.spotify.com/embed/playlist/{id}` — the public embed page ships the full track list inside a `__NEXT_DATA__` JSON blob with no auth required (same technique Soundiiz/TuneMyMusic/Exportify have used for years). Each scraped track is then enriched with ISRC, album name, release date, popularity, and explicit flag via batched `/v1/tracks?ids=…` calls (which still work). Album label is *not* in the `/v1/tracks` payload (Spotify only returns it on `/v1/albums`), so the embed-fallback path leaves `label` unset on imported tracks. The embed page caps the pre-rendered tracklist at exactly 50 entries; the route response carries an `embed_truncated: true` flag and the import dialog shows a friendly banner explaining the cap. Album, artist and single-track URL paths are unchanged. Lazy-load pagination beyond 50 tracks is deferred. Single point of integration: `backend/services/spotify_service.py` `_scrape_playlist_embed`, `_enrich_tracks_via_api`, `_fetch_playlist_with_token`.
- **Spotify Bulk-Track Lookup — Per-Track Fallback (2026-04-28, Task #156)**: The same Development-Mode policy that blocks `/playlists/{id}/tracks` also 403s the bulk track endpoint `GET /v1/tracks?ids=…`, which Cadence relied on in two places: (1) the playlist-embed enrichment from Task #153, and (2) `credits_service._batch_fetch_spotify_popularity` for the Creator Profile → Credits tab. When that bulk call was blocked, the Credits tab silently rendered `Total Estimated Streams: 0` for every song even though OAuth was healthy and the songs all had valid Spotify links. The fix is a single new helper `spotify_service._batch_or_individual_track_lookup(track_ids, token, logger)` that tries the bulk endpoint first and on `SpotifyForbiddenError` falls back to looping `GET /v1/tracks/{id}` one ID at a time — the single-track endpoint is *not* affected by the same policy block, so it still returns real popularity, ISRC, album metadata for accounts whose dev app doesn't have Extended Quota Mode. Both `_enrich_tracks_via_api` (Task #153 path) and `_batch_fetch_spotify_popularity` (credits path) now route through this helper, so any future bulk Spotify endpoint we add gets the same protection from one place. A second wart this task fixed: Spotify's `/v1/search` is similarly degraded in Development Mode and returns `popularity = 0` on every result. Both `credits_service._batch_fetch_spotify_popularity` (search-fallback branch) and `stream_estimator.estimate_streams_for_song` (search-fallback branch) now do a single confirmatory `GET /v1/tracks/{id}` lookup whenever a search hit reports `popularity = 0`, and adopt the confirmed value if it's nonzero. Net result: per-song stream estimates and the Credits-tab "Total Estimated Streams" headline number now populate correctly on dev-app accounts.
- **Royalty Reconciliation Engine**: A financial-institution grade engine for reconciling royalty data, using `royalty_statements.total_revenue_cents` and `royalty_statement_lines.net_amount` as a single source of truth. It includes comprehensive validation for uploaded statements.

## External Dependencies
- PostgreSQL
- React
- FastAPI
- SQLAlchemy
- Tailwind CSS
- Vite
- Recharts
- Heroicons
- @dnd-kit
- html2canvas
- PyJWT
- Bcrypt
- openpyxl
- OpenAI
- Alembic
- Gunicorn
- Resend
- APScheduler
- Dropbox SDK
- Cryptography
- pywebpush
- ReportLab