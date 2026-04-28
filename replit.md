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
The frontend employs an Apple Music-style aesthetic with a collapsible sidebar, gradient headers, rounded cards, and smooth transitions. It features a primary sage-green color scheme and is optimized for mobile devices. Key dashboards include Creator Roster, Creator Profiles, Catalog View, Placement Tracking Timeline, Reports (powered by Recharts), and Catalog Valuation. User experience is enhanced through modular widget dashboards and grid/list view toggles.

### Technical Implementations
- **Multi-Tenant Architecture**: Ensures data isolation and organization-scoped access control.
- **Authentication**: JWT-based authentication with bcrypt for password hashing.
- **Data Models**: Comprehensive schema for entities like Organizations, Users, Creators, Songs, Works, Releases, Contracts, Placements, and Royalty data.
- **Rights & Contract Tracking**: Supports deal-level contracts, asset-to-contract linking, and validates per-asset rights splits, deriving song-level percentages from credit-level splits.
- **Multi-Client Song Grouping**: Facilitates shared song management across multiple clients.
- **Catalog Valuation Tool**: Utilizes a weighted average of industry metrics and a proprietary Black Box Algorithm, including an underwriting engine for statement-driven valuations.
- **AI-Powered Data Ingestion**: Employs OpenAI for intelligent CSV column mapping, PDF/Word Schedule A parsing, and contract term extraction.
- **Notification & Action Items System**: Provides customizable in-app and email notifications, managing proactive, deadline-driven action items.
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
- **Production Infrastructure Foundation**: Features APP_ENV-driven environment separation, `/health` endpoint, hardened CORS, per-request `X-Request-ID` for structured JSON logs, HTTPS enforcement, and global exception handlers. Deployment targets a Reserved VM to ensure continuous operation of APScheduler jobs.
- **Spotify Integration**: Cadence integrates with Spotify via a project-owned OAuth app for both listener-authenticated and client-credentials calls. This includes a robust OAuth flow, token management, and fallback mechanisms for API limitations in development mode.
- **Spotify Playlist Import**: Supports importing Spotify playlists, including a public embed fallback for cases where the Web API is restricted. This fallback scrapes track data from public embed pages.
- **Spotify Popularity Cache + Circuit Breaker**: Implements a process-wide circuit breaker for Spotify API calls to handle rate limiting and quota exhaustion. It also includes a persistent per-song popularity cache to reduce API calls and provide stream estimations even during throttling.
- **Spotify Bulk-Track Lookup with Per-Track Fallback**: Handles Spotify API limitations on bulk track lookups in development mode by falling back to individual track lookups when bulk requests are blocked or return nulls.
- **Royalty Reconciliation Engine**: A financial-institution grade engine for reconciling royalty data, using `royalty_statements.total_revenue_cents` and `royalty_statement_lines.net_amount` as a single source of truth, with comprehensive validation for uploaded statements.

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