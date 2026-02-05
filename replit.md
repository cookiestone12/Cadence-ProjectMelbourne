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
- **Creator Roster Management**: Visual creator cards with stats and detailed profiles.
- **Advanced Catalog View**: Spreadsheet-style table with robust filtering capabilities.
- **Placement Tracking**: Visual pipeline from offer to payment.
- **Reports & Analytics**: Health distribution charts, placement rates, and actionable insights.
- **Schedule A Export**: CSV generation of creator catalogs.
- **Contract Management**: Secure upload, download, and deletion of PDF contracts linked to songs, with controlled access for linked accounts.
- **Account Linking**: Allows secure linking between Individual and Enterprise organizations with mutual consent and configurable permission levels.
- **Master Admin System**: Super admin role with elevated privileges for platform-wide management, including user activation/deactivation, organization impersonation, and system-wide statistics.

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

**Admin Route:**
- `POST /api/admin/run-reminders`: Trigger automated reminders (super admin only)

**Frontend Components:**
- `NotificationBell`: Bell icon with unread count badge and dropdown
- `Settings` page with Notifications tab for preference management

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