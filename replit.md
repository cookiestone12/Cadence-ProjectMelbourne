# Cadence - Catalog Intelligence - Multi-Tenant Rights & Catalog Administration

## Overview
Cadence is a multi-tenant platform for music industry professionals to manage music catalogs, rights, and creator relationships. It provides tools for catalog valuation, rights administration, creator management, and placement tracking, offering insights into catalog performance and value. The platform aims for an intuitive user interface inspired by Apple Music, serving as a comprehensive solution for music professionals to maximize catalog value and streamline operations.

## User Preferences
### Coding Style
- Python: PEP 8 style, type hints, SQLAlchemy ORM patterns
- JavaScript/React: Functional components, hooks, modern ES6+
- CSS: Tailwind utility classes with gradient themes
- Imports: Absolute imports for backend modules

## System Architecture
Cadence uses a modern tech stack with React 18 and Tailwind CSS for the frontend, and FastAPI with SQLAlchemy and PostgreSQL for the backend.

### UI/UX Decisions
The frontend adopts an Apple Music-style aesthetic, featuring a collapsible sidebar, gradient headers, rounded cards, and smooth transitions, optimized for mobile devices. The primary color scheme is sage-green. Key dashboards include Creator Roster, Creator Profiles, Catalog View, Placement Tracking Timeline, Reports with Recharts, and Catalog Valuation. Modular widget dashboards and grid/list view toggles enhance user experience.

### Technical Implementations
- **Multi-Tenant Architecture**: Ensures data isolation and organization-scoped access control.
- **Authentication**: JWT-based authentication with bcrypt for password hashing.
- **Data Models**: Comprehensive schema for Organizations, Users, Creators, Songs, Works, Releases, Contracts, Placements, and Royalty data.
- **Rights & Contract Tracking**: Supports deal-level contracts, asset-to-contract linking, and validates per-asset rights splits. Song-level Publishing % and Master % are read-only and derived from credit-level splits.
- **Multi-Client Song Grouping**: Facilitates shared song management across multiple clients.
- **Catalog Valuation Tool**: Employs a weighted average of industry metrics and a proprietary Black Box Algorithm, including an underwriting engine for statement-driven valuations and per-creator scope. Decay analytics provide insights into songs awaiting more data.
- **AI-Powered Data Ingestion**: Utilizes OpenAI for intelligent column mapping in CSV imports, parsing PDF/Word Schedule A documents, and extracting key terms from contracts.
- **Notification & Action Items System**: Customizable in-app and email notifications and a system for managing proactive, deadline-driven action items.
- **Placement Management**: Tracks sync licensing placements through a status pipeline.
- **Cross-Organization Client Sharing**: Secure sharing workflow with email invitations, role-based catalog synchronization, and granular permissions.
- **Royalty Accounting System**: Financial engine for statement ingestion, asset matching, royalty calculation, and payment management, supporting multi-currency and PRO statements, with a focus on single source of truth and reconciliation.
- **Release Delivery & Distribution Readiness**: Validation checks for release and track metadata.
- **Cloud Storage Integration**: Multi-provider integration (Dropbox, Google Drive) for linking audio files, with AI audio analysis (BPM, key, loudness, tags) and an organization-wide audio linking pipeline. Per-creator storage linking is also supported.
- **Client Portal**: Org-managed client login system for creators with full catalog management capabilities, including adding/editing songs, contract creation with AI parsing, document uploads, and royalty statement ingestion.
- **Streaming Credits & Intelligence**: Muso.ai-inspired streaming intelligence system with chart data ingestion, ISRC-based track matching, and cross-platform stream estimation.
- **Progressive Web App (PWA)**: Includes a web manifest and service worker for offline caching and push notifications.
- **Universal Document & Item Sharing**: Allows sharing various items via email or directly to other Cadence accounts.
- **Catalog Refactor — Released/Unreleased Model**: Introduces "Unreleased" catalog section and related statuses.
- **Comprehensive Audit Logging**: Organization-scoped audit trail for critical actions, including song edit history.
- **AI Assistant Chat**: Floating chat button providing natural language guidance about the app, powered by OpenAI `gpt-4o-mini`.
- **Production Infrastructure Foundation**: APP_ENV-driven environment separation, `/health` endpoint, hardened CORS, per-request `X-Request-ID` for structured JSON logs, HTTPS enforcement, in-process ring buffer log handler, and global exception handlers.
- **Schedule A Splits Materialization**: Schedule A ingestion (`schedule_a_ingestion.py`) now writes credit-level `pub_share`/`master_share` and creates the matching `Contract` (SPLIT_SHEET) + `ContractAsset` + `RightsSplit` rows via `sync_credit_to_splits`, so Pub %/Master % survive the credit-driven rollup and are visible in both the internal Catalog View and the Client Portal catalog tab. The portal `/api/client-portal/catalog` returns `publishing_percentage`, `master_percentage`, and per-credit `pub_share`/`master_share`. A backfill script (`backend/scripts/backfill_schedule_a_splits_120.py`) materializes splits for songs imported before this fix.
- **Decay Analytics Sees Historical Periods**: Legacy royalty statements uploaded before period auto-parsing shipped had `period_start = NULL`, which made `underwriting_engine.py` fall back to `date.today()` for every line — collapsing all history into a single bucket and preventing decay-curve fits. `parse_period_from_filename` (in `pdf_statement_parser.py`) recognizes the patterns ops staff actually use ("BMI 2023 Jul-Dec", "ASCAP 2024 H1", "Vanguard Q3 2024", bare years) without requiring a period header. The backfill script `backend/scripts/backfill_statement_periods_121.py` walks every NULL-period statement, re-parses the original PDF when `file_path` still resolves on disk, falls back to filename heuristics otherwise, and propagates the recovered period down to `RoyaltyStatementLine.activity_period_start` on lines that were left NULL. Statements that can't be auto-recovered surface a yellow "Period missing — fix" badge in the Royalties statements table that opens the existing edit modal.
- **Royalty Reconciliation Engine (Financial-Institution Grade)**: Reports & Royalties pages share a single source of truth — `royalty_statements.total_revenue_cents` (header) for org-wide totals and `royalty_statement_lines.net_amount` for per-track / per-creator rollups. The legacy `royalty_transactions` table is no longer queried by analytics. Upload flow rejects same-org/same-filename duplicates with HTTP 409 (overridable via `force=true`) and auto-extracts `period_start`/`period_end` from PDF cover pages. `GET /api/royalty-processing/{org_id}/reconciliation` returns per-statement variance (header vs. sum-of-lines vs. ledger vs. pdf_grand_total) with flags `DUPLICATE_FILE`, `ZERO_AMOUNT_LINES`, `LINES_MISSING_AMOUNTS`, `LEDGER_MISSING`, `PROCESSED_WITHOUT_LEDGER`, `PERIOD_MISSING`, `HEADER_VS_LINES_VARIANCE`, `HEADER_VS_LEDGER_VARIANCE`, `UNASSIGNED`, `ZERO_AMOUNT_HEADER`, plus a `generated_at` timestamp and a yellow attention banner on the Reports page that links to Royalties for resolution.

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