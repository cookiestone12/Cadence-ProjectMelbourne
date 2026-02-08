# Rythm - Catalog Manager - Multi-Tenant Rights & Catalog Administration

## Overview
Rythm is a multi-tenant platform for music labels, publishers, production companies, and creators to manage music catalogs and rights. It features an Apple Music-inspired UI, creator-centric views, health scoring, placement tracking, and robust rights administration. The platform includes a comprehensive catalog valuation tool with multiple methodologies and detailed reporting, providing actionable insights into catalog performance and value.

## User Preferences
### Coding Style
- Python: PEP 8 style, type hints, SQLAlchemy ORM patterns
- JavaScript/React: Functional components, hooks, modern ES6+
- CSS: Tailwind utility classes with gradient themes
- Imports: Absolute imports for backend modules

## System Architecture
The platform utilizes a modern web stack: React 18 with Tailwind CSS for the frontend, and FastAPI with SQLAlchemy and PostgreSQL for the backend.

### UI/UX Decisions
The frontend features an Apple Music-style aesthetic with a collapsible sidebar, gradient headers, rounded cards, and smooth transitions, ensuring mobile responsiveness. Key pages include a dashboard, creator roster, detailed creator profiles, a spreadsheet-style catalog view with advanced filters, a placement tracking timeline, and comprehensive reports with Recharts visualizations. A Catalog Valuation dashboard provides financial insights and branded Excel report downloads. The color palette is a sage-green theme optimized for productivity in light mode.

### Technical Implementations
- **Multi-Tenant Architecture**: Ensures secure data isolation and organization-scoped access control. Tenant-level admin panel (`/org-admin`) for OWNER/ADMIN role users to manage team members, reset passwords, assign clients/creators to users, and customize organization branding (logo, display name, primary color).
- **Authentication**: JWT for token-based authentication and bcrypt for password hashing.
- **Database Schema**: Core models manage `Organization`, `User`, `Creator`, `Song`, `SongCredit`, `SongDSPLink`, `ChecklistItem`, `SongChecklistStatus`, `SongStreamingMetrics`, `TerritoryRevenue`, `ValuationCalculation`, `AccountLink`, `SongContract`, `Notification`, `NotificationPreference`, `ActionItem`, `Work`, `WorkTrack`, `WorkCredit`, `Release`, `ReleaseTrack`, `Contract`, `ContractParty`, `ContractAsset`, `RightsSplit`, `RoyaltyStatement`, `RoyaltyTransaction`, `RoyaltyAllocation`, `Payment`, and `Placement`.
- **Rights & Contract Tracking**: Deal-level contracts with parties, territory, advance tracking. Asset-to-contract linking (songs and works). Per-asset rights splits with percentage validation (max 100% per rights type). Query rights by asset or by rights holder.
- **Health Score System**: Dynamically calculates song health based on weighted checklist completion.
- **Catalog Valuation Tool**: Employs a weighted average of four methodologies (Streaming Multiple, Revenue Multiple, Market Comparables, Black Box Algorithm) considering streaming data, revenue, growth rates, and territory breakdown.
- **API Security**: Enforces JWT authentication, user-organization membership validation, organization-scoped queries, and cross-tenant validation.
- **Frontend State Management**: JWT tokens stored in localStorage, with organization context loaded on mount. API calls via Axios.
- **AI-Powered CSV Import**: Intelligent column mapping using OpenAI (via Replit AI Integrations) for bulk song import, with fallback pattern matching and manual override.
- **Notification System**: Customizable in-app and email notifications for various event types, with user and organization-level preferences.
- **Action Items System**: Proactive management of action items with deadlines, priorities, reminders, and auto-generation based on catalog gaps. Extended with cross-module fields (work_id, release_id, contract_id, placement_id, entity_type, entity_label) for unified task tracking across all platform modules.
- **Placement Management**: Full sync licensing/placement tracking with status pipeline (PITCHED→IN_REVIEW→IN_NEGOTIATION→SECURED→DELIVERED→AIRED→PAID), financial tracking (license fees, currency), client/project info, and contract linking. Summary endpoint with pipeline value and status counts.
- **Cross-Module Task Auto-Generation**: Automated task creation for contract expirations (30-day alerts), release readiness gaps, unmatched royalty transactions, placement follow-ups (14+ days since pitch), and placements needing contracts.
- **Core Catalog & Creator Management**: Expanded data models for `Works` (compositions), `Releases` (albums/EPs), and `Creator` profiles.
- **Spotify Integration**: Real Spotify API integration for playlist import (with preview and duplicate detection) and track search functionality.
- **Cross-IP Flexibility**: `IPAssetType` enum (TRACK, VIDEO, PODCAST, AUDIOBOOK, OTHER) with `asset_type` field on Song, Work, and Release models. Default "TRACK" ensures backward compatibility while enabling future expansion to non-music IP domains.
- **Alembic Migrations**: Database migration management via Alembic with autogenerated initial schema migration. Config in `alembic/env.py` connects to project's SQLAlchemy models.
- **Production Server**: Gunicorn config (`backend/gunicorn_config.py`) with Uvicorn workers, environment-aware CORS via `CORS_ORIGINS`, and `run_production.sh` for production startup.
- **Structured Logging**: JSON-formatted logging via `backend/utils/logging_config.py` with request tracing middleware (request_id, duration). Configurable via `LOG_FORMAT` (text/json) and `LOG_LEVEL` env vars.
- **Containerization**: Multi-stage `Dockerfile` (Node frontend build + Python production), `docker-compose.yml` with PostgreSQL, `.dockerignore` for clean builds.

