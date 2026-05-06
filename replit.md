# Cadence - Catalog Intelligence - Multi-Tenant Rights & Catalog Administration

## Overview
Cadence is a multi-tenant platform designed for music industry professionals to manage music catalogs, rights, and creator relationships. It offers tools for catalog valuation, rights administration, creator management, and placement tracking, aiming to maximize catalog value and streamline operations with an intuitive user interface inspired by Apple Music. The platform provides insights into catalog performance and value, serving as a comprehensive solution for the music industry.

## User Preferences
### Coding Style
- Python: PEP 8 style, type hints, SQLAlchemy ORM patterns
- JavaScript/React: Functional components, hooks, modern ES6+
- CSS: Tailwind utility classes with gradient themes
- Imports: Absolute imports for backend modules

## System Architecture
Cadence utilizes a modern tech stack: React 18 and Tailwind CSS for the frontend, and FastAPI with SQLAlchemy and PostgreSQL for the backend.

### UI/UX Decisions
The frontend features an Apple Music-style aesthetic with a collapsible sidebar, gradient headers, rounded cards, and smooth transitions, primarily using a sage-green color scheme. It's optimized for mobile and includes modular widget dashboards, grid/list view toggles, and Recharts-powered reports. Key dashboards include Creator Roster, Creator Profiles, Catalog View, Placement Tracking Timeline, and Catalog Valuation, which supports multiple methodologies (Income, Market Comparable, DCF, Blended) with historical trends and PDF report generation.

### Technical Implementations
- **Multi-Tenant Architecture**: Ensures data isolation and organization-scoped access.
- **Authentication**: JWT-based with bcrypt for password hashing.
- **Data Models**: Comprehensive schema for various music industry entities.
- **Rights & Contract Tracking**: Manages deal-level contracts and asset rights splits.
- **Multi-Client Song Grouping**: Enables shared song management.
- **Catalog Valuation Tool**: Employs multiple valuation engines and a blended view, providing detailed catalog value insights and underwriting capabilities.
- **AI-Powered Data Ingestion**: Uses OpenAI for CSV mapping, document parsing, and contract term extraction.
- **Notification & Action Items System**: Customizable in-app and email notifications.
- **Placement Management**: Tracks sync licensing placements through a status pipeline.
- **Cross-Organization Client Sharing**: Secure sharing with email invitations and granular permissions.
- **Royalty Accounting System**: Financial engine for statement ingestion, matching, calculation, and payment management, supporting multi-currency.
- **Release Delivery & Distribution Readiness**: Validates release and track metadata.
- **Cloud Storage Integration**: Multi-provider integration (Dropbox, Google Drive) with AI audio analysis.
- **Client Portal**: Organization-managed login for creators with catalog management.
- **Streaming Credits & Intelligence**: Integrates chart data and cross-platform stream estimation.
- **Progressive Web App (PWA)**: Offline caching and push notifications.
- **Universal Document & Item Sharing**: Allows sharing via email or directly within Cadence.
- **Catalog Refactor**: Introduced "Unreleased" catalog sections and statuses.
- **Comprehensive Audit Logging**: Organization-scoped audit trail for critical actions.
- **AI Assistant Chat**: OpenAI-powered chat for guidance, leveraging a rewritten domain knowledge base and tool registry for read/write actions, with user confirmation for mutations. Smart model routing (`gpt-4o` for valuation/audit/calculation, `gpt-4o-mini` otherwise), `temperature=0.3 / top_p=0.9 / MAX_TOOL_ITERATIONS=8`. Org-level `assistant_write_enabled` flag (admin toggle in Settings) gates the proposal write tools — when off, the assistant is read-only. Per-user 20/hr write rate limit (HTTP 429), payload field blocklist, and 8 additional write tools (`mark_song_registered` for MLC + 6 other registries, `add_fee_to_song`, `update_song_status`, `update_creator_pro`, `update_release_status`, `update_release_type`, `update_contract_status`, `update_action_item_status`).
- **Production Infrastructure Foundation**: Environment separation, health endpoints, CORS, request IDs, HTTPS enforcement, and global exception handling.
- **Spotify Integration**: OAuth-based integration for API calls, token management, and playlist imports.
- **Spotify Popularity Cache + Circuit Breaker**: Manages Spotify API calls and caches popularity data.
- **Royalty Reconciliation Engine**: Financial-grade engine for reconciling royalty data.
- **API Versioning**: Backend routes are namespaced under `/api/v1/`.
- **Modular Backend**: `models.py` split into domain-specific modules.
- **Advance Consolidation**: Unified `advances` table with backward compatibility.
- **Royalty Audit Engine**: Four-check audit engine (`CROSS_STATEMENT`, `RATE_CHECK`, `MISSING_PERIOD`, `DECAY_ANOMALY`) with persistence and frontend surfacing.
- **Luminate-Ready Streaming Metrics**: Integration for importing Luminate exports and associating metrics with songs.
- **Per-PRO Song Registration**: Tracks song registrations across various PROs.
- **Performance Sweep**: Added composite indexes and fixed N+1 query issues.
- **Active-Org Pointer & Org Switcher**: Enhanced user experience for multi-organization users with a robust active organization management system and secure switching.
- **Bulk Royalty Upload — Inline Mapping Review & Retry**: Multi-file royalty statement uploads run as a single batch with per-row status (uploading / done / overwritten / needs review / error). Users can fix individual file mappings inline before processing and re-run only the failed rows via a "Retry failed" button without rebuilding the batch or re-uploading successful files.
- **SEO & AI Search Visibility**: `frontend/index.html` carries the canonical title ("Cadence Catalog Intelligence — …"), a deliberately vague meta description, OG/Twitter tags, and two JSON-LD blocks (Organization + SoftwareApplication with Basic/Pro/Enterprise offers). `frontend/public/sitemap.xml` + `robots.txt` + `og-image.png` (1200×630) ship as static assets. Per-route `<SEO>` component (`frontend/src/components/SEO.jsx`) backed by `react-helmet-async` (wired via `HelmetProvider` in `main.jsx`) overrides title/description/canonical on `/about`, `/careers`, `/investors`, `/help`. The keyword-rich, long-form product descriptive copy (six pillar cards + closing keyword paragraph disambiguating Cadence Catalog Intelligence from Cadence Design Systems) lives on a hidden `/what-is-cadence` page (`frontend/src/pages/WhatIsCadencePage.jsx`) — listed in `sitemap.xml` for crawler/AI discovery but **not linked anywhere in nav/footer** so the visible homepage stays minimal.

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