# Cadence - Catalog Intelligence - Multi-Tenant Rights & Catalog Administration

## Overview
Cadence is a multi-tenant platform designed for music labels, publishers, production companies, and creators to efficiently manage music catalogs and rights. It provides a comprehensive suite of tools for catalog valuation, rights administration, creator management, and placement tracking. The platform aims to offer actionable insights into catalog performance and value, leveraging an intuitive, Apple Music-inspired user interface.

## User Preferences
### Coding Style
- Python: PEP 8 style, type hints, SQLAlchemy ORM patterns
- JavaScript/React: Functional components, hooks, modern ES6+
- CSS: Tailwind utility classes with gradient themes
- Imports: Absolute imports for backend modules

## System Architecture
Cadence is built on a modern web stack: React 18 with Tailwind CSS for the frontend, and FastAPI with SQLAlchemy and PostgreSQL for the backend.

### UI/UX Decisions
The frontend employs an Apple Music-style aesthetic, featuring a collapsible sidebar, gradient headers, rounded cards, and smooth transitions, all designed for mobile responsiveness. The color palette is a sage-green theme. Key dashboards include a Creator Roster, detailed Creator Profiles, a spreadsheet-style Catalog View with advanced filtering, a Placement Tracking Timeline, comprehensive Reports with Recharts visualizations, and a Catalog Valuation dashboard offering financial insights and branded Excel report downloads.