### Feature Specifications
- **Creator Roster Management**: Visual cards with stats and detailed profiles, supporting manual addition.
- **Advanced Catalog View**: Spreadsheet-style with robust filtering.
- **Song Management**: Manual and bulk CSV upload (with AI mapping) of songs with full metadata.
- **Placement Tracking**: Full placement management page with summary cards (total, pipeline value, paid, active pitches), status filters, detail panel with status transitions, CRUD operations, and contract linking. Visual pipeline from PITCHED through to PAID.
- **Released Status & Spotify Links**: Mark songs as released and prompt for Spotify links.
- **Reports & Analytics**: Comprehensive tabbed analytics dashboard (Overview, Catalog Health, Revenue, Creators, Placements, Rights Coverage) with Recharts visualizations including area charts, pie charts, bar charts, line charts, funnel views, coverage progress bars, top earners tables, and gap analysis. Backend analytics API aggregates data across all modules.
- **Schedule A Export**: CSV generation of creator catalogs.
- **Contract Management**: Secure PDF upload, download, and deletion linked to songs with access control. Full deal-level contract tracking with parties, assets, rights splits, territory, and advance management via Contracts page.
- **Rights & Splits**: Per-asset rights splits with percentage validation. Rights query by asset or rights holder. Rights & Splits tab in song detail modal and works detail panel.
- **Account Linking**: Secure linking between Individual and Enterprise organizations with mutual consent.
- **Master Admin System**: Super admin role for platform-wide management (user/organization management, impersonation, system statistics).
- **Global Search**: Unified search across songs, works, releases, and creators.
- **Bulk Operations**: Bulk update songs and assign credits.
- **Notification Center**: In-app notification bell with unread count badge, dropdown panel with read/unread states, mark-all-read, and per-notification delete. User and org-level notification preferences in Settings.
- **Unified Tasks Inbox**: Upgraded Action Items page serving as cross-module task inbox with entity-type filtering (songs, works, releases, contracts, placements, royalties), clickable entity links navigating to related pages, module breakdown widgets, and cross-module task auto-generation.
- **Enhanced Home Dashboard**: Homepage shows urgent action items widget, recent notifications summary, action item summary cards with overdue/priority badges, placement pipeline summary (total, pipeline value, paid, active pitches), tasks-by-module breakdown, alongside existing needs-attention songs and top creators.
- **Royalty Accounting System**: Full financial engine with statement ingestion (CSV/Excel upload), asset matching (ISRC/title/artist fuzzy matching), royalty calculation engine applying contract splits, advance recoupment tracking, per-holder allocations, and payment management. Dashboard with revenue charts, top earning tracks, recoupment progress bars, and earnings breakdowns by rights holder, contract, and track. Supports multi-currency with exchange rate conversion.
- **Release Delivery & Distribution Readiness**: Comprehensive distribution readiness validation with categorized checks (identifiers, metadata, artwork, legal, credits) at both release and track levels. Status workflow with validation gates (Draft → Ready → Submitted → Released; submission requires full readiness). CSV and JSON metadata export for distribution packages. Release Builder UI with readiness score, categorized checklist, export buttons, and status transition controls.

## External Dependencies
- **PostgreSQL**: Primary database.
- **React**: Frontend UI library.
- **FastAPI**: Python backend framework.
- **SQLAlchemy**: Python ORM.
- **Tailwind CSS**: Utility-first CSS framework.
- **Vite**: Frontend build tool.
- **Recharts**: React charting library.
- **Heroicons**: Icon library.
- **PyJWT**: JSON Web Token implementation for Python.
- **Bcrypt**: Password hashing library.
- **openpyxl**: Python library for reading and writing Excel files.
- **OpenAI**: Used for AI-powered CSV column mapping.
- **Alembic**: Database migration tool for SQLAlchemy.
- **Gunicorn**: Production WSGI/ASGI server with Uvicorn workers.

## User Guide
- **User Guide Page**: Accessible at `/guide` without authentication, covering all 17 sections of the platform with table of contents, feature documentation, step-by-step instructions, tips, and glossary.
- **PDF Export**: "Save as PDF" button triggers browser print dialog with print-optimized CSS for clean A4 PDF output.
- **Updateable**: Guide content lives in `frontend/src/pages/UserGuidePage.jsx` — update VERSION and LAST_UPDATED constants at the top of the file when making changes.