# Cadence - Catalog Intelligence - Multi-Tenant Rights & Catalog Administration

## Overview
Cadence is a multi-tenant platform designed for music labels, publishers, production companies, and creators to efficiently manage music catalogs and rights. It provides a comprehensive suite of tools for catalog valuation, rights administration, creator management, and placement tracking, offering actionable insights into catalog performance and value. The platform aims to provide an intuitive user interface inspired by Apple Music.

## User Preferences
### Coding Style
- Python: PEP 8 style, type hints, SQLAlchemy ORM patterns
- JavaScript/React: Functional components, hooks, modern ES6+
- CSS: Tailwind utility classes with gradient themes
- Imports: Absolute imports for backend modules

## System Architecture
Cadence is built on a modern web stack: React 18 with Tailwind CSS for the frontend, and FastAPI with SQLAlchemy and PostgreSQL for the backend.

### UI/UX Decisions
The frontend employs an Apple Music-style aesthetic, featuring a collapsible sidebar, gradient headers, rounded cards, and smooth transitions, designed for mobile responsiveness. The color palette is a sage-green theme. Key dashboards include Creator Roster, Creator Profiles, a spreadsheet-style Catalog View, Placement Tracking Timeline, Reports with Recharts visualizations, and a Catalog Valuation dashboard.

### Technical Implementations
- **Multi-Tenant Architecture**: Ensures secure data isolation and organization-scoped access control with a tenant-level admin panel.
- **Authentication**: JWT for token-based authentication and bcrypt for password hashing, supporting case-insensitive username login and a Master Admin account.
- **Database Schema**: Manages core entities including Organizations, Users, Creators, Songs, Works, Releases, Contracts, Placements, and Royalty data.
- **Rights & Contract Tracking**: Supports deal-level contracts with parties, territories, advances, payment direction, and asset-to-contract linking. Per-asset rights splits are validated to 100%.
- **Health Score System**: Dynamically calculates song health based on weighted checklist completion.
- **Catalog Valuation Tool**: Uses a weighted average of Streaming Multiple, Revenue Multiple, Market Comparables, and a Black Box Algorithm. Enhanced with an institutional-grade Underwriting Engine that produces statement-driven valuations with song-by-period revenue spine, exponential decay analytics (k, half-life, R², CAGR, volatility), HHI/Top-N concentration metrics, DCF projections (10yr, 9/11/14% discount rates), and multiplier valuation bands (publishing 10/13/16×, masters 6/9/12×). Powered by a versioned Knowledge Base (`backend/kb/underwriting_kb.json`) with classification rules, territory normalization, and control thresholds. Results stored in `UnderwritingRun` model with full audit trail.
- **API Security**: Enforces JWT authentication, user-organization membership validation, and organization-scoped queries.
- **AI-Powered Data Ingestion**: Utilizes OpenAI for intelligent column mapping during bulk song import (CSV) and for parsing PDF/Word (.docx) Schedule A documents to extract creator and song information.
- **Notification System**: Customizable in-app and email notifications with user and organization-level preferences, including real-time email alerts.
- **Action Items System**: Manages proactive action items with deadlines and priorities, with auto-generation based on catalog gaps and cross-module tracking.
- **Placement Management**: Comprehensive sync licensing/placement tracking with a status pipeline from PITCHED to PAID, financial tracking, and automatic accounting integration upon PAID transition.
- **Sync Reports**: Customizable sync placement reports with PDF/CSV export and branded templates.
- **Cross-Organization Client Sharing**: Secure sharing workflow with email-based invitations, passcode verification, and role-based catalog synchronization. Accepted shares surface shared creators in the recipient's Roster (with "Shared" badge) and their songs in the Catalog page. Shared creators can be viewed in full detail (songs, releases, accounting, streaming credits) using org-scoped API calls with shared-access authorization via `has_shared_access()` helper. The Active Shares tab shows both sent and received active shares. Senders can cancel pending invitations. Notifications sent for all sharing actions (create, accept, reject, revoke, cancel). Statuses: PENDING, ACCEPTED, REJECTED, REVOKED, CANCELLED.
- **Expense Tracking**: An Expense model with categories and a status flow, integrated into the Royalties page.
- **Works Folder Organization**: Supports hierarchical folder organization for Works with nesting, renaming, deletion, and move functionality.
- **Core Catalog & Creator Management**: Expanded data models for `Works` (compositions) and `Releases` (albums/EPs) with `work_type` and `IPAssetType` for broader IP management.
- **Creative Directory**: A contact management system for industry collaborators with CRUD functionality, searching, filtering, and export options.
- **Creator Contact Roles**: Multi-contact assignment system for creators with specific roles and primary contact designation for email routing.
- **Unified Email System**: App-wide email infrastructure powered by Resend with branded HTML templates for various use cases (e.g., Registration Reports, notifications, invites).
- **Registration Reports**: Operational PRO registration workflow for tracking and generating branded PDF reports for songs/works, with direct email and CSV/manual PDF download options.
- **Spotify Integration**: Integrates with the Spotify API for playlist import, track search, and release metadata lookup.
- **Cloud Storage Integration**: Multi-provider cloud storage integration (Dropbox, Google Drive) for linking audio files to songs/releases, with OAuth and a browsable folder selection UI.
- **AI Contract Parsing**: Upload a PDF or DOCX contract document during contract creation, and AI (OpenAI gpt-4o-mini) extracts key terms (title, type, dates, territory, advance amounts, parties, terms summary) to auto-fill the contract form. Parsed document is auto-attached after creation. Service: `backend/services/contract_parser.py`, endpoint: `POST /api/rights/contracts/parse-document`. The Upload Contract Document modal supports both "Attach to existing contract" and "Create new contract from document" modes, with the latter triggering AI parsing and auto-filling a review form before creation.
- **AI Audio Analysis**: Background analysis pipeline using OpenAI for generating BPM, key, loudness, mood/texture/sync tags from audio files.
- **Audio Tagging System**: AI-generated tags with confidence scores and user-editable overrides, powering catalog filtering and Brief Builder.
- **Brief Builder**: Sync brief matching tool that uses OpenAI for natural language query parsing from free-text descriptions and structured filters, returning ranked song results.
- **Royalty Accounting System**: Financial engine for statement ingestion, asset matching, royalty calculation, advance recoupment, and payment management, supporting multi-currency and PRO statements. Supports CSV, Excel (.xlsx/.xls), and PDF file uploads — PDFs use a tiered parsing approach: (1) dedicated text-based publishing statement parser (`backend/utils/pdf_statement_parser.py`) for large multi-page publishing royalty statements (e.g., KOBALT/BMI format with Title/Writer/Source/Income Type/Territory/Amount structure), (2) pdfplumber table extraction, (3) OpenAI AI fallback. The publishing parser handles 500+ page statements with regex-based line parsing for 99.9% revenue accuracy. Includes a professional royalty processing pipeline with matching, allocation preview, audit-safe reprocessing, and payables management. **Client-specific royalties**: Statements are attributed to a creator/client via `creator_id` on `RoyaltyStatement`. The Royalties page shows a client card landing view (`CreatorRoyaltyLanding`) with per-client revenue summaries; clicking a client card navigates into their scoped royalty tabs (Processing, Statements, Earnings, etc.). Upload forms require client selection. API: `GET /api/royalties/creators-summary/{org_id}` returns per-creator aggregated stats.
- **Release Delivery & Distribution Readiness**: Comprehensive validation checks for release and track metadata, artwork, legal, and credits, with a status workflow and export options.
- **Per-Creator Storage Linking**: Links individual creators to Dropbox/Google Drive folders with AI-powered recursive file scanning, fuzzy filename matching, a review workflow, and scheduled scans.
- **Client Portal**: Org-managed client login system for creators with full catalog management capabilities — add/edit songs, import via Schedule A, create contracts with AI parsing, upload documents, and ingest royalty statements. Supports configurable `client_access_scope` (`OWN`/`ALL`) per client user. Grant Company Access uses shareable access codes (8-char alphanumeric, per-org) instead of org name lookup. All client actions are audit-logged.
- **Bulk & Cross-Org Contact Sharing**: Multi-select contact cards for bulk email sharing with PDF attachments, and shareable public links (token-based, expiring) for cross-organization contact card viewing without login. Model: `SharedContactLink`, public page: `/shared/contacts/:token`.
- **Per-Client Contact Sharing**: Admins explicitly share creative directory contacts with client accounts via `ClientSharedContact` model. Client portal Directory tab shows only contacts shared with that client (read-only). Admin UI supports single and bulk sharing via a "Share to Client" action in the multi-select bar.
- **Client Account Merge**: Allows client portal users to merge their client account into an independent Cadence account. Flow: client requests merge with target email → 6-digit verification code sent via Resend → client verifies → Master Admin reviews/approves/rejects. On approval, `OrganizationMember` (CLIENT role) transfers to target user, `Creator.linked_user_id` updates, old account deactivated. Model: `AccountMergeRequest`, routes: `backend/routes/account_merge.py`, UI in Client Portal profile tab and Admin Dashboard merge-requests tab.
- **Editable Credit Roles**: Song credits on Creator Detail pages support inline role editing (Artist, Primary Artist, Featured Artist, Songwriter, Producer, Composer, Lyricist). The Add Song modal includes a Client Role selector. API returns `credit_role` and `credit_id` when listing songs filtered by `creator_id`.
- **Streaming Credits & Intelligence**: Muso.ai-inspired streaming intelligence system with chart data ingestion from 5 platforms (Spotify, YouTube, Apple RSS, Deezer, Last.fm), ISRC-based track matching to catalog songs, and cross-platform stream estimation using market-share ratios. Features a Credits overview page (sidebar), Credits tab on Creator Profiles with role breakdowns and RIAA equivalents, shareable public Credits profiles with optional passcode protection, Client Portal Credits tab, and "Download for Social" PNG export (1080×1350 Instagram-ready branded card via html2canvas, component: `SocialCard.jsx`). Chart ingestion runs on a 4-hour APScheduler interval (runs immediately on startup). Credits only count songs with Spotify import (via `SongDSPLink` platform='SPOTIFY' or `Song.spotify_link`). Stream estimation fallback chain: Analytics.spotify_streams → SongStreamingMetrics.total_streams → Spotify API popularity lookup → chart position data. Models: `ChartSource`, `ChartEntry` (org-agnostic), `StreamEstimate`, `CreatorCreditsProfile` (per-org). Routes: `backend/routes/streaming_credits.py` (3 routers: `router`, `public_router`, `admin_chart_router`). Services: `chart_fetcher.py`, `track_matcher.py`, `stream_estimator.py`, `credits_service.py`, `chart_scheduler.py`. Platform keys: SPOTIFY, APPLE_MUSIC, YOUTUBE_MUSIC, AMAZON_MUSIC, TIDAL, DEEZER.
- **Progressive Web App (PWA)**: Includes a web manifest, service worker for offline caching and push notifications, and an install prompt.

## External Dependencies
- **PostgreSQL**: Primary database.
- **React**: Frontend UI library.
- **FastAPI**: Python backend framework.
- **SQLAlchemy**: Python ORM.
- **Tailwind CSS**: Utility-first CSS framework.
- **Vite**: Frontend build tool.
- **Recharts**: React charting library.
- **Heroicons**: Icon library.
- **html2canvas**: DOM-to-canvas rendering for image export.
- **PyJWT**: JSON Web Token implementation for Python.
- **Bcrypt**: Password hashing library.
- **openpyxl**: Python library for Excel file handling.
- **OpenAI**: Used for AI-powered CSV column mapping and document parsing.
- **Alembic**: Database migration tool.
- **Gunicorn**: Production WSGI/ASGI server.
- **Resend**: Email delivery service.
- **APScheduler**: Background task scheduling.
- **Dropbox SDK**: Dropbox API client for Python.
- **Cryptography**: Token encryption/decryption for OAuth tokens.
- **pywebpush**: Web Push notification library for Python.