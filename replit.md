# Ampersound Intelligence - Catalog Manager - Multi-Tenant Rights & Catalog Administration

## Overview
Ampersound Intelligence is a multi-tenant platform designed for music labels, publishers, production companies, and individual creators to manage their music catalogs and rights. It offers an Apple Music-inspired user interface, creator-centric views, health scoring for catalog completeness, placement tracking, and robust rights administration. The platform includes a comprehensive catalog valuation tool with multiple methodologies and detailed reporting capabilities, aiming to provide actionable insights into catalog performance and value.

## User Preferences
### Coding Style
- Python: PEP 8 style, type hints, SQLAlchemy ORM patterns
- JavaScript/React: Functional components, hooks, modern ES6+
- CSS: Tailwind utility classes with gradient themes
- Imports: Absolute imports for backend modules

## System Architecture
The platform is built on a modern web stack featuring React 18 with Tailwind CSS for the frontend, and FastAPI with SQLAlchemy and PostgreSQL for the backend.

### UI/UX Decisions
The frontend adopts an Apple Music-style aesthetic, characterized by a collapsible sidebar, gradient headers, rounded cards, and smooth transitions, ensuring mobile responsiveness. Key pages include a dashboard, creator roster, detailed creator profiles, a spreadsheet-style catalog view with advanced filters, a placement tracking timeline, and comprehensive reports with Recharts visualizations. The Catalog Valuation dashboard provides detailed financial insights and download functionality for branded Excel reports.

### Color Palette (Sage-Green Theme)
The app uses a soothing, eye-friendly sage-green color palette optimized for productivity work in light mode:
- **Primary**: #5B8A72 (sage green) - Main actions, active states
- **Secondary**: #7BA594 (light sage) - Secondary elements, gradients
- **Background**: #F5F7F4 (warm off-white) - Page backgrounds
- **Surface**: #FAFBF9 (off-white) - Cards and panels
- **Text Primary**: #3D4A44 (charcoal green) - Headings, important text
- **Text Secondary**: #7A8580 (muted sage) - Supporting text
- **Success**: #5B9A6E (green) - Positive states
- **Info**: #5A8A9A (teal) - Informational elements
- **Warning**: #C4956B (warm amber) - Warnings
- **Error**: #C47068 (muted coral) - Errors

### Technical Implementations
- **Multi-Tenant Architecture**: Ensures secure data isolation and organization-scoped access control.
- **Authentication**: Utilizes JWT for token-based authentication and bcrypt for secure password hashing.
- **Database Schema**: Core models include `Organization`, `User`, `Creator`, `Song`, `SongCredit`, `SongDSPLink`, `ChecklistItem`, `SongChecklistStatus`, `SongStreamingMetrics`, `TerritoryRevenue`, and `ValuationCalculation`. New models like `AccountLink` facilitate consent-based linking between individual and enterprise organizations, and `SongContract` manages PDF contract storage with access control.
- **Health Score System**: Dynamically calculates a song's health based on weighted checklist completion (e.g., ISRC, ISWC, PRO registration, DSP links).
- **Catalog Valuation Tool**: Employs a weighted average of four methodologies (Streaming Multiple, Revenue Multiple, Market Comparables, Black Box Algorithm) considering streaming data, revenue, growth rates, and territory breakdown to provide comprehensive catalog and song valuations. It also generates 30/90/365-day revenue projections.
- **API Security**: All API endpoints enforce JWT authentication, user-organization membership validation, organization-scoped queries, and cross-tenant validation for data integrity.
- **Frontend State Management**: JWT tokens are stored in localStorage, with organization context loaded on mount. API calls are managed via Axios.

### Feature Specifications
- **Creator Roster Management**: Visual creator cards with stats and detailed profiles. Includes manual creator addition with roles, territory, PRO, and IPI fields.
- **Advanced Catalog View**: Spreadsheet-style table with robust filtering capabilities.
- **Manual Song Addition**: Add individual songs to creator catalogs with full metadata fields (title, artist, ISRC, ISWC, release date, label, percentages, advance).
- **CSV Catalog Upload**: Bulk import songs via CSV with AI-powered column mapping that automatically detects and maps headers to standard fields.
- **Placement Tracking**: Visual pipeline from offer to payment.
- **Released Status & Spotify Links**: Mark songs as released directly in catalog view with checkbox. When marking released, prompts for Spotify link via modal. Spotify links open directly to Spotify.
- **Reports & Analytics**: Health distribution charts, placement rates, and actionable insights.
- **Schedule A Export**: CSV generation of creator catalogs.
- **Contract Management**: Secure upload, download, and deletion of PDF contracts linked to songs, with controlled access for linked accounts.
- **Account Linking**: Allows secure linking between Individual and Enterprise organizations with mutual consent and configurable permission levels.
- **Master Admin System**: Super admin role with elevated privileges for platform-wide management, including user activation/deactivation, organization impersonation, and system-wide statistics.

