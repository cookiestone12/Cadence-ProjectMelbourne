# MIME Catalog Intelligence - Internal Demo Dashboard

**Private Internal Demo Only** - A comprehensive music catalog intelligence platform demonstrating MIME Publishing's automated song valuation, performance scoring, and analytics capabilities.

## Overview

This is an **internal demo dashboard** showcasing the catalog intelligence tool that will eventually be offered to external clients. This demo simulates the workflow after a client uploads their completed Schedule A (using our standard template) through what will be a separate public website.

### Key Features

- **Catalog View**: Comprehensive overview of your catalog with summary metrics, grading breakdowns, and detailed song listings
- **Search View**: Search for songs by title or artist name, displaying valuations and metrics for both catalog and external songs
- **Integrated Upload**: Upload filled Schedule A templates directly within the dashboard for demo purposes
- **Advanced Valuations**: Low/Base/High valuation ranges plus estimated revenue projections
- **Score Breakdown**: Four-factor scoring system (Catalog Value, Growth Momentum, Metadata Health, Exploitation Potential)
- **Mock External Data**: Simulates Chartmetric, Luminate, and Spotify API responses until real keys are provided

## Tech Stack

### Frontend
- React 18 with React Router
- Tailwind CSS for styling
- Vite for development and building
- React Dropzone for file uploads
- Axios for API communication

### Backend
- FastAPI (Python 3.11)
- PostgreSQL database via SQLAlchemy ORM
- JWT authentication (minimal - single admin user)
- Mock data system with automatic API switching

### Database
- PostgreSQL (Replit-hosted)
- Models: Users, Songwriters, Songs, Catalogs, Analytics, Settings

## Running the Demo

### Automatic Setup (Replit)

The demo runs automatically on Replit with:
- Backend on port 8000
- Frontend on port 5000
- Auto-seeded demo catalog on first run

### Manual Setup

1. **Install Dependencies**

```bash
# Backend
cd backend && pip install -r requirements.txt

# Frontend
cd frontend && npm install
```

2. **Environment Variables**

Required (automatically set by Replit):
- `DATABASE_URL` - PostgreSQL connection string
- `SESSION_SECRET` - JWT secret key

Optional API keys (for real data):
- `CHARTMETRIC_API_KEY`
- `SPOTIFY_CLIENT_ID` & `SPOTIFY_CLIENT_SECRET`
- `LUMINATE_API_KEY`

3. **Run the Application**

```bash
# Backend
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000

# Frontend (must bind to 0.0.0.0:5000)
cd frontend && npm run dev
```

## Using the Demo

### First Time Access

1. **Register**: Create an account (first user becomes admin automatically)
2. **View Demo Catalog**: The dashboard loads with pre-seeded demo data
3. **Explore**:
   - **Catalog tab**: View catalog summary, score breakdowns, and all songs
   - **Search tab**: Search for songs (searches catalog first, then shows mock external data if no match)

### Demo Features

#### Catalog View

Displays:
- **Catalog Summary**: Total songs, controlled publishing %, estimated valuations (Low/Base/High)
- **Score Breakdown Card**: Visual breakdown of the four scoring factors
- **Upload Panel**: Upload filled Schedule A templates for demo purposes
- **Songs Table**: All songs with Publishing %, Master %, Revenue, Valuations, and Scores
- **Song Details**: Click any song to see full analytics, writer splits, and metrics

#### Search View

Features:
- **Universal Search**: Search by song title or artist name
- **Dual Data Sources**: 
  - Shows catalog songs if they match
  - Shows mock "external" results from Chartmetric/Luminate if no catalog match
- **Result Cards**: Display valuation, track metrics, artist metrics, and territories
- **In-Catalog Indicator**: Clearly shows whether a song is in your catalog or external data

#### Song Detail Page

Comprehensive view including:
- Estimated revenue and overall score
- Valuation range (Low/Base/High) with visual emphasis on base valuation
- Score breakdown with progress bars for each factor
- Writer splits with percentages
- ISRC/ISWC codes (if available)
- Track performance metrics with growth indicators
- Playlist performance and top playlists
- Regional performance breakdown

