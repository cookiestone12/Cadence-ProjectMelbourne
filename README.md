# Gotcha Catalog Manager

**Multi-Tenant Rights & Catalog Administration Platform** - A comprehensive catalog management system for labels, publishers, production companies, and individual creators, featuring Apple Music-style interface with creator-centric catalog views, health scoring, and rights administration.

## Overview

Gotcha Catalog Manager is a multi-tenant platform that combines sophisticated catalog administration with an intuitive, modern interface. Built for music industry professionals, it provides complete visibility into catalog health, creator performance, placement tracking, and rights management.

### Key Features

- **Multi-Tenant Architecture**: Organization-scoped access control with secure data isolation
- **Apple Music-Style Interface**: Modern, gradient-themed UI with sidebar navigation and responsive design
- **Creator Roster Management**: Visual creator cards with performance metrics and detailed profiles
- **Catalog Health Scoring**: Dynamic checklist-based system with weighted completion tracking
- **Placement Pipeline**: Track songs from offer through payment with visual status indicators
- **Schedule A Export**: Generate comprehensive CSV exports of creator catalog data
- **Reports & Analytics**: Health distribution charts, placement rates, and performance insights
- **Valuation Integration**: Placeholder for Luminate-powered catalog valuation (coming soon)

## Tech Stack

### Frontend
- React 18 with React Router
- Tailwind CSS for styling
- Heroicons for iconography
- Vite for development and building
- Recharts for analytics visualizations
- Axios for API communication

### Backend
- FastAPI (Python 3.11)
- SQLAlchemy ORM with PostgreSQL
- JWT authentication with bcrypt password hashing
- Pydantic for data validation
- CSV export generation

### Database
- PostgreSQL (Replit-hosted)
- Multi-tenant data model with organization isolation
- Models: Organization, OrganizationMember, User, Creator, Song, SongCredit, SongDSPLink, ChecklistItem, SongChecklistStatus, SongValuationSnapshot

## Running the Application

### Automatic Setup (Replit)

The application runs automatically on Replit with:
- Backend on port 8000
- Frontend on port 5000
- Auto-seeded demo organization and data on first run

### Manual Setup

1. **Install Dependencies**

```bash
# Backend
pip install -r backend/requirements.txt

# Frontend
cd frontend && npm install
```

2. **Environment Variables**

Required (automatically set by Replit):
- `DATABASE_URL` - PostgreSQL connection string
- `SESSION_SECRET` - JWT secret key

3. **Initialize Database**

```bash
# Seed the database with demo data
python backend/init_gotcha_db.py
```

4. **Run the Application**

```bash
# Backend
bash run_backend.sh

# Frontend
cd frontend && npm run dev
```

## Demo Credentials

**Username:** `admin`
**Password:** `demo123`
**Email:** `admin@demolabel.com`

Demo organization: **Demo Label Co.** (Record Label)
- 6 creators across various roles
- 35 songs with realistic credits, DSP links, and placement statuses
- Pre-configured checklist items for catalog health tracking

## Using the Application

### Dashboard (Home)

The home page provides an at-a-glance view of your catalog:
- **Quick Stats**: Total songs, active creators, placements, organization type
- **Needs Attention**: Songs with health scores below 50%
- **Top Creators**: Your most productive creators by song count

### Roster

Browse and manage your creator roster:
- **Visual Grid**: Creator cards with hero images and performance metrics
- **Creator Details**: Click any creator to view their complete profile with tabs:
  - **Overview**: Performance stats, recent songs, and creator details
  - **Songs**: Complete catalog with health scores
  - **Placements**: All placements with status tracking
  - **Schedule A**: Export creator catalog to CSV

### Catalog

Comprehensive spreadsheet-style view of your entire catalog:
- **Search**: Real-time search across titles, artists, and projects
- **Filters**: Filter by creator, role (Writer/Producer/Performer), health score, and status
- **Batch View**: See all songs with ISRC, ISWC, release dates, health scores, and status badges
- **Status Indicators**: Visual badges for Paid, PRO Registration, DSP Registration, and Contracts

### Placements