### Catalog Import System
The platform includes an AI-powered CSV import system for bulk catalog management:

**CSV/Excel Upload API Routes (`/api/csv/*`):**
- `POST /preview/{org_id}`: Upload CSV or Excel file and get AI-suggested column mapping with preview rows
- `POST /import/{org_id}`: Import songs with mapping, creator attribution, and auto health scoring

**AI Column Mapping:**
- Uses OpenAI (via Replit AI Integrations) to intelligently map headers to standard fields
- Recognizes flexible naming from any manager format:
  - "Track" / "Song" / "Title" → maps to Song Title
  - "Writer" / "Artist" / "Performer" → maps to Artist Name
  - "%" / "Share" / "Split" / "Pub" → maps to percentages
- Fallback pattern matching when AI is unavailable
- Manual override capability in UI for all mappings

**Supported File Formats:**
- CSV (.csv)
- Excel (.xlsx, .xls) with automatic date conversion to YYYY-MM-DD

**Supported Import Fields:**
- title, primary_artist, isrc, iswc, project_title, release_date
- label, publishing_percentage, master_percentage, advance_amount
- recording_code, notes

**Import Features:**
- Multi-step wizard: Upload → Map Columns → Select Creator → Import
- Assign songs to existing creator or create new creator during import
- Auto-calculate health scores based on field completeness
- Validation for ISRC/ISWC formats and percentage ranges
- Bulk song creation with automatic checklist initialization
- Unmapped fields are left blank (not required)

### Master Admin System
The platform includes a comprehensive master admin system for managing multiple tenant accounts:

**User Model Enhancements:**
- `is_super_admin`: Boolean flag for super admin access
- `is_active`: Boolean flag for account activation status
- `last_login_at`: Timestamp of last login

**Organization Model Enhancements:**
- `display_name`: Custom display name for the organization
- `logo_url`: URL to organization logo
- `logo_orientation`: Logo display format (square, horizontal, vertical)
- `primary_color`: Custom brand color

**Admin API Routes (`/api/admin/*`):**
- `GET /stats`: System-wide statistics (users, organizations, songs, creators)
- `GET/POST /users`: List and create users
- `GET/PUT/DELETE /users/{id}`: Manage individual users
- `GET/POST /organizations`: List and create organizations
- `PUT /organizations/{id}`: Update organization details
- `POST /organizations/{id}/members`: Add members to organizations
- `DELETE /organizations/{id}/members/{user_id}`: Remove members
- `POST /impersonate/{org_id}`: Access any organization for support

**Admin Dashboard Features:**
- Overview tab with system statistics
- Users tab with activation/deactivation, role management
- Organizations tab with branding configuration
- Organization impersonation for support access

**Beta Company Accounts:**
- Art Never Dies Music
- Co5
- Rolling Loud
- Global 7 Ent
- Xansational Music

### Notification System
The platform includes a comprehensive notification system with customizable preferences:

**Database Models:**
- `Notification`: Stores individual notifications with type, title, message, read status
- `NotificationPreference`: User preferences for each notification type (in-app, email, frequency)

**Notification Types:**
- `MISSING_ISRC`: Alert when songs are missing ISRC codes
- `MISSING_ISWC`: Alert when songs are missing ISWC codes
- `CONTRACT_PENDING`: Reminder for pending contract uploads
- `PRO_INCOMPLETE`: Alert for incomplete PRO registrations
- `WEEKLY_HEALTH_SUMMARY`: Weekly catalog health report
- `CUSTOM_DEADLINE`: Reminders for custom-set deadlines
- `SYSTEM_ANNOUNCEMENT`: Platform updates and news
- `CATALOG_UPDATE`: Changes to catalog
- `PLACEMENT_UPDATE`: Placement status changes

**API Routes (`/api/notifications/*`):**
- `GET /`: List notifications (with optional unread_only filter)
- `GET /unread-count`: Get count of unread notifications
- `PUT /{id}/read`: Mark notification as read
- `PUT /read-all`: Mark all notifications as read
- `DELETE /{id}`: Delete notification
- `GET /preferences`: Get user's notification preferences
- `PUT /preferences`: Update notification preference

**Admin Routes:**
- `POST /api/admin/run-reminders`: Trigger automated reminders (super admin only)
- `POST /api/admin/run-action-reminders`: Process action item deadline reminders
- `POST /api/admin/send-org-digest/{org_id}`: Send organization action item digest

**Organization Notification Settings:**
- `GET /api/notifications/org/{org_id}/settings`: Get org-level notification settings
- `PUT /api/notifications/org/{org_id}/settings`: Update org-level notification settings (admin only)

**Frontend Components:**
- `NotificationBell`: Bell icon with unread count badge and dropdown
- `Settings` page with Notifications tab for preference management
- `Settings` page with Organization tab for org admins to configure notification defaults and digest settings

### Action Items System
The platform includes a proactive action item management system with deadline tracking:

