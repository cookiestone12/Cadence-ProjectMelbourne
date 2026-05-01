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
- **AI Assistant Chat**: A floating chat button powered by OpenAI `gpt-4o-mini` for natural language guidance.
- **Production Infrastructure Foundation**: Features APP_ENV-driven environment separation, `/health` endpoint, hardened CORS, `X-Request-ID` for structured JSON logs, HTTPS enforcement, and global exception handlers.
- **Spotify Integration**: Integrates with Spotify via OAuth for listener-authenticated and client-credentials calls, including token management and fallbacks.
- **Spotify Playlist Import**: Supports importing Spotify playlists, with a public embed fallback for restricted API access.
- **Spotify Popularity Cache + Circuit Breaker**: Implements a process-wide circuit breaker for Spotify API calls and a persistent per-song popularity cache.
- **Spotify Bulk-Track Lookup with Per-Track Fallback**: Handles Spotify API limitations on bulk track lookups by falling back to individual track lookups.
- **Royalty Reconciliation Engine**: A financial-institution grade engine for reconciling royalty data, using `royalty_statements.total_revenue_cents` and `royalty_statement_lines.net_amount` as a single source of truth.
- **API Versioning**: Backend routes are namespaced under `/api/v1/` with mirroring of legacy `/api/` routes.
- **Modular Backend**: `models.py` has been split into 14 domain-specific modules for better organization and maintainability.
- **Advance Consolidation**: Legacy advance tables have been consolidated into a unified `advances` table with a backward-compatible API.

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