# Cadence - Catalog Intelligence - Multi-Tenant Rights & Catalog Administration

## Overview
Cadence is a multi-tenant platform for music industry professionals, designed to manage music catalogs, rights, and creator relationships. It provides tools for catalog valuation, rights administration, creator management, and placement tracking. The platform aims to offer insights into catalog performance and value, with an intuitive user interface inspired by Apple Music, serving as a comprehensive solution for maximizing catalog value and streamlining music industry operations.

## User Preferences
### Coding Style
- Python: PEP 8 style, type hints, SQLAlchemy ORM patterns
- JavaScript/React: Functional components, hooks, modern ES6+
- CSS: Tailwind utility classes with gradient themes
- Imports: Absolute imports for backend modules

## System Architecture
Cadence uses a modern tech stack with React 18 and Tailwind CSS for the frontend, and FastAPI with SQLAlchemy and PostgreSQL for the backend.

### UI/UX Decisions
The frontend employs an Apple Music-style aesthetic with a collapsible sidebar, gradient headers, rounded cards, and smooth transitions. It features a primary sage-green color scheme and is optimized for mobile devices. Key dashboards include Creator Roster, Creator Profiles, Catalog View, Placement Tracking Timeline, Reports (powered by Recharts), and Catalog Valuation. User experience is enhanced through modular widget dashboards and grid/list view toggles. The UI supports multiple valuation methodologies (Income, Market Comparable, DCF, Blended) with a toggle, historical trend charts, and PDF report generation.