### Uploading a Schedule A (Internal Demo)

1. Navigate to **Catalog View**
2. Find the "Upload Filled Schedule A (Internal Demo)" panel
3. Drag & drop or click to browse for your filled template (PDF, XLSX, or XLS)
4. System will parse the file, fetch analytics (from mock data), and calculate valuations/scores
5. New catalog will appear in the dashboard

**Template Requirements:**
- Use the official MIME Schedule A template
- Include songwriter information (Name, PRO, IPI)
- Song columns: Song Title, Artist(s) Name, Publishing % Owned, Master % Owned, Spotify Link

## API Endpoints

### Authentication
- `POST /api/auth/register` - Register new user
- `POST /api/auth/login` - Login and get JWT token

### Catalog
- `GET /api/catalog/summary` - Get catalog summaries with totals and breakdowns
- `GET /api/catalog/songs` - Get all songs
- `GET /api/catalog/songs/{id}` - Get song details with full analytics
- `POST /api/catalog/upload` - Upload and parse Schedule A file
- `GET /api/catalog/search?q=query` - Search songs (catalog + external mock data)

### Settings
- `GET /api/settings/api-status` - Check which APIs are configured vs. mock

## Mock Data Structure

Demo data is located in `mock_data/`:

1. **demo_catalog.json** - Parsed demo catalog with 5 songs and songwriter info
2. **external_metrics_tracks.json** - Mock track metrics keyed by song title (streams, playlists, growth, territories)
3. **external_metrics_artists.json** - Mock artist metrics keyed by artist name (monthly listeners, followers, growth, genres)

These are used for:
- Seeding the demo catalog on startup
- Providing "external" search results when no catalog match exists
- Simulating Chartmetric/Luminate/Spotify responses until real API keys are added

## Valuation Engine

Calculates **three valuation scenarios** plus revenue estimate:

- **Estimated Revenue**: Annual revenue projection based on streams
- **Low (Conservative)**: Base valuation × 8
- **Base (Realistic)**: Weighted calculation using streams (40%), playlists (30%), Chartmetric score (20%), regional performance (10%)
- **High (Optimistic)**: Base valuation × 15-18 (higher for high-growth songs)

Growth rate influences the high-end multiplier.

## Scoring System

**Four-factor scoring** (each 0-25 points, total 0-100):

1. **Catalog Value** (0-25): Based on total streams and commercial performance
2. **Growth Momentum** (0-25): 3-month and 12-month growth rates
3. **Metadata Health** (0-25): Data completeness (ISRC, ISWC, links) and Chartmetric quality score
4. **Exploitation Potential** (0-25): Playlist reach and positions

Breakdown is displayed visually in both Catalog View and Song Detail pages.

## Configuration for Real Data

To switch from mock to real API data:

1. Go to **Settings** page (admin only)
2. Note the API keys required
3. Add keys via Replit Secrets:
   - `CHARTMETRIC_API_KEY`
   - `SPOTIFY_CLIENT_ID` and `SPOTIFY_CLIENT_SECRET`
   - `LUMINATE_API_KEY`
4. Restart the application
5. System automatically uses real APIs when keys are detected

The flow is identical - only the data source changes.

## Branding

- **Primary**: Purple (#8B5CF6)
- **Accent**: Gold/Orange (#F59E0B)
- **MIME Logo**: Displayed in navigation
- **"Internal Demo" badge**: Visible in navigation header

## Future Enhancements

For production release:
- Separate public website for client Schedule A uploads
- Real-time API integration
- Advanced trend charts and revenue projections
- Multi-tenant architecture for multiple clients
- Automated reporting and export

## Support

This is an internal demo. For questions about the catalog intelligence tool, contact the MIME Publishing product team.

## License

Proprietary - MIME Publishing © 2025

---

**Made In Memphis Entertainment, LLC (MIME)**
*Empowering Artists, Amplifying Voices*
