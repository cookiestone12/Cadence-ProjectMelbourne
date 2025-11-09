# MIME Catalog Intelligence Platform - Internal Demo

## Project Overview
An **internal demo dashboard** showcasing MIME Publishing's catalog intelligence tool. This demonstrates the capabilities that will be offered to external clients in the future.

**Status**: Internal Demo v1.0 (November 9, 2025)
**Purpose**: Showcase catalog valuation, scoring, and search capabilities

## Architecture

### Tech Stack
- **Frontend**: React 18 + Tailwind CSS + Vite
- **Backend**: FastAPI (Python 3.11)
- **Database**: PostgreSQL (Replit-hosted)
- **Authentication**: JWT (minimal for demo)

### Project Structure
```
/
├── backend/              # FastAPI backend application
│   ├── models/          # Database models (SQLAlchemy)
│   │   ├── models.py   # User, Songwriter, Song, Catalog, Analytics, Settings
│   │   └── __init__.py
│   ├── routes/          # API endpoints
│   │   ├── auth.py     # Registration & login
│   │   ├── catalog.py  # Catalog summary, songs, search
│   │   └── settings.py # API status & configuration
│   ├── services/        # Business logic
│   │   ├── valuation_engine.py  # 3-tier valuations + revenue
│   │   ├── scoring_engine.py    # 4-factor scoring breakdown
│   │   ├── chartmetric.py       # Mock Chartmetric API
│   │   ├── spotify.py           # Mock Spotify API
│   │   └── luminate.py          # Mock Luminate API
│   ├── utils/           # Authentication utilities
│   ├── seed_data.py     # Demo catalog seeding
│   └── main.py          # FastAPI app initialization
├── frontend/            # React frontend application
│   ├── src/
│   │   ├── components/  # Navigation, etc
│   │   ├── pages/       # Home, CatalogView, Search, SongDetail, Login, Upload, Settings
│   │   └── services/    # API client services
│   └── public/          # Static assets (logo, templates)
├── mock_data/           # Mock data for demo
│   ├── demo_catalog.json             # 5-song demo catalog with full metadata
│   ├── external_metrics_tracks.json  # Mock track metrics by song title
│   └── external_metrics_artists.json # Mock artist metrics by artist name
└── uploads/             # Uploaded Schedule A files
```

## Key Features

### Implemented (Internal Demo v1.0)
1. ✅ **Catalog View** - Catalog summary, score breakdown, songs table, integrated upload
2. ✅ **Search View** - Universal search (catalog + external mock data)
3. ✅ **Song Detail** - Comprehensive analytics with valuations, scores, metrics
4. ✅ **3-Tier Valuations** - Low/Base/High scenarios + estimated revenue
5. ✅ **4-Factor Scoring** - Catalog Value, Growth Momentum, Metadata Health, Exploitation Potential
6. ✅ **Mock External Data** - Simulated Chartmetric, Spotify, Luminate responses
7. ✅ **Demo Catalog Seeding** - Auto-populate 5 demo songs on first run
8. ✅ **Catalog Grouping** - Songs organized by catalog with ownership percentages
9. ✅ **File Upload** - Drag-and-drop Schedule A processing (internal demo only)
10. ✅ **MIME Branding** - Purple/orange theme with "Internal Demo" badge

### Future Enhancements
- Separate public website for client Schedule A uploads
- Real-time API integration (when keys provided)
- Advanced trend charts and revenue projections
- Multi-tenant architecture for multiple clients
- Automated reporting and export

## Database Schema

### Tables
- **users**: Authentication (minimal for demo)
- **catalogs**: Catalog metadata (name, client, upload date)
- **songwriters**: Songwriter information (PRO, IPI)
- **songs**: Core song data with ownership percentages
  - New fields: `catalog_id`, `isrc`, `iswc`, `writer_splits` (JSON)
  - New valuations: `valuation_low`, `valuation_base`, `valuation_high`, `estimated_revenue`
  - New scoring: `score`, `score_breakdown` (JSON with 4 factors)
- **analytics**: Performance metrics and data (legacy, may be deprecated)
- **settings**: System configuration key-value pairs