### Technical Implementations
- **Multi-Tenant Architecture**: Ensures data isolation and organization-scoped access control.
- **Authentication**: JWT-based authentication with bcrypt for password hashing.
- **Data Models**: Comprehensive schema for Organizations, Users, Creators, Songs, Works, Releases, Contracts, Placements, and Royalty data.
- **Rights & Contract Tracking**: Supports deal-level contracts, asset-to-contract linking, and validates per-asset rights splits.
- **Multi-Client Song Grouping**: Facilitates shared song management across multiple clients.
- **Catalog Valuation Tool**: Utilizes multiple valuation engines (source-typed income, market comparable, discounted cash flow) and a 40/30/30 blended view to provide comprehensive catalog valuation, including an underwriting engine. Exposes the spec'd contract pair `GET /api/v1/organizations/{org_id}/valuation/catalog?creator_id=&method=` (income | market_comparable | dcf | blended) and `GET /api/v1/organizations/{org_id}/valuation/report/pdf?creator_id=` (ReportLab PDF), plus the prior `/api/valuation/full/{run,summary,trend}` orchestration routes. Per-creator share is RightsSplit-weighted via `_attribute_songs_to_creators` (single source of truth for both fresh-run and persisted summaries; falls back to equal-split SongCredit only when no RightsSplit rows exist for a song). Market-comparable per-stream tier bands are sourced from `backend/config/streaming_rates.py::MARKET_COMPARABLE_TIER_BANDS`. `SongStreamingMetrics.ownership_percentage` is canonically a **fraction** in [0.0, 1.0] (model default 1.0; seed values 1.0/0.5/0.25/0.333/0.125); the market-comparable engine treats values >1.0 as a legacy percent and divides by 100 (then clamps to [0,1]) for backward compatibility.
- **AI-Powered Data Ingestion**: Employs OpenAI for intelligent CSV column mapping, PDF/Word parsing, and contract term extraction.
- **Notification & Action Items System**: Provides customizable in-app and email notifications.
- **Placement Management**: Tracks sync licensing placements through a status pipeline.
- **Cross-Organization Client Sharing**: Implements a secure sharing workflow with email invitations and granular permissions.
- **Royalty Accounting System**: A financial engine for statement ingestion, asset matching, royalty calculation, and payment management, supporting multi-currency and PRO statements.
- **Release Delivery & Distribution Readiness**: Includes validation checks for release and track metadata.
- **Cloud Storage Integration**: Multi-provider integration (Dropbox, Google Drive) for linking audio files, with AI audio analysis.
- **Client Portal**: An organization-managed client login system for creators with full catalog management capabilities.
- **Streaming Credits & Intelligence**: A system for streaming intelligence, including chart data ingestion and cross-platform stream estimation.
- **Progressive Web App (PWA)**: Includes a web manifest and service worker for offline caching and push notifications.
- **Universal Document & Item Sharing**: Allows sharing various items via email or directly to other Cadence accounts.
- **Catalog Refactor**: Introduces "Unreleased" catalog sections and associated statuses.
- **Comprehensive Audit Logging**: Provides an organization-scoped audit trail for critical actions.
- **AI Assistant Chat**: A floating chat button powered by OpenAI `gpt-4o-mini` for natural language guidance. The knowledge base lives in `backend/data/assistant_app_guide.md` (UI guide) and `backend/data/assistant_industry_knowledge.md` (PRO/master/publishing/sync/splits/contracts terms) and is loaded once at module import. The route accepts a `PageContext` block (page, path, song_id, creator_id, etc) — pages and modals populate it via `frontend/src/lib/assistantContext.js` (`setAssistantContext`/`clearAssistantContext`), which writes to `window.__cadenceAssistantContext`. The assistant calls a tool registry in `backend/services/assistant_tools.py`: 8 read tools (search/get for songs, creators, contracts, royalties, action items) and 5 write tools (create_song/placement/action_item/contract_stub, update_placement_status). Write tools never mutate on first call — they build a `ProposedAction` (uuid, 10-min TTL, in a process-local lock-guarded dict) and return its summary. The route streams SSE events `tool_running`, `tool_result`, `proposed_action`, `content`, `error`, `done` (max 5 tool iterations). The user confirms via `POST /api/assistant/actions/{id}/confirm` (atomic claim — pop-under-lock prevents double-execute on rapid clicks) or cancels via `DELETE /api/assistant/actions/{id}`. Mutations write an audit-log entry tagged `details.source = "assistant"`. Backend gunicorn runs `workers=1` (see `backend/gunicorn_config.py`), which is why the in-memory action store is safe.
- **Production Infrastructure Foundation**: Features APP_ENV-driven environment separation, `/health` endpoint, hardened CORS, `X-Request-ID` for structured JSON logs, HTTPS enforcement, and global exception handlers.
- **Spotify Integration**: Integrates with Spotify via OAuth for listener-authenticated and client-credentials calls, including token management and fallbacks.
- **Spotify Playlist Import**: Supports importing Spotify playlists, with a public embed fallback for restricted API access.
- **Spotify Popularity Cache + Circuit Breaker**: Implements a process-wide circuit breaker for Spotify API calls and a persistent per-song popularity cache.
- **Spotify Bulk-Track Lookup with Per-Track Fallback**: Handles Spotify API limitations on bulk track lookups by falling back to individual track lookups.
- **Royalty Reconciliation Engine**: A financial-institution grade engine for reconciling royalty data, using `royalty_statements.total_revenue_cents` and `royalty_statement_lines.net_amount` as a single source of truth.
- **API Versioning**: Backend routes are namespaced under `/api/v1/` with mirroring of legacy `/api/` routes.
- **Modular Backend**: `models.py` has been split into 14 domain-specific modules for better organization and maintainability.
- **Advance Consolidation**: Legacy advance tables have been consolidated into a unified `advances` table with a backward-compatible API.
- **Royalty Audit Engine (Task #173 — A+ Phase 6)**: Four-check audit engine (`backend/services/audit_engine.py`) that scans a tenant's royalty data for `CROSS_STATEMENT` mismatches, `RATE_CHECK` shortfalls vs `MASTER_RATES`, `MISSING_PERIOD` gaps, and `DECAY_ANOMALY` deviations from the exponential decay fit. Findings persist to `royalty_audits` (idempotent at audit_type+song+period grain) and surface via `GET/POST /api/v1/organizations/{org_id}/audit/{findings,summary,scan,findings/{id}/resolve,findings/{id}/reopen}` plus the new frontend `AuditPage` (Analytics → Royalty Audit). Severity is bucketed CRITICAL/HIGH/MEDIUM/LOW from the % delta.
- **Luminate-Ready Streaming Metrics (Task #173)**: `SongStreamingMetrics` gained `luminate_total_streams`, `period_start`, `period_end`, `last_synced`, `data_source` columns (auto-`ALTER TABLE` on boot for existing deployments). New `LuminateService.import_csv` parses Luminate exports, matches songs by ISRC, upserts metrics tagged `data_source='luminate'`, and triggers an audit re-scan via `POST /api/v1/organizations/{org_id}/audit/luminate/import`.
- **Per-PRO Song Registration (Task #173)**: New `song_registrations` table (one row per song × registry: BMI/ASCAP/SESAC/GMR/MLC/SOUNDEXCHANGE/HFA) with `GET/PATCH /api/v1/songs/{song_id}/registrations[/{registry_type}]`. Lazy-backfills from legacy `Song.is_registered_with_pro` / `soundexchange_registered` / `mlc_registered` flags on first read. The scoring engine now consumes `registration_completeness` (0..1) into `metadata_health` (re-weighted to 7+7+7+4=25, chartmetric override preserved).
- **Performance Sweep (Task #173)**: New composite indexes — `ix_songs_org_is_released`, `ix_streaming_metrics_org_period`, plus per-table indexes on `royalty_audits` and `song_registrations`. Fixed N+1 in legacy `GET /api/songs` listing (`joinedload(Song.analytics)` + batch credit/creator lookup) so it issues 3 queries total instead of `1 + 2N`.
- **GitHub Issue Template (Task #173)**: `.github/ISSUE_TEMPLATE/task.yml` adds a structured Cadence Task form with Area + Priority + Type dropdowns and a `Done looks like` acceptance section.
- **Active-Org Pointer & Org Switcher (Task #190)**: New `users.current_organization_id` FK (`ON DELETE SET NULL`, idempotent ALTER + oldest-membership backfill in `db_setup._ensure_active_org_pointer`, defensive duplicate in `main.py` startup) replaces the unordered `OrganizationMember.first()` lookup that was leaking the wrong org's data into multi-org users' dashboards. `backend/utils/auth.py::resolve_active_org_id(db, user)` validates the pointer (must reference an org the user is still a member of), self-heals to the oldest membership when invalid, and persists the corrected value. All auto-resolution helpers (`organizations.get_current_organization`, `get_current_membership`, `actions.get_user_organization_id`, `audio._get_org_id`, `brief_builder._get_org_id`, `document_sharing._get_user_org`) consume it. `POST /api/v1/organizations/` now sets the pointer to the freshly-created org. New routes: `GET /api/v1/organizations/mine` (returns `{active_organization_id, organizations:[{id,name,display_name,type,logo_url,role,is_active}]}`) and `PATCH /api/v1/organizations/current` (body `{organization_id}`, enforces membership → 403 otherwise). Frontend `frontend/src/components/OrgSwitcher.jsx` (rendered in the Sidebar header for non-client users) eager-loads `/mine` on mount and PATCHes + `window.location.reload()`s on selection so every page's cached org-scoped fetches re-run for the new org (UI shows "Switching…" + disabled trigger during the transition). PATCH `/current` allows `is_cadence_staff` (in addition to `is_super_admin`) to switch into any org for cross-tenant support — mirroring `GET /api/organizations/{org_id}` — and writes an `organization.switch` audit-log entry tenant-scoped to the new org. For staff/super-admin durability, `resolve_active_org_id` honors a pointer at any *existing* org even when the user has no `OrganizationMember` row there (mirrors `PATCH /current`'s allowance and `GET /api/organizations/{org_id}` reads). Regular members are still strictly gated by membership. Regression coverage lives in `backend/tests/test_active_org_pointer_190.py` (9 tests: pointer-respecting `/current`, stale-pointer self-heal, `/mine` shape, PATCH persistence, 403 for non-member, durable Cadence-staff impersonation, fallback when an impersonated org is deleted, create-org auto-activation, and a creators-org-endpoint tenant-isolation guard). The migration also swept 25 additional unordered `OrganizationMember.user_id == current_user.id .first()` sites across `valuation_reports.py` (16), `integrations.py`, `auth.py` (login response role), `assistant.py`, `contracts_mgmt.py`, `creators.py`, `credits.py`, `support.py`, `tenant_admin.py` (3), and `works.py` to consume `get_active_membership(db, user)`. Two-filter patterns (user_id AND organization_id from URL) that verify membership of a specific URL-supplied org were intentionally left as-is. Existing JWTs stay valid — the pointer is server-side only.

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