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