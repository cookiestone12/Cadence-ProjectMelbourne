# Cadence - Catalog Intelligence - Multi-Tenant Rights & Catalog Administration

## Overview
Cadence is a multi-tenant platform for music industry professionals to manage music catalogs, rights, and creator relationships. It provides tools for catalog valuation, rights administration, creator management, and placement tracking, delivering insights into catalog performance and value. The platform aims to provide an intuitive user interface inspired by Apple Music.

## User Preferences
### Coding Style
- Python: PEP 8 style, type hints, SQLAlchemy ORM patterns
- JavaScript/React: Functional components, hooks, modern ES6+
- CSS: Tailwind utility classes with gradient themes
- Imports: Absolute imports for backend modules

## System Architecture
Cadence is built with React 18 and Tailwind CSS for the frontend, and FastAPI with SQLAlchemy and PostgreSQL for the backend.

### UI/UX Decisions
The frontend features an Apple Music-style aesthetic with a collapsible sidebar, gradient headers, rounded cards, and smooth transitions, optimized for mobile. The color palette uses a sage-green theme. Dashboards include Creator Roster, Creator Profiles, Catalog View, Placement Tracking Timeline, Reports with Recharts, and Catalog Valuation.

### Technical Implementations
- **Multi-Tenant Architecture**: Ensures secure data isolation and organization-scoped access control.
- **Authentication**: JWT for token-based authentication and bcrypt for password hashing, supporting Master Admin and case-insensitive username login.
- **Database Schema**: Manages Organizations, Users, Creators, Songs, Works, Releases, Contracts, Placements, and Royalty data.
- **Rights & Contract Tracking**: Supports deal-level contracts with parties, territories, advances, and asset-to-contract linking. Per-asset rights splits are validated to 100%.
- **Health Score System**: Dynamically calculates song health based on weighted checklist completion (10 items, 90 total weight).
- **Catalog Valuation Tool**: Employs a weighted average of Streaming Multiple, Revenue Multiple, Market Comparables, and a Black Box Algorithm. Includes an institutional-grade Underwriting Engine for statement-driven valuations with exponential decay analytics, concentration metrics, DCF projections, and multiplier valuation bands.
- **API Security**: Enforces JWT authentication, user-organization membership, and organization-scoped queries.
- **AI-Powered Data Ingestion**: Uses OpenAI for intelligent column mapping during bulk CSV import and for parsing PDF/Word Schedule A documents.
- **Notification System**: Customizable in-app and email notifications with user and organization-level preferences.
- **Action Items System**: Manages proactive action items with deadlines and priorities, auto-generated based on catalog gaps.
- **Placement Management**: Sync licensing/placement tracking with a status pipeline from PITCHED to PAID, financial tracking, and accounting integration.
- **Sync Reports**: Customizable sync placement reports with PDF/CSV export and branded templates.
- **Cross-Organization Client Sharing**: Secure sharing workflow with email invitations, passcode verification, role-based catalog synchronization, and granular module-level permissions (catalog, contracts, placements, royalties, contacts). Module restrictions enforced server-side via `has_shared_access(required_module=)` and on frontend via tab filtering.
- **Expense Tracking**: An Expense model integrated into the Royalties page.
- **Works Approval Workflow**: New compositions enter as PENDING and require OWNER/ADMIN approval. Auto-generates `WORK_PENDING_APPROVAL` action items on creation; approval marks action items completed. Frontend shows pending/approved badges and an approve button for admins.
- **Works Folder Organization**: Supports hierarchical folder organization for Works.
- **Core Catalog & Creator Management**: Expanded data models for `Works` and `Releases` with `work_type` and `IPAssetType`.
- **Creative Directory**: Contact management system for industry collaborators with private/public visibility toggle, per-user ownership, Quick Share PRO Info (copy-to-clipboard and email), and visibility filtering (All My Contacts, Private Only, Org-Wide).
- **Creator Contact Roles**: Multi-contact assignment system for creators with specific roles.
- **Unified Email System**: App-wide email infrastructure powered by Resend with branded HTML templates.
- **Bulk Registration**: Operational PRO registration workflow for tracking and generating branded PDF reports. Includes submission history tracking (sent_at/sent_to) and a Submission History section on the frontend.
- **Roster Deck Configuration**: Pre-export configuration modal for selecting per-creator bio, social links, DSP links, and folder/custom links to include in the PDF roster deck. Supports bulk toggle-all and per-creator field_overrides sent to backend.
- **Spotify Integration**: Integrates with Spotify API for playlist import, track search, and release metadata lookup.
- **Cloud Storage Integration**: Multi-provider cloud storage integration (Dropbox, Google Drive) for linking audio files.
- **AI Contract Parsing**: Uses OpenAI to extract key terms from PDF/DOCX contracts for auto-filling contract forms.
- **AI Audio Analysis**: Background analysis pipeline using OpenAI for generating BPM, key, loudness, mood/texture/sync tags from audio files.
- **Audio Tagging System**: AI-generated tags with confidence scores and user-editable overrides.
- **Brief Builder**: Sync brief matching tool using OpenAI for natural language query parsing. Includes fallback for unanalyzed songs (scored lower but included in results) and structured filter support.
- **Org-Wide Audio Linking Pipeline**: Org-level Dropbox scan that fuzzy-matches audio files to catalog songs, auto-links high-confidence matches (creating AudioAssets), and queues AI analysis. Coverage dashboard shows linked/analyzed/unlinked song stats.
- **Royalty Accounting System**: Financial engine for statement ingestion, asset matching, royalty calculation, and payment management, supporting multi-currency and PRO statements. Features tiered PDF parsing and a professional royalty processing pipeline. Accounting engine is decoupled from auto-matching: statements can be processed into ledger entries without matched lines (unmatched lines book as org-unallocated revenue); auto-match is optional on upload and available as post-hoc enrichment.
- **Release Delivery & Distribution Readiness**: Validation checks for release and track metadata, artwork, legal, and credits.
- **Per-Creator Storage Linking**: Links creators to cloud storage folders with AI-powered file scanning and fuzzy matching.
- **Client Portal**: Org-managed client login system for creators with full catalog management capabilities, including adding/editing songs, contract creation with AI parsing, document uploads, and royalty statement ingestion. Supports configurable `client_access_scope` and uses shareable access codes.
- **Bulk & Cross-Org Contact Sharing**: Multi-select contact cards for bulk email sharing and shareable public links for cross-organization viewing.
- **Per-Client Contact Sharing**: Admins explicitly share creative directory contacts with client accounts.
- **Client Account Merge**: Allows client portal users to merge their client account into an independent Cadence account via a verification and approval process.
- **Editable Credit Roles**: Song credits on Creator Detail pages support inline role editing.
- **Streaming Credits & Intelligence**: Muso.ai-inspired streaming intelligence system with chart data ingestion from multiple platforms, ISRC-based track matching, and cross-platform stream estimation. Features Credits overview, Credits tab on Creator Profiles, shareable public Credits profiles, and "Download for Social" PNG export.
- **Progressive Web App (PWA)**: Includes a web manifest, service worker for offline caching and push notifications.
- **Modular Widget Dashboard**: Home page uses a widget-based architecture with customizable widgets (Stats, Placement Pipeline, Tasks, etc.) via drag-and-drop.
- **Grid/List View Toggle**: Roster, Creative Directory, and Credits pages support toggling between card grid and table list views.
- **Universal Document & Item Sharing**: Share documents, audio files, statements, catalog entries (songs), contacts, and contracts via email or directly to other Cadence accounts. Recipients can view shared item details (including full contract details with parties, assets, and attached documents), download attached files (documents, statements), and import shared catalog entries or contacts directly into their own organization.
- **Duplicate Catalog Entry**: Quick song duplication feature.
- **Comprehensive Audit Logging**: Organization-scoped audit trail for critical actions, accessible via an Audit Log tab in Tenant Admin.
- **Infrastructure Cost Tracker**: Master Admin "costs" tab with categorized service cost cards (AI, Email, Storage, Music APIs, Infrastructure, Push), AI usage tracking via `AIUsageLog` table (instrumented across 5 OpenAI call sites), and downloadable branded PDF cost report with executive summary, per-service breakdown, and scaling projections.
- **Support Ticket System**: User-facing support page (`/support`) for submitting bug reports, feature requests, and general support tickets with image attachments and canvas annotation tools (circle, arrow, freehand drawing). Admin "support" tab in Master Admin dashboard with filterable ticket table, status workflow (Open/In Progress/Resolved/Closed), and internal admin notes. Backend: `SupportTicket` and `SupportTicketAttachment` models, routes in `backend/routes/support.py` and admin endpoints in `backend/routes/admin.py`.
- **AI Assistant Chat**: Floating chat button (bottom-right) on every authenticated page. Opens a slide-up panel where users can ask natural language questions about the app and receive step-by-step guidance referencing actual page names, sidebar items, and buttons. Powered by OpenAI `gpt-4o-mini` with a comprehensive system prompt mapping all Cadence features. Streams responses via SSE. Usage logged to `AIUsageLog`. Role-aware (Client users get scoped guidance). Backend: `backend/routes/assistant.py`, Frontend: `frontend/src/components/AssistantChat.jsx`.
- **Public Website Pages**: Landing page (`/`) with waitlist signup and demo request forms. Careers page (`/careers`) showcasing the 2026 internship program with 4 roles (Engineering, Design, Marketing, Business Development). Investor Relations page (`/investors`) with inquiry form for potential investors. All public pages share consistent nav/footer with cross-links. Lead types: `WAITLIST`, `DEMO_REQUEST`, `INVESTOR_INQUIRY`. Admin LeadsTab filters all types.

## External Dependencies
- **PostgreSQL**: Primary database.
- **React**: Frontend UI library.
- **FastAPI**: Python backend framework.
- **SQLAlchemy**: Python ORM.
- **Tailwind CSS**: Utility-first CSS framework.
- **Vite**: Frontend build tool.
- **Recharts**: React charting library.
- **Heroicons**: Icon library.
- **@dnd-kit**: Drag-and-drop toolkit for React.
- **html2canvas**: DOM-to-canvas rendering for image export.
- **PyJWT**: JSON Web Token implementation.
- **Bcrypt**: Password hashing library.
- **openpyxl**: Python library for Excel file handling.
- **OpenAI**: AI services for CSV column mapping, document parsing, and audio analysis.
- **Alembic**: Database migration tool.
- **Gunicorn**: Production WSGI/ASGI server.
- **Resend**: Email delivery service.
- **APScheduler**: Background task scheduling.
- **Dropbox SDK**: Dropbox API client.
- **Cryptography**: Token encryption/decryption.
- **pywebpush**: Web Push notification library.
- **ReportLab**: PDF generation for cost reports.