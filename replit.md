# Cadence - Catalog Intelligence - Multi-Tenant Rights & Catalog Administration

## Overview
Cadence is a multi-tenant platform designed for music industry professionals to manage music catalogs, rights, and creator relationships. It provides tools for catalog valuation, rights administration, creator management, and placement tracking, offering insights into catalog performance and value. The platform aims for an intuitive user interface inspired by Apple Music, serving as a comprehensive solution for music professionals.

## User Preferences
### Coding Style
- Python: PEP 8 style, type hints, SQLAlchemy ORM patterns
- JavaScript/React: Functional components, hooks, modern ES6+
- CSS: Tailwind utility classes with gradient themes
- Imports: Absolute imports for backend modules

## System Architecture
Cadence utilizes a modern tech stack with React 18 and Tailwind CSS for the frontend, and FastAPI with SQLAlchemy and PostgreSQL for the backend.

### UI/UX Decisions
The frontend adopts an Apple Music-style aesthetic, featuring a collapsible sidebar, gradient headers, rounded cards, and smooth transitions, optimized for mobile devices. The primary color scheme is sage-green. Key dashboards include Creator Roster, Creator Profiles, Catalog View, Placement Tracking Timeline, Reports with Recharts, and Catalog Valuation.

### Technical Implementations
- **Multi-Tenant Architecture**: Ensures data isolation and organization-scoped access control.
- **Authentication**: JWT-based authentication with bcrypt for password hashing, supporting master admin and case-insensitive username login.
- **Data Models**: Comprehensive schema for Organizations, Users, Creators, Songs, Works, Releases, Contracts, Placements, and Royalty data.
- **Rights & Contract Tracking**: Supports deal-level contracts, asset-to-contract linking, and validates per-asset rights splits to 100%. Song-level Publishing % and Master % are read-only and derived from credit-level splits.
- **Multi-Client Song Grouping**: Facilitates shared song management across multiple clients via a `shared_song_group_id`, enabling linked actions and notifications.
- **Auto-Create Creator**: Automatically creates creator records when new creator names are added via credits.
- **MLC Statement Processing**: Handles MLC statements for multi-client royalty distribution, normalizing split shares.
- **Health Score System**: Dynamically calculates song health based on a weighted checklist.
- **Catalog Valuation Tool**: Employs a weighted average of industry metrics and a proprietary Black Box Algorithm, including an underwriting engine for statement-driven valuations.
- **API Security**: Enforces JWT authentication, user-organization membership, and organization-scoped queries.
- **AI-Powered Data Ingestion**: Utilizes OpenAI for intelligent column mapping in CSV imports and parsing PDF/Word Schedule A documents.
- **Notification System**: Customizable in-app and email notifications with user and organization-level preferences.
- **Action Items System**: Manages proactive, deadline-driven action items, auto-generated based on catalog gaps.
- **Placement Management**: Tracks sync licensing placements through a status pipeline (PITCHED to PAID) with financial and accounting integration.
- **Sync Reports**: Customizable sync placement reports with PDF/CSV export options and branded templates.
- **Cross-Organization Client Sharing**: Secure sharing workflow with email invitations, role-based catalog synchronization, and granular module-level permissions.
- **Expense Tracking**: Integrated Expense model within the Royalties page.
- **Works Approval Workflow**: Manages composition approval with PENDING status, requiring OWNER/ADMIN approval and generating associated action items.
- **Works Folder Organization**: Supports hierarchical folder structures for Works.
- **Core Catalog & Creator Management**: Expanded data models for `Works` and `Releases` with `work_type` and `IPAssetType`.
- **Creative Directory**: Contact management system with private/public visibility, per-user ownership, and Quick Share PRO Info features.
- **Creator Contact Roles**: Allows assigning multiple contacts to creators with specific roles.
- **Unified Email System**: App-wide email infrastructure powered by Resend with branded HTML templates.
- **Bulk Registration**: Operational PRO registration workflow for tracking and generating branded PDF reports with submission history.
- **Roster Deck Configuration**: Pre-export configuration for PDF roster decks, allowing selection of per-creator bio, links, and custom fields.
- **Spotify Integration**: Integrates with Spotify API for playlist import, track search, and release metadata lookup.
- **Cloud Storage Integration**: Multi-provider integration (Dropbox, Google Drive) for linking audio files.
- **AI Contract Parsing**: Uses OpenAI to extract key terms from PDF/DOCX contracts.
- **AI Audio Analysis**: Background analysis pipeline using OpenAI for generating BPM, key, loudness, mood/texture/sync tags from audio files.
- **Audio Tagging System**: AI-generated tags with confidence scores and user-editable overrides.
- **Brief Builder**: Sync brief matching tool using OpenAI for natural language query parsing and structured filtering.
- **Org-Wide Audio Linking Pipeline**: Organization-level Dropbox scan that fuzzy-matches audio files to catalog songs, auto-links high-confidence matches, and queues AI analysis.
- **Royalty Accounting System**: Financial engine for statement ingestion, asset matching, royalty calculation, and payment management, supporting multi-currency and PRO statements.
- **Release Delivery & Distribution Readiness**: Validation checks for release and track metadata, artwork, legal, and credits.
- **Per-Creator Storage Linking**: Links creators to cloud storage folders with AI-powered file scanning and fuzzy matching.
- **Client Portal**: Org-managed client login system for creators with full catalog management capabilities, including adding/editing songs, contract creation with AI parsing, document uploads, and royalty statement ingestion.
- **Bulk & Cross-Org Contact Sharing**: Multi-select contact cards for bulk email sharing and shareable public links.
- **Per-Client Contact Sharing**: Admins can explicitly share creative directory contacts with client accounts.
- **Client Account Merge**: Allows client portal users to merge their client account into an independent Cadence account.
- **Editable Credit Roles**: Inline editing of song credits on Creator Detail pages.
- **Streaming Credits & Intelligence**: Muso.ai-inspired streaming intelligence system with chart data ingestion, ISRC-based track matching, and cross-platform stream estimation, featuring shareable public profiles.
- **Progressive Web App (PWA)**: Includes a web manifest and service worker for offline caching and push notifications.
- **Modular Widget Dashboard**: Home page uses a customizable widget-based architecture.
- **Grid/List View Toggle**: Supports toggling between card grid and table list views on various pages.
- **Universal Document & Item Sharing**: Allows sharing documents, audio files, statements, catalog entries, contacts, and contracts via email or directly to other Cadence accounts, with import functionality for recipients.
- **Catalog Refactor — Released/Unreleased Model**: Introduces "Unreleased" catalog section, `release_status`, `entry_type`, and `parent_song_id` for duplicate tracking. Automated and manual release status management.
- **Duplicate Catalog Entry**: Feature to quickly duplicate songs, linking back to the original.
- **Song Edit History**: Verifiable audit trail for song mutations, tracking field-level changes with user attribution and exportable PDF history.
- **Comprehensive Audit Logging**: Organization-scoped audit trail for critical actions, accessible via Tenant Admin.
- **Infrastructure Cost Tracker**: Master Admin feature for tracking categorized service costs, AI usage, and generating branded PDF cost reports.
- **Support Ticket System**: User-facing support page for submitting tickets with image attachments and annotation tools. Admin interface for managing tickets.
- **AI Assistant Chat**: Floating chat button providing natural language guidance about the app, powered by OpenAI `gpt-4o-mini`, with role-aware responses.
- **Public Website Pages**: Landing page with waitlist/demo forms, Careers page, and Investor Relations page with inquiry forms.
- **Production Infrastructure Foundation**: APP_ENV-driven environment separation (development vs production), `/health` endpoint with real DB connectivity probe, hardened CORS (locks down `*` in production), per-request `X-Request-ID` propagated via ContextVar through structured JSON logs (request_id, user_id, route, duration_ms), HTTPS enforcement via `X-Forwarded-Proto` (fail-closed, /health exempt), in-process ring buffer log handler (last 10k records, accessible via `tail_logs()`) for the upcoming internal logs viewer, and global exception handlers (SQLAlchemyError→503, JWTError→401, generic→500 with traceback hidden in production).

## Source Control
The codebase is mirrored from this Replit workspace to a private GitHub repository. The workspace is the live editor; GitHub is the off-site backup. Day-to-day pushes happen through Replit's built-in **Git** panel — open it, write a short commit message, click **Commit & Push**.

See `CONTRIBUTING.md` for the full plain-language walkthrough, including how to recover the workspace from GitHub if it's ever lost, and the strict rule that **secrets never leave Replit's secret manager**.

`.gitignore` is configured to keep `attached_assets/` (chat-pasted scratch files), `uploads/`, local databases, log files, build output, and most of `.local/` out of source control. Only `.local/tasks/` is intentionally tracked, since it's the project-task history.

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