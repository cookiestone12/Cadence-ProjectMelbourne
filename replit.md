# Rythm - Catalog Intelligence - Multi-Tenant Rights & Catalog Administration

## Overview
Rythm is a multi-tenant platform designed for music labels, publishers, production companies, and creators to efficiently manage music catalogs and rights. It provides a comprehensive suite of tools for catalog valuation, rights administration, creator management, and placement tracking. The platform aims to offer actionable insights into catalog performance and value, leveraging an intuitive, Apple Music-inspired user interface.

## User Preferences
### Coding Style
- Python: PEP 8 style, type hints, SQLAlchemy ORM patterns
- JavaScript/React: Functional components, hooks, modern ES6+
- CSS: Tailwind utility classes with gradient themes
- Imports: Absolute imports for backend modules

## System Architecture
Rythm is built on a modern web stack: React 18 with Tailwind CSS for the frontend, and FastAPI with SQLAlchemy and PostgreSQL for the backend.

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
- **AI-Powered CSV Import**: Utilizes OpenAI for intelligent column mapping during bulk song import.
- **Notification System**: Customizable in-app and email notifications with user and organization-level preferences.
- **Action Items System**: Manages proactive action items with deadlines and priorities, with auto-generation based on catalog gaps and cross-module tracking.
- **Placement Management**: Comprehensive sync licensing/placement tracking with a status pipeline from PITCHED to PAID, financial tracking, contract linking, release linking, creator/client filtering, catalog search pickers for works/releases, and automatic accounting integration (creates RoyaltyStatement + RoyaltyTransaction on PAID transition with license fee).
- **Cross-Module Task Auto-Generation**: Automated task creation for contract expirations, release readiness gaps, and placement follow-ups.
- **Core Catalog & Creator Management**: Expanded data models for `Works` (compositions) and `Releases` (albums/EPs) with `work_type` and `IPAssetType` enum for broader IP management.
- **Creative Directory**: A contact management system for industry collaborators with CRUD functionality, searchable UI, role filtering, and PDF export.
- **Registration Reports**: Operational PRO registration workflow. Tracks `is_registered_with_pro` flag on Songs and Works. Supports Outstanding/Registered filtering, creator grouping, checkbox selection for aggregating items into reports. Generates branded PDF reports for selected items. Includes direct email-to-admin feature via Resend with PDF attachment, plus CSV and manual PDF download options.
- **Spotify Integration**: Integrates with the Spotify API for playlist import and track search.
- **Alembic Migrations**: Manages database migrations.
- **Production Server**: Configured with Gunicorn and Uvicorn workers for production deployment.
- **Structured Logging**: JSON-formatted logging with request tracing.
- **Containerization**: Utilizes Docker for multi-stage builds and `docker-compose` for local development.

### Feature Specifications
- **Creator Roster Management**: Visual cards and detailed profiles.
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
- **Fees & Advances Tracking**: Per-creator fee and advance tracking with recoupment progress, integrated into royalty accounting.
- **Release Delivery & Distribution Readiness**: Comprehensive validation checks for release and track metadata, artwork, legal, and credits, with a status workflow and export options (CSV, JSON, PDF).

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