**Database Model:**
- `ActionItem`: Tracks action items with priority, deadline, status, and reminders

**API Routes (`/api/actions/*`):**
- `GET /org/{org_id}`: List all action items for organization
- `GET /creator/{creator_id}`: List action items for a specific creator
- `POST /org/{org_id}`: Create new action item
- `PUT /{action_id}`: Update action item (deadline, priority, status)
- `DELETE /{action_id}`: Delete action item
- `POST /{action_id}/complete`: Mark action item as completed
- `GET /summary/org/{org_id}`: Get summary stats (pending, overdue, due this week, high priority)

**Action Item Types:**
- `MISSING_ISRC`: Need to register ISRC
- `MISSING_ISWC`: Need to register ISWC
- `CONTRACT_PENDING`: Contract needs upload
- `PRO_INCOMPLETE`: PRO registration incomplete
- `DSP_REGISTRATION`: DSP registration needed
- `CUSTOM_DEADLINE`: User-defined deadline
- `GENERAL`: General action item

**Priority Levels:**
- 1: High priority (red)
- 2: Medium priority (amber)
- 3: Low priority (green)

**Auto-Generation:**
- `GET /api/actions/gaps/{creator_id}`: Analyze catalog and return list of missing items (ISRC, ISWC, contracts, PRO, DSP)
- `POST /api/actions/generate/{creator_id}`: Create action items from detected gaps (avoids duplicates)

**Frontend Components:**
- `ActionsTab`: Full-featured Actions tab in creator profile with deadline management, priority filtering, inline editing, and "Generate Actions" button that auto-creates tasks based on catalog gaps

### Phase 1: Robust Catalog & Creator Management (Completed Feb 2026)

**New Data Models:**
- `Work`: Musical compositions with title, ISWC, alternative titles, language, genre, lyrics
- `WorkTrack`: Links Works to Songs (tracks/recordings), with is_primary flag
- `WorkCredit`: Credits on works (composer, lyricist, arranger, publisher) with share percentages
- `Release`: Albums, EPs, singles with UPC, catalog number, release date, cover art, copyright info
- `ReleaseTrack`: Links Releases to Songs with track/disc numbers and bonus track flag
- `ContributorType`, `ReleaseType`, `ReleaseStatus` enums

**Creator Model Expansion:**
- Added fields: contributor_type, phone, publisher_name, label_affiliation, bio, website_url, spotify_artist_id, apple_music_id

**New API Routes:**
- `GET/POST /api/works/org/{org_id}`: List and create works
- `GET/PUT/DELETE /api/works/{work_id}`: Manage individual works
- `POST/DELETE /api/works/{work_id}/tracks`: Link/unlink tracks to works
- `POST/DELETE /api/works/{work_id}/credits/{credit_id}`: Add/remove credits on works
- `GET/POST /api/releases/org/{org_id}`: List and create releases
- `GET/PUT/DELETE /api/releases/{release_id}`: Manage individual releases
- `POST/DELETE /api/releases/{release_id}/tracks/{song_id}`: Add/remove tracks from releases
- `PUT /api/releases/{release_id}/tracks/reorder`: Reorder tracks
- `GET /api/releases/{release_id}/health`: Release readiness health check
- `PUT /api/bulk/songs/{org_id}`: Bulk update multiple songs at once
- `POST /api/bulk/songs/{org_id}/credits`: Bulk assign credits to songs
- `GET /api/bulk/search/{org_id}?q=...`: Global search across songs, works, releases, creators
- `POST /api/spotify/playlist/preview/{org_id}`: Preview Spotify playlist import
- `POST /api/spotify/playlist/import/{org_id}`: Import tracks from Spotify playlist
- `POST /api/spotify/search`: Search Spotify tracks

**New Frontend Pages:**
- `WorksPage` (/works): Browse, create, edit works with track linking and credit management
- `ReleasesPage` (/releases): Create releases, manage tracks, view health/readiness scores
- `SearchPage` (/search): Unified global search across all entity types with type filters
- `NewCatalogPage` enhanced: Multi-select + bulk edit, Spotify playlist import

**Spotify Integration:**
- Real Spotify API integration via Replit connectors (with client credentials fallback)
- Playlist import with preview, duplicate detection, and creator assignment
- Track search functionality

**Testing:**
- Unit tests in `backend/tests/test_phase1.py` for models, validation, and business logic

## External Dependencies
- **PostgreSQL**: Primary database.
- **React**: Frontend UI library.
- **FastAPI**: Python backend framework.
- **SQLAlchemy**: Python Object Relational Mapper (ORM).
- **Tailwind CSS**: Utility-first CSS framework for styling.
- **Vite**: Frontend build tool.
- **Recharts**: React charting library for data visualization.
- **Heroicons**: Icon library.
- **PyJWT**: JSON Web Token implementation for Python.
- **Bcrypt**: Password hashing library.
- **openpyxl**: Python library for reading and writing Excel 2010 xlsx/xlsm/xltx/xltm files.