### Technical Implementations
- **Multi-Tenant Architecture**: Ensures secure data isolation and organization-scoped access control. Includes a tenant-level admin panel for managing team members, branding, and roster delegation.
- **Authentication**: JWT for token-based authentication and bcrypt for password hashing, supporting case-insensitive username login. A Master Admin account provides platform-wide access.
- **Database Schema**: Manages core entities including Organizations, Users, Creators, Songs, Works, Releases, Contracts, Placements, and Royalty-related data.
- **Rights & Contract Tracking**: Supports deal-level contracts with parties, territories, advance tracking, payment direction, and asset-to-contract linking. Per-asset rights splits are validated to 100%.
- **Health Score System**: Dynamically calculates song health based on weighted checklist completion.
- **Catalog Valuation Tool**: Uses a weighted average of Streaming Multiple, Revenue Multiple, Market Comparables, and a Black Box Algorithm.
- **API Security**: Enforces JWT authentication, user-organization membership validation, and organization-scoped queries.
- **AI-Powered CSV Import**: Utilizes OpenAI for intelligent column mapping during bulk song import. Also supports PDF and Word (.docx) Schedule A document parsing, extracting creator info (name, PRO IPI#, ID#), song entries with artist/title/percentage, and Schedule A/B sections.
- **Notification System**: Customizable in-app and email notifications with user and organization-level preferences. Real-time email alerts when `email_enabled` is set for notification types.
- **Action Items System**: Manages proactive action items with deadlines and priorities, with auto-generation based on catalog gaps and cross-module tracking. Supports user assignment with inline dropdowns, "Assigned To" filtering, and scroll-to-top navigation.
- **Placement Management**: Comprehensive sync licensing/placement tracking with a status pipeline from PITCHED to PAID, financial tracking, contract linking, release linking, creator/client filtering, catalog search pickers for works/releases, and automatic accounting integration (creates RoyaltyStatement + RoyaltyTransaction on PAID transition with license fee).
- **Sync Reports**: Customizable sync placement reports filtered by client, status, and date range with PDF/CSV export and branded templates.
- **Cross-Organization Client Sharing**: Secure sharing flow with email-based invitations, 6-digit passcode verification, org name confirmation, and three role levels (COPRIMARY, SECONDARY, READER) with catalog sync.
- **Expense Tracking (Money Out)**: New Expense model with 10 categories (producer fees, day rates, video production, legal, etc.) and status flow (PENDING→APPROVED→PAID/CANCELLED). Integrated into Royalties page as Money Out tab with Expenses and Payments sub-sections.
- **Works Folder Organization**: WorkFolder model with parent_folder_id for nesting, folder bar with counts, inline rename/delete, and move-to-folder functionality on the Works page.
- **Cross-Module Task Auto-Generation**: Automated task creation for contract expirations, release readiness gaps, and placement follow-ups.
- **Core Catalog & Creator Management**: Expanded data models for `Works` (compositions) and `Releases` (albums/EPs) with `work_type` and `IPAssetType` enum for broader IP management.
- **Creative Directory**: A contact management system for industry collaborators with CRUD functionality, searchable UI, role filtering, PDF export, and email sharing of contact cards.
- **Creator Contact Roles**: Multi-contact assignment system for creators via `CreatorContact` association model. Each creator can have multiple contacts with specific roles (DISTRIBUTION, LEGAL, ADMIN, MANAGER, PUBLISHER, A_AND_R, MARKETING, OTHER). Supports primary contact designation per role and auto-discovery for email routing (e.g., auto-find DISTRIBUTION contact when sending release info).
- **Unified Email System**: App-wide email infrastructure powered by Resend via Replit Connector. Branded HTML templates (Cadence sage-green theme) for 7 use cases: (1) Registration Report emails with PDF attachments, (2) Share Contact/Creator Cards, (3) Real-time Notification Alerts, (4) App Invites (welcome/coming-soon), (5) Release Distribution info to contacts, (6) Action Items Push to creators, (7) Email Digests. Reusable `EmailSendModal` component for consistent email UI. Configurable sender with fallback chain.
- **Registration Reports**: Operational PRO registration workflow. Tracks `is_registered_with_pro` flag on Songs and Works. Supports Outstanding/Registered filtering, creator grouping, checkbox selection for aggregating items into reports. Generates branded PDF reports for selected items. Includes direct email-to-admin feature via Resend with PDF attachment, plus CSV and manual PDF download options. Performance-optimized with `OrgLookups` class (bulk pre-fetching creators/contacts/credits in 4 queries instead of N+1). Saved report persistence via `RegistrationReport` model with save/refresh/delete/PDF-download endpoints and cached JSON data snapshots.
- **Spotify Integration**: Integrates with the Spotify API for playlist import, track search, and release metadata lookup (auto-populate release details from Spotify album/track URLs).
- **Cloud Storage Integration**: Multi-provider cloud storage integration supporting Dropbox and Google Drive (Box deferred). OAuth connect/disconnect per org per provider. Links audio files to songs/releases without hosting audio locally. Temporary downloads for AI analysis only. Browseable folder selection UI via reusable FolderPicker component with breadcrumb navigation, navigation stack for Google Drive folder IDs, and path-based navigation for Dropbox. Browse endpoints are async to prevent production streaming errors.
- **AI Audio Analysis**: Background analysis pipeline using OpenAI for generating BPM, key, loudness, mood/texture/sync tags from audio file metadata and song context. Analysis results stored in AudioAnalysis with tag system (AudioTag/AudioAssetTag). Supports single and bulk analysis.
- **Audio Tagging System**: AI-generated tags with confidence scores + user-editable overrides. Tag types: MOOD, TEXTURE, SYNC, GENRE, USER. Tags power catalog filtering and Brief Builder matching.
- **Brief Builder**: Sync brief matching tool that accepts free-text descriptions + structured filters (BPM range, key, moods, textures, vocal presence, stems available). Uses OpenAI for natural language query parsing. Returns ranked song results with match scores and reasons.
- **Catalog Audio Filters**: Toggleable audio columns (Audio Linked, BPM, Key, Mood, Analyzed) and client-side audio filters in the catalog view.
- **Alembic Migrations**: Manages database migrations.
- **Production Server**: Configured with Gunicorn and Uvicorn workers for production deployment.
- **Structured Logging**: JSON-formatted logging with request tracing.
- **Containerization**: Utilizes Docker for multi-stage builds and `docker-compose` for local development.

### Feature Specifications
- **Creator Roster Management**: Visual cards and detailed profiles with DSP links (Spotify, Apple Music, YouTube), social media (Instagram, X/Twitter), bio, and custom named links. Branded roster PDF export with selectable creators.
- **Advanced Catalog View**: Spreadsheet-style with filtering and sortable columns.
- **Song Management**: Manual and AI-powered bulk CSV upload.
- **Placement Tracking**: Comprehensive management page with status pipeline, CRUD operations, and contract linking.
- **Reports & Analytics**: Tabbed analytics dashboard with Recharts visualizations across various modules.
- **Schedule A Export**: CSV generation of creator catalogs.
- **Contract Management**: Secure PDF upload/download, deal-level tracking, assets, rights splits, territory, and advance management.
- **Rights & Splits**: Per-asset rights split management with percentage validation and SPLIT_SHEET contract generation with PDF export.
- **Account Linking**: Secure linking between Individual and Enterprise organizations.
- **Master Admin System**: Super admin role for platform management.
- **Global Search**: Unified search across songs, works, releases, and creators.
- **Bulk Operations**: Bulk update and credit assignment for songs.
- **Notification Center**: In-app notifications with read/unread states and user/org preferences.
- **Scheduled Email Digests**: Automated email notifications for action items with configurable frequency and content.
- **Unified Tasks Inbox**: Upgraded Action Items page serving as a cross-module task inbox with entity-type filtering.
- **Enhanced Home Dashboard**: Displays urgent action items, notifications, placement pipeline summary, and tasks breakdown.
- **Royalty Accounting System**: Financial engine for statement ingestion, asset matching, royalty calculation, advance recoupment, and payment management, supporting multi-currency and PRO statements.
- **Royalty Processing Pipeline**: Professional royalty processing with Processing Inbox, Statement Detail View (6 tabs: Overview/Lines/Matching/Allocation Preview/Run History/Exports), three-tier auto-matching (ISRC/UPC/fuzzy), Matching Console with bulk-confirm, allocation preview with contract splits and advance recoupment, audit-safe reprocessing with REVERSAL entries, Payables management with payout batches, and per-creator Ledger/Recoupment sub-tabs.
- **Fees & Advances Tracking**: Per-creator fee and advance tracking with recoupment progress, integrated into royalty accounting.
- **Release Delivery & Distribution Readiness**: Comprehensive validation checks for release and track metadata, artwork, legal, and credits, with a status workflow and export options (CSV, JSON, PDF).
- **Per-Creator Storage Linking**: Link individual creators to Dropbox/Google Drive folders. AI-powered recursive file scanning with fuzzy filename matching (HIGH/MEDIUM/LOW/NONE confidence levels). Review workflow for approve/reject/reassign scan results. Bulk approve and bulk analyze integration. Scheduled scans via APScheduler (daily/weekly/etc.) with per-link frequency settings.

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
- **openpyxl**: Python library for Excel file handling.
- **OpenAI**: Used for AI-powered CSV column mapping.
- **Alembic**: Database migration tool.
- **Gunicorn**: Production WSGI/ASGI server.
- **Resend**: Email delivery service.
- **APScheduler**: Background task scheduling.
- **Dropbox SDK**: Dropbox API client for Python (OAuth, file browsing, download links).
- **Cryptography**: Token encryption/decryption for OAuth tokens at rest.
- **pywebpush**: Web Push notification library for Python (VAPID-based push to service workers).

### PWA (Progressive Web App)
- **manifest.webmanifest**: App manifest with name, icons, theme color (#5B8A72), display: standalone.
- **sw.js**: Service worker with offline shell caching (cache-first for static assets, network-first for API), push event handler, notification click navigation.
- **Push Notifications**: VAPID-based web push via pywebpush. PushSubscription model stores per-user device subscriptions. Backend endpoints: /api/push/vapid-public-key, /subscribe, /unsubscribe, /send (admin), /test.
- **Install Prompt**: beforeinstallprompt captured in Settings page, shows Install button or "Installed" badge.
- **Service Worker Registration**: Registered in main.jsx on window load.