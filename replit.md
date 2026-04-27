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
- **Spotify Integration (rotated 2026-04-27, Task #145)**: Cadence reaches Spotify two ways and BOTH must be rotated together when changing Spotify accounts — see "Spotify rotation runbook" in `DEPLOYMENT.md` §4 for the full procedure: (1) the **Replit Spotify connection** in this project (OAuth, used by `_get_replit_access_token()` in `backend/services/spotify_service.py` for playlist import / release lookup / track auto-fill); (2) the **Developer-app fallback** (`SPOTIFY_CLIENT_ID` + `SPOTIFY_CLIENT_SECRET` secrets, used by `_get_client_credentials_token()` for unauthenticated catalog/search calls in the chart ingester and AI track matcher). On 2026-04-27 both halves were rotated to a new account; the credentials and OAuth wiring are confirmed correct (the in-process smoke test acquired tokens from both paths) but the actual Spotify Web API responses returned 403 with two specific error strings observed verbatim in this session — the dev app needs Premium on the owner account and the new listener needs to be added to the dev app's Users and Access list before catalog calls will succeed. Tracked in follow-up Task #146.
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