Track your placement pipeline:
- **Stage Progression**: Offer → Contract Sent → Executed → Registered → Paid
- **Progress Bars**: Visual progress indicators for each placement
- **Filterable Table**: Sort and filter placements by status

### Reports

Analyze catalog health and performance:
- **Summary Cards**: Total songs, average health score, placement rate, registered count
- **Health Distribution**: Pie chart showing songs across health categories (Critical, Needs Work, Good, Excellent)
- **Actionable Insights**: Identify areas needing attention

### Valuation

Coming soon placeholder for Luminate-powered catalog valuation:
- Portfolio value estimation
- 30-day revenue projections
- Year-over-year growth tracking

## API Endpoints

### Authentication
- `POST /api/auth/register` - Register new user (creates organization for first user)
- `POST /api/auth/login` - Login and get JWT token

### Organizations
- `GET /api/organizations/current` - Get user's current organization
- `GET /api/organizations/{org_id}` - Get organization details
- `GET /api/organizations/{org_id}/members` - List organization members

### Creators
- `GET /api/creators/org/{org_id}` - List creators for organization
- `GET /api/creators/{creator_id}` - Get creator details with stats
- `POST /api/creators/org/{org_id}` - Create new creator

### Songs / Catalog
- `GET /api/songs/org/{org_id}` - List songs with filters (creator_id, role, min_health, max_health, status)
- `GET /api/songs/{song_id}` - Get song details with credits, DSP links, and checklist
- `POST /api/songs/org/{org_id}` - Create new song
- `PATCH /api/songs/{song_id}` - Update song details

### Credits & DSP Links
- `POST /api/credits/{song_id}` - Add credit to song (validates creator organization)
- `DELETE /api/credits/{credit_id}` - Remove credit
- `POST /api/dsp-links/{song_id}` - Add DSP link
- `DELETE /api/dsp-links/{link_id}` - Remove DSP link

### Checklist & Health Scores
- `GET /api/checklist/checklist-items` - List all checklist items
- `GET /api/checklist/{song_id}/checklist` - Get song checklist status
- `PATCH /api/checklist/{song_id}/checklist` - Update checklist items (auto-calculates health score)

### Schedule A Export
- `GET /api/schedule-a/creator/{creator_id}` - Export creator catalog as CSV

### Valuation (Stub)
- `GET /api/valuations/song/{song_id}` - Get song valuation (placeholder)
- `POST /api/valuations/song/{song_id}` - Create song valuation (placeholder)

## Multi-Tenant Security

All API endpoints enforce organization-scoped access control:
1. **Authentication Required**: All endpoints require valid JWT token
2. **Organization Membership**: Users can only access data for organizations they belong to
3. **Cross-Tenant Isolation**: Creator-song relationships validated at organization level
4. **Role-Based Access**: Admin/Member roles for different permission levels

## Health Score System

The health score (0-100%) is dynamically calculated based on checklist item completion:

**Default Checklist Items:**
- Songwriting splits verified (10%)
- Production credits complete (10%)
- ISRC registered (15%)
- ISWC registered (15%)
- PRO registration complete (20%)
- DSP links added (10%)
- Lyrics uploaded (5%)
- Audio file uploaded (15%)

**Calculation:**
```
health_score = (completed_weight / total_weight) × 100
```

Checklist items can be dynamically added, and the system automatically creates status rows for new songs.

## Branding

- **Primary Gradient**: Purple (#9333EA) to Pink (#EC4899)
- **Gotcha Logo**: Clean text-based logo with gradient
- **Apple Music Aesthetic**: Sidebar navigation, hero headers, rounded cards, smooth transitions

## Future Enhancements

Planned features:
- Song Detail Drawer with comprehensive metadata editing
- Luminate integration for real-time catalog valuation
- Advanced reporting with revenue projections
- Automated placement status tracking
- Bulk import/export functionality
- User permission management

## Support

For questions about Gotcha Catalog Manager, contact your administrator or the development team.

## License

Proprietary © 2025

---

**Gotcha Catalog Manager**
*Modern Catalog Administration for the Music Industry*
