# Ampersound Intelligence - Catalog Manager - Multi-Tenant Rights & Catalog Administration

## Overview
Ampersound Intelligence is a multi-tenant platform for music labels, publishers, production companies, and creators to manage music catalogs and rights. It features an Apple Music-inspired UI, creator-centric views, health scoring, placement tracking, and robust rights administration. The platform includes a comprehensive catalog valuation tool with multiple methodologies and detailed reporting, providing actionable insights into catalog performance and value.

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
- **Multi-Tenant Architecture**: Ensures secure data isolation and organization-scoped access control.
- **Authentication**: JWT for token-based authentication and bcrypt for password hashing.
- **Database Schema**: Core models manage `Organization`, `User`, `Creator`, `Song`, `SongCredit`, `SongDSPLink`, `ChecklistItem`, `SongChecklistStatus`, `SongStreamingMetrics`, `TerritoryRevenue`, `ValuationCalculation`, `AccountLink`, `SongContract`, `Notification`, `NotificationPreference`, `ActionItem`, `Work`, `WorkTrack`, `WorkCredit`, `Release`, `ReleaseTrack`, `Contract`, `ContractParty`, `ContractAsset`, and `RightsSplit`.
- **Rights & Contract Tracking**: Deal-level contracts with parties, territory, advance tracking. Asset-to-contract linking (songs and works). Per-asset rights splits with percentage validation (max 100% per rights type). Query rights by asset or by rights holder.
- **Health Score System**: Dynamically calculates song health based on weighted checklist completion.
- **Catalog Valuation Tool**: Employs a weighted average of four methodologies (Streaming Multiple, Revenue Multiple, Market Comparables, Black Box Algorithm) considering streaming data, revenue, growth rates, and territory breakdown.
- **API Security**: Enforces JWT authentication, user-organization membership validation, organization-scoped queries, and cross-tenant validation.
- **Frontend State Management**: JWT tokens stored in localStorage, with organization context loaded on mount. API calls via Axios.
- **AI-Powered CSV Import**: Intelligent column mapping using OpenAI (via Replit AI Integrations) for bulk song import, with fallback pattern matching and manual override.
- **Notification System**: Customizable in-app and email notifications for various event types, with user and organization-level preferences.
- **Action Items System**: Proactive management of action items with deadlines, priorities, reminders, and auto-generation based on catalog gaps.
- **Core Catalog & Creator Management**: Expanded data models for `Works` (compositions), `Releases` (albums/EPs), and `Creator` profiles.
- **Spotify Integration**: Real Spotify API integration for playlist import (with preview and duplicate detection) and track search functionality.

### Feature Specifications
- **Creator Roster Management**: Visual cards with stats and detailed profiles, supporting manual addition.
- **Advanced Catalog View**: Spreadsheet-style with robust filtering.
- **Song Management**: Manual and bulk CSV upload (with AI mapping) of songs with full metadata.
- **Placement Tracking**: Visual pipeline from offer to payment.
- **Released Status & Spotify Links**: Mark songs as released and prompt for Spotify links.
- **Reports & Analytics**: Health distribution charts, placement rates, and insights.
- **Schedule A Export**: CSV generation of creator catalogs.
- **Contract Management**: Secure PDF upload, download, and deletion linked to songs with access control. Full deal-level contract tracking with parties, assets, rights splits, territory, and advance management via Contracts page.
- **Rights & Splits**: Per-asset rights splits with percentage validation. Rights query by asset or rights holder. Rights & Splits tab in song detail modal and works detail panel.
- **Account Linking**: Secure linking between Individual and Enterprise organizations with mutual consent.
- **Master Admin System**: Super admin role for platform-wide management (user/organization management, impersonation, system statistics).
- **Global Search**: Unified search across songs, works, releases, and creators.
- **Bulk Operations**: Bulk update songs and assign credits.
- **Notification Center**: In-app notification bell with unread count badge, dropdown panel with read/unread states, mark-all-read, and per-notification delete. User and org-level notification preferences in Settings.
- **Action Items Dashboard**: Standalone org-wide Action Items page with summary cards (pending, overdue, due this week, high priority), filterable/sortable list, inline creation form, complete/delete actions, and org-wide auto-generation from catalog gaps.
- **Enhanced Home Dashboard**: Homepage shows urgent action items widget, recent notifications summary, action item summary cards with overdue/priority badges, alongside existing needs-attention songs and top creators.

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