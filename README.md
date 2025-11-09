# MIME Catalog Intelligence Platform

A comprehensive music catalog intelligence platform for MIME Publishing that provides automated song valuation, performance scoring, and analytics dashboard.

## Overview

MIME Catalog Intelligence is a single-client platform designed to help MIME Publishing manage and analyze their music catalog. The system automatically fetches data from multiple sources (Chartmetric, Spotify, Luminate) to calculate valuations and performance scores for each song.

## Features

- **Schedule A Template Upload**: Download and upload the official MIME Schedule A template to register songs
- **Automated Analytics**: Fetch streaming data, playlist positions, and regional performance metrics
- **Valuation Engine**: Calculate song worth based on streaming data, playlist reach, and market performance
- **Scoring System**: Rate songs on commercial potential (0-100) based on trend analysis and catalog health
- **Dashboard**: View all songs with key metrics, valuations, and scores at a glance
- **Song Details**: Comprehensive analytics for each song including playlists, regional data, and trends
- **Mock Data Fallback**: System runs with mock data by default and automatically switches to real APIs when keys are provided
- **Admin Settings**: Configure API keys and view integration status

## Tech Stack

### Frontend
- React 18 with React Router
- Tailwind CSS for styling
- Vite for development and building
- Recharts for data visualization
- React Dropzone for file uploads
- Axios for API communication

### Backend
- FastAPI (Python)
- PostgreSQL database via SQLAlchemy ORM
- JWT authentication with role-based access control
- Python libraries: pandas, openpyxl, PyPDF2

### Database
- PostgreSQL (Replit-hosted)
- Models: Users, Songwriters, Songs, Analytics, Settings

## Installation

### Prerequisites
- Python 3.11+
- Node.js 20+
- PostgreSQL database (automatically provided by Replit)

### Setup Instructions

1. **Install Dependencies**

```bash
# Backend dependencies
cd backend
pip install -r requirements.txt

# Frontend dependencies
cd frontend
npm install
```

2. **Environment Variables**

The following environment variables are automatically set by Replit:
- `DATABASE_URL` - PostgreSQL connection string
- `SESSION_SECRET` - JWT secret key

Optional API keys (add via Replit Secrets):
- `CHARTMETRIC_API_KEY` - For Chartmetric analytics
- `SPOTIFY_CLIENT_ID` - For Spotify data
- `SPOTIFY_CLIENT_SECRET` - For Spotify authentication
- `LUMINATE_API_KEY` - For Luminate/radio data
- `CLAUDE_API_KEY` - For future AI-powered features

**Note**: The system runs with mock data by default. Add API keys to enable real data fetching.

3. **Run the Application**

The application uses two workflows:

```bash
# Backend (runs on port 8000)
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000

# Frontend (runs on port 5000)
cd frontend && npm run dev
```

On Replit, both workflows start automatically.

4. **Access the Application**

- Frontend: https://your-repl-url.repl.co
- Backend API: https://your-repl-url.repl.co/api

## Usage

### First Time Setup

1. **Register an Account**
   - Visit the login page
   - Click "Register" to create an account
   - First user automatically gets admin privileges

2. **Download Schedule A Template**
   - Go to the home page
   - Click "Download Template"
   - Fill in songwriter and song information

3. **Upload Schedule A**
   - Login to your account
   - Navigate to "Upload" page
   - Drag and drop or click to upload your completed template
   - Supported formats: PDF, Excel (.xlsx, .xls)

4. **View Analytics**
   - Dashboard shows all songs with valuations and scores
   - Click "View Details" on any song for comprehensive analytics
   - View streaming data, playlist performance, and regional metrics

### Admin Features

Admins can access the Settings page to:
- View API configuration status
- See which services are using mock vs. real data
- Get instructions for adding API keys

## API Endpoints

### Authentication
- `POST /api/auth/register` - Register new user
- `POST /api/auth/login` - Login and get JWT token

### Catalog
- `GET /api/catalog/songs` - Get all songs (requires auth)
- `GET /api/catalog/songs/{id}` - Get song details (requires auth)
- `POST /api/catalog/upload` - Upload Schedule A file (requires auth)

### Settings
- `GET /api/settings` - Get all settings (admin only)
- `POST /api/settings` - Create/update setting (admin only)
- `GET /api/settings/api-status` - Check API configuration status

### Health
- `GET /api/health` - Health check endpoint

## Mock Data

The `mock_data/` directory contains JSON files simulating responses from:
- **chartmetric_response.json**: Chartmetric track data (scores, playlists, trends)
- **spotify_response.json**: Spotify track and streaming data
- **luminate_response.json**: Regional performance and radio data

These mock files are used automatically when real API keys are not configured.

## Valuation Engine

The valuation engine calculates song worth using weighted factors:

- **Stream Value (40%)**: $0.003 per stream average
- **Playlist Value (30%)**: Based on follower count and position in high-profile playlists
- **Chartmetric Score (20%)**: Industry standard scoring
- **Regional Performance (10%)**: Geographic market share

## Scoring System

Songs are scored 0-100 based on:

- **Commercial Potential (40 points)**: Stream counts and playlist positions
- **Trend Momentum (30 points)**: Rising, stable, or declining trajectory
- **Catalog Health (30 points)**: Engagement metrics and quality indicators

Score Ranges:
- 80-100: Excellent (Green)
- 60-79: Good (Yellow)
- 0-59: Needs Attention (Red)

## File Format Requirements

### Schedule A Template

The system expects the following structure:

**Songwriter Information:**
- Songwriter Name
- PRO Affiliation (ASCAP, BMI, SESAC, etc.)
- IPI Number

**Song Table:**
| Song Title | Artist Name | Publishing % Owned | Master % Owned | Spotify Link |
|-----------|-------------|-------------------|----------------|--------------|

**Important Notes:**
- Use the official MIME template for best results
- Deviations from the format may cause parsing errors
- Future updates will include AI-powered extraction for non-standard formats

## Branding

The platform features MIME Publishing's brand colors:
- **Purple** (#8B5CF6): Primary brand color
- **Orange** (#F59E0B): Accent color
- **Dark** (#1F2937): Text and UI elements

Logo and branding elements are located in `frontend/public/`.

## Future Enhancements

Planned features for future releases:
- AI-powered document extraction using Claude
- Real-time API integration with live data
- Advanced analytics with trend charts and revenue projections
- Bulk catalog operations (import/export, batch updates)
- Notification system for performance milestones
- Multi-client tenant architecture

## Support

For questions or issues with MIME Catalog Intelligence, please contact your MIME Publishing administrator.

## License

Proprietary - MIME Publishing © 2025

---

**Made In Memphis Entertainment, LLC (MIME)**
*Empowering Artists, Amplifying Voices*