## Core Engines

### Valuation Engine (`services/valuation_engine.py`)

Returns **four metrics** per song:
- **Estimated Revenue**: Annual revenue projection based on streams
- **Low (Conservative)**: Base × 8
- **Base (Realistic)**: Weighted calculation using:
  - Streams (40%)
  - Playlists (30%)
  - Chartmetric score (20%)
  - Regional performance (10%)
- **High (Optimistic)**: Base × 15-18 (varies by growth rate)

### Scoring Engine (`services/scoring_engine.py`)

Returns **breakdown** with four factors (0-25 points each):
1. **Catalog Value** (0-25): Based on total streams and commercial performance
2. **Growth Momentum** (0-25): 3-month and 12-month growth rates
3. **Metadata Health** (0-25): Data completeness (ISRC, ISWC) and quality score
4. **Exploitation Potential** (0-25): Playlist reach and positions

Total score: 0-100 points

## Pages & Routes

### Frontend Pages
- **Home** (`/`) - Landing page with Schedule A template download
- **Catalog View** (`/catalog`) - Main dashboard with catalog summary, score breakdown, and songs table
- **Search** (`/search`) - Search songs by title/artist (catalog + external data)
- **Song Detail** (`/catalog/songs/:id`) - Comprehensive song analytics
- **Upload** (`/upload`) - Standalone upload page (also integrated in Catalog View)
- **Login** (`/login`) - Authentication
- **Settings** (`/settings`) - API configuration (admin only)

### API Endpoints
- `POST /api/auth/register` - Register new user
- `POST /api/auth/login` - Login and get JWT token
- `GET /api/catalog/summary` - Get catalog summaries with totals and breakdowns
- `GET /api/catalog/songs` - Get all songs
- `GET /api/catalog/songs/{id}` - Get song details with full analytics
- `POST /api/catalog/upload` - Upload and parse Schedule A file
- `GET /api/catalog/search?q=query` - Search songs (catalog + external mock data)
- `GET /api/settings/api-status` - Check which APIs are configured vs. mock

## Mock Data Strategy

The demo uses a **fallback architecture**:
1. Load demo catalog on first startup (from `mock_data/demo_catalog.json`)
2. For search queries with no catalog match, return mock "external" data from:
   - `external_metrics_tracks.json` - Track-level metrics (streams, playlists, growth, territories)
   - `external_metrics_artists.json` - Artist-level metrics (monthly listeners, followers, growth, genres)

### Mock Data Files
- **demo_catalog.json** - 5 demo songs with full metadata (songwriter, splits, ISRC/ISWC)
- **external_metrics_tracks.json** - Keyed by song title, contains comprehensive track data
- **external_metrics_artists.json** - Keyed by artist name, contains artist profile data

This simulates the experience of having real Chartmetric/Luminate/Spotify integrations.

## Environment Variables

### Required (Auto-configured by Replit)
- `DATABASE_URL` - PostgreSQL connection
- `SESSION_SECRET` - JWT secret key
- `PGHOST`, `PGPORT`, `PGUSER`, `PGPASSWORD`, `PGDATABASE`

### Optional (For Real API Data)
- `CHARTMETRIC_API_KEY`
- `SPOTIFY_CLIENT_ID`
- `SPOTIFY_CLIENT_SECRET`
- `LUMINATE_API_KEY`

When keys are provided, system automatically switches from mock to real APIs.

## Workflows

Two workflows configured:

1. **backend** (Console, Port 8000)
   - Command: `bash run_backend.sh`
   - Runs FastAPI with uvicorn
   - Seeds demo catalog on first startup

2. **frontend** (Webview, Port 5000)
   - Command: `cd frontend && npm run dev`
   - Runs Vite dev server with proxy to backend
   - Must bind to `0.0.0.0:5000` for Replit

## Recent Changes

### November 9, 2025 - Internal Demo Transformation
**Transformed app from client-facing to internal demo dashboard:**

