# Ampersound Intelligence - Catalog Manager - Multi-Tenant Rights & Catalog Administration

## Overview
A comprehensive multi-tenant catalog management platform for labels, publishers, production companies, and individual creators. Features an Apple Music-style interface with creator-centric catalog views, health scoring, placement tracking, and rights administration. Built using Python/FastAPI/SQLAlchemy/PostgreSQL stack.

## User Preferences
### Coding Style
- Python: PEP 8 style, type hints, SQLAlchemy ORM patterns
- JavaScript/React: Functional components, hooks, modern ES6+
- CSS: Tailwind utility classes with gradient themes
- Imports: Absolute imports for backend modules

## System Architecture

### Tech Stack
- **Frontend**: React 18, React Router, Tailwind CSS, Vite, Heroicons, Recharts
- **Backend**: FastAPI (Python 3.11), SQLAlchemy ORM, PostgreSQL
- **Authentication**: JWT with bcrypt password hashing
- **Database**: PostgreSQL (Replit-hosted)

### Core Features
- **Multi-Tenant Architecture**: Organization-scoped access control with secure data isolation
- **Apple Music-Style UI**: Collapsible sidebar with hamburger menu, gradient headers, mobile responsive
- **Creator Roster Management**: Visual creator cards with stats, detailed profiles with tabs
- **Health Score System**: Dynamic checklist-based scoring (0-100%) with weighted completion
- **Catalog View**: Spreadsheet-style table with advanced filters (creator, role, health, status)
- **Placement Tracking**: Pipeline visualization (Offer → Contract → Executed → Registered → Paid)
- **Schedule A Export**: CSV generation of creator catalogs
- **Reports & Analytics**: Health distribution charts, placement rates, actionable insights
- **Catalog Valuation Tool**: Comprehensive valuation system with streaming metrics, territory breakdown, multiple methodologies, song detail modals, and Excel report downloads

## Database Schema

### Core Models (backend/models/models.py)
- **Organization**: Multi-tenant root entity (id, name, type, created_at)
- **OrganizationMember**: User-organization relationship with roles
- **User**: Authentication (id, username, email, hashed_password)
- **Creator**: Talent roster (id, name, role, hero_image_url, organization_id)
- **Song**: Catalog entries with ownership, health scores, status flags
- **SongCredit**: Many-to-many creator-song relationships with role and split percentage
- **SongDSPLink**: DSP platform links (Spotify, Apple Music, etc.)
- **ChecklistItem**: System-wide checklist items with weights
- **SongChecklistStatus**: Per-song checklist completion tracking
- **SongStreamingMetrics**: Streaming data (total, ad-supported, premium, interactive, on-demand, programmed, audio, video, sales, ownership %)
- **TerritoryRevenue**: Territory-level revenue breakdown (publishing/master split across US, UK, CA, DE, FR, AU, BR, JP, MX, ES)
- **ValuationCalculation**: Computed valuations using 4 methodologies (streaming multiple, revenue multiple, market comps, black box) with revenue projections, growth rates, risk scores

### Key Fields
- **Song**: isrc, iswc, project_title, release_date, status_health_score, has_paid, has_pro_registration, has_dsp_registration, has_contract, media_url
- **Organization**: type (label, publisher, production_company, individual), account_type (INDIVIDUAL, ENTERPRISE)
- **Creator**: role (Writer, Producer, Performer, Manager, Other), email, linked_user_id

### Account Types & Linking (New)
- **AccountLink**: Links Individual and Enterprise organizations with mutual consent
  - Fields: individual_org_id, enterprise_org_id, status (PENDING/ACTIVE/REVOKED/EXPIRED), permission_level (VIEW/MANAGE/FULL)
  - Requires both individual_consent and enterprise_consent for activation
  - Supports time-limited agreements via expiration_date
  - Account type validation enforced during creation

### Contract Management (New)
- **SongContract**: PDF contract storage attached to songs
  - Fields: song_id, organization_id, file_name, file_path, contract_type, description
  - Supports linked account access (partners can view contracts based on permission_level)
  - Upload/download/delete with authentication
  - Auto-updates song has_contract_executed and has_contract_sent flags

## API Architecture

### Security Pattern
All endpoints enforce multi-tenant isolation:
1. JWT authentication required
2. User-organization membership validation
3. Organization-scoped queries on all resources
4. Cross-tenant validation on relationships (e.g., creator-song credits)

### Key Endpoints

#### Authentication
- `POST /api/auth/register` - Creates user and organization
- `POST /api/auth/login` - Returns JWT token

#### Organizations
- `GET /api/organizations/current` - User's current org
- `GET /api/organizations/{org_id}/members` - List members

#### Creators / Roster
- `GET /api/creators/org/{org_id}` - List creators with stats
- `GET /api/creators/{creator_id}` - Creator details with computed stats
- `POST /api/creators/org/{org_id}` - Create new creator