#### Backend Changes
- Added `Catalog` model to group songs by catalog
- Updated `Song` model with new fields: `catalog_id`, `isrc`, `iswc`, `writer_splits` (JSON)
- Added 3-tier valuation fields: `valuation_low`, `valuation_base`, `valuation_high`, `estimated_revenue`
- Added scoring breakdown: `score_breakdown` (JSON with 4 factors)
- Refactored `valuation_engine.py` to return dict with low/base/high/revenue
- Refactored `scoring_engine.py` to return 4-factor breakdown
- Created `seed_data.py` to auto-populate demo catalog on startup
- Added `/api/catalog/summary` endpoint for catalog aggregations
- Added `/api/catalog/search` endpoint for universal search (catalog + external mock)
- Updated all catalog endpoints to use new valuation/scoring format

#### Frontend Changes
- Renamed `Dashboard` → `Catalog View` with enhanced layout:
  - Catalog summary card (total songs, publishing %, valuations)
  - Score breakdown card (visual breakdown of 4 factors)
  - Integrated upload panel (moved from separate page)
  - Enhanced songs table with new valuation columns
- Created `Search` page for universal search (catalog + external data)
- Updated `SongDetail` page with new format:
  - 3-tier valuations with visual emphasis
  - 4-factor score breakdown with progress bars
  - Writer splits display
  - Growth indicators on metrics
  - ISRC/ISWC codes
- Updated `Navigation` to show Catalog and Search tabs (removed Dashboard/Upload)
- Added "Internal Demo" badge to header

#### Mock Data
- Created comprehensive demo catalog JSON (5 songs, full metadata)
- Created external metrics JSONs for tracks and artists
- Designed for realistic demo experience

#### Documentation
- Updated README to reflect internal demo purpose
- Documented all new features and API endpoints

### November 9, 2025 (Initial) - MVP Implementation
- Created full-stack application with React frontend and FastAPI backend
- Implemented database models and migrations
- Built initial valuation engine with weighted calculation
- Built initial scoring system with commercial potential rating
- Created mock data layer for API fallbacks
- Set up JWT authentication with admin roles
- Designed UI with MIME branding colors
- Configured workflows for automatic deployment

## User Preferences

### Coding Style
- Python: PEP 8 style, type hints where helpful
- JavaScript/React: Functional components, hooks
- CSS: Tailwind utility classes
- Imports: Absolute imports for backend modules

## Known Issues

### Current Status
- No LSP errors
- Both workflows running successfully
- Database seeded correctly on startup

### Expected Behaviors
- First user to register becomes admin automatically
- Database is dropped and recreated when schema changes (requires re-registration)
- React Router future flag warnings in browser console (informational, safe to ignore)

### Limitations
- PDF parsing is basic (structured Excel recommended)
- Mock data is static (will be dynamic with real APIs)
- Single-tenant architecture (no multi-tenancy yet)
- Minimal authentication (for demo purposes)

## Development Notes

### Running Locally
```bash
# Backend
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000

# Frontend (must bind to 0.0.0.0:5000 for Replit)
cd frontend && npm run dev
```

### Database Management
- Schema auto-created on startup via SQLAlchemy's `create_all()`
- Demo catalog auto-seeded on first run (checks for existing data)
- To reset database: Drop tables via SQL tool and restart backend

### Testing the Demo
1. Register a new account (first user becomes admin)
2. View **Catalog** tab to see pre-seeded demo catalog
3. Use **Search** tab to search for songs (searches catalog first, then mock external data)
4. Click any song to view detailed analytics
5. Upload a Schedule A file via upload panel in Catalog View (internal demo feature)

## Deployment Notes

The application is configured for Replit deployment:
- Frontend binds to `0.0.0.0:5000` (required for Replit)
- Backend runs on port 8000 (internal)
- Vite configured with `allowedHosts: true`
- CORS enabled for all origins in development

## Assets

### Templates
- Schedule A template: `frontend/public/MIME_Song_Registration_Template_1762653175934.pdf`

### Branding
- MIME logo: `frontend/public/mime-logo.png`
- Colors: Purple (#8B5CF6), Gold/Orange (#F59E0B), Dark (#1F2937)
- "Internal Demo" badge in navigation header

## Contact

This internal demo was built for MIME Publishing (Made In Memphis Entertainment, LLC).