#### Songs / Catalog
- `GET /api/songs/org/{org_id}` - List songs with filters (creator_id, role, min_health, max_health, status)
- `GET /api/songs/{song_id}` - Song details with credits, DSP links, checklist
- `POST /api/songs/org/{org_id}` - Create song
- `PATCH /api/songs/{song_id}` - Update song

#### Credits & DSP Links
- `POST /api/credits/{song_id}` - Add credit (validates creator org matches song org)
- `DELETE /api/credits/{credit_id}` - Remove credit
- `POST /api/dsp-links/{song_id}` - Add DSP link
- `DELETE /api/dsp-links/{link_id}` - Remove DSP link

#### Checklist & Health
- `GET /api/checklist/checklist-items` - List all checklist items
- `GET /api/checklist/{song_id}/checklist` - Song checklist status
- `PATCH /api/checklist/{song_id}/checklist` - Update checklist (auto-recalculates health score, uses upsert pattern)

#### Export
- `GET /api/schedule-a/creator/{creator_id}` - CSV export of creator catalog

#### Contracts (New)
- `POST /api/contracts/upload/{song_id}` - Upload PDF contract (org members only)
- `GET /api/contracts/song/{song_id}` - List contracts for song (org members + linked accounts)
- `GET /api/contracts/download/{contract_id}` - Download contract PDF (org members + linked accounts)
- `DELETE /api/contracts/{contract_id}` - Delete contract (org members only)

#### Account Links (New)
- `POST /api/account-links/request` - Create link request between Individual and Enterprise orgs
- `POST /api/account-links/{id}/consent` - Give consent for pending link
- `POST /api/account-links/{id}/revoke` - Revoke active link
- `GET /api/account-links/organization/{org_id}` - List all links for org
- `GET /api/account-links/active/{org_id}` - List active links (auto-expires stale links)
- `PUT /api/account-links/{id}` - Update link settings

#### Valuation Reports
- `GET /api/valuation/catalog/summary` - Full catalog summary with stats, top songs, territory breakdown
- `GET /api/valuation/song/{song_id}/detail` - Detailed song valuation with streaming metrics, territories, credits
- `GET /api/valuation/catalog/download/excel` - Downloadable Excel report with Ampersand Intelligence branding

## Frontend Architecture

### Navigation Structure
- **Sidebar**: Home, Roster, Catalog, Placements, Reports, Valuation
- **Mobile Responsive**: Collapsible sidebar with hamburger menu for full-screen content viewing
- **Apple Music Aesthetic**: Gradient headers, rounded cards, smooth transitions

### Page Components
1. **HomePage**: Dashboard with stats, needs attention, top creators
2. **RosterPage**: Creator grid with search
3. **CreatorDetailPage**: Hero header with tabs (Overview, Songs, Placements, Schedule A)
4. **CatalogPage**: Spreadsheet table with search and filters
5. **PlacementsPage**: Timeline with progress bars
6. **ReportsPage**: Health analytics with Recharts visualizations
7. **ValuationPage**: Catalog valuation dashboard with:
   - Stats cards (total catalog value, annual revenue, 30-day revenue, avg growth rate)
   - Top valued songs table with streaming metrics and calculated valuations
   - Territory breakdown table showing global revenue distribution
   - Song detail modal with valuation methodology breakdown and streaming analytics
   - Download branded Excel reports
   - Graceful empty states when no data exists

### State Management
- JWT token in localStorage
- Organization context loaded on mount
- API calls via Axios with bearer token
- React Router for client-side routing

## Health Score Calculation

**Formula:**
```
health_score = (sum of completed item weights / total weight) × 100
```

**Default Checklist Items:**
- Songwriting splits verified (10%)
- Production credits complete (10%)
- ISRC registered (15%)
- ISWC registered (15%)
- PRO registration complete (20%)
- DSP links added (10%)
- Lyrics uploaded (5%)
- Audio file uploaded (15%)

**Upsert Pattern:** When checklist items are dynamically added, the system creates missing SongChecklistStatus rows automatically.

## Valuation Calculation Methodology

**Valuation Formula:** Weighted average of 4 methodologies (25% each)

### 1. Streaming Multiple Method
- Formula: `Total Streams × Avg Revenue Per Stream × Ownership % × Multiple (18-28x)`
- Multiple varies based on growth rate and health score
- Higher growth and health = higher multiple

### 2. Revenue Multiple Method  
- Formula: `Annual Revenue × Multiple (8-15x) × Ownership %`
- Multiple adjusts based on growth trajectory
- Fast-growing catalogs receive higher multiples

### 3. Market Comparables Method
- Base valuation with ±15% variance
- Considers market trends and comparable song performance
- Weighted average across comparable transactions

### 4. Black Box Algorithm
- Proprietary formula considering:
  - Health score (metadata completeness)
  - Recency (days since release)
  - Growth rate
  - Total streams and revenue
  - Ownership percentage
- Outputs valuation and risk score (0-100)

**Revenue Projections:**
- 30-day, 90-day, 365-day forecasts
- Based on historical growth rates
- Territory-specific revenue attribution

**Territory Breakdown:**
- 10 territories tracked: US, UK, CA, DE, FR, AU, BR, JP, MX, ES
- Split between Publishing and Master revenue streams
- Realistic distribution (US typically 40-65% of total)

## Demo Data

### Seed Scripts
**backend/init_gotcha_db.py** - Basic catalog data:
- **Organization**: Demo Label Co. (Record Label)
- **User**: admin / demo123 (admin@demolabel.com)
- **Creators**: 6 creators (mix of Writers, Producers, Performers)
- **Songs**: 35 songs with varied:
  - Release dates (2019-2025)
  - Health scores (0-100%)
  - Status flags (Paid, PRO Registered, DSP Registered, Contracts)
  - Credits with splits
  - DSP links
  - Placement statuses

**backend/seed_valuation_data.py** - Valuation data for demo catalog:
- **Streaming Metrics**: 50K - 10M streams per song across platforms
- **Territory Data**: 10 territories per song with realistic US dominance
- **Ownership**: Varied percentages (100%, 50%, 33.3%, 25%, 12.5%)
- **Valuations**: Range from hundreds of thousands to millions per song
- **Growth Rates**: -5% to +35% reflecting market dynamics
- **Total Demo Catalog Value**: $92,648,317.65
- **Total Annual Revenue**: $5,796,552.12

**backend/seed_jack_lomastro.py** - Jack Lomastro placement data:
- **Creator**: Jack Lomastro (Producer, Songwriter)
- **Placements**: 142 songs (52 released, 90 pipeline)
- **Paid Placements**: 27 ($71,177.49 total advances)
- **Status Distribution**: 43 contracted, 32 PRO registered, 48 DSP registered

### Schedule A Export System
- **Data Endpoint**: `/api/schedule-a/creator/{id}/data` - JSON with Released/Pipeline sections
- **PDF Export**: `/api/schedule-a/creator/{id}/pdf` - Branded reportlab PDF with summary stats
- **CSV Export**: `/api/schedule-a/creator/{id}/csv` - Industry-standard CSV with headers first
- **Status Logic**: Derived from placement fields (Paid → Contracted → Contract Sent → In Pipeline)
- **Publishing Percentages**: Capped at 100%, normalized to 2 decimal places

## Development Configuration

### Workflows
- **Backend**: `bash run_backend.sh` → uvicorn on port 8000
- **Frontend**: `cd frontend && npm run dev` → Vite on port 5000

### Environment Variables
- `DATABASE_URL` - PostgreSQL connection (auto-set by Replit)
- `SESSION_SECRET` - JWT secret key (auto-set by Replit)

## Deployment Configuration

### Future Production Setup
- **Build**: `cd frontend && npm run build` → static files in `frontend/dist/`
- **Run**: `python -m uvicorn backend.main:app --host 0.0.0.0 --port 5000`
- **Deployment Type**: Autoscale (cost-effective, runs only when accessed)
- **Static Serving**: Backend serves frontend build files with SPA routing fallback

## Security Highlights

1. **Multi-Tenant Isolation**: All queries scoped to user's organization
2. **Cross-Tenant Validation**: Creator-song relationships validated at org level
3. **Password Hashing**: bcrypt with automatic salt generation
4. **JWT Authentication**: Secure token-based sessions
5. **SQL Injection Prevention**: SQLAlchemy ORM with parameterized queries

## Future Enhancements

- Song Detail Drawer with inline editing
- Real-time streaming API integration for live valuation updates
- Bulk import/export for catalog management (CSV, Excel)
- User permission management (admin vs. member roles)
- Automated placement status tracking via webhooks
- Time-series valuation tracking (historical trend charts)
- Automated valuation report scheduling and email delivery
- Custom valuation methodology configuration per organization

## Branding

- **Color Scheme**: Purple (#9333EA) to Pink (#EC4899) gradient
- **Typography**: Sans-serif, clean and modern
- **Logo**: Text-based "Ampersound Intelligence" with gradient effect
- **Aesthetic**: Apple Music-inspired design language

## External Dependencies

- **PostgreSQL**: Primary database
- **React**: Frontend library
- **FastAPI**: Backend framework
- **SQLAlchemy**: Python ORM
- **Tailwind CSS**: Utility-first CSS framework
- **Vite**: Frontend build tool
- **Recharts**: React charting library
- **Heroicons**: Icon library
- **JWT**: Authentication tokens
- **bcrypt**: Password hashing
- **openpyxl**: Excel report generation (Python)
