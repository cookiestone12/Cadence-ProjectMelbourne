# MIME Catalog Intelligence Platform

## Project Overview
A comprehensive music catalog intelligence platform for MIME Publishing with automated song valuation, performance scoring, and analytics dashboard.

**Status**: Initial MVP completed (November 9, 2025)

## Architecture

### Tech Stack
- **Frontend**: React 18 + Tailwind CSS + Vite
- **Backend**: FastAPI (Python 3.11)
- **Database**: PostgreSQL (Replit-hosted)
- **Authentication**: JWT with role-based access control

### Project Structure
```
/
├── backend/              # FastAPI backend application
│   ├── models/          # Database models (SQLAlchemy)
│   ├── routes/          # API endpoints (auth, catalog, settings)
│   ├── services/        # External API integrations & engines
│   └── utils/           # Authentication utilities
├── frontend/            # React frontend application
│   ├── src/
│   │   ├── components/  # Reusable UI components
│   │   ├── pages/       # Page components
│   │   └── services/    # API client services
│   └── public/          # Static assets (logo, templates)
├── mock_data/           # Mock API responses (Chartmetric, Spotify, Luminate)
└── uploads/             # Uploaded Schedule A files

```

## Key Features

### Implemented (MVP)
1. ✅ Home page with Schedule A template download
2. ✅ File upload with drag-and-drop (PDF/Excel support)
3. ✅ Dashboard showing all songs with metrics
4. ✅ Song detail view with comprehensive analytics
5. ✅ Mock data layer for API integrations
6. ✅ Valuation engine (stream-based calculation)
7. ✅ Scoring system (0-100 commercial potential)
8. ✅ Admin settings for API key configuration
9. ✅ PostgreSQL database with full schema
10. ✅ JWT authentication with admin roles
11. ✅ Backend API with all CRUD operations
12. ✅ MIME branding (purple/orange theme)

### Planned (Future)
- AI-powered document extraction with Claude
- Real-time API integration (when keys provided)
- Advanced analytics with trend charts
- Bulk catalog operations
- Notification system
- Multi-client tenant architecture

## Database Schema

### Tables
- **users**: Authentication and authorization
- **songwriters**: Songwriter information (PRO, IPI)
- **songs**: Core song data with ownership percentages
- **analytics**: Performance metrics and data
- **settings**: System configuration key-value pairs

## API Integration Strategy

The system uses a **fallback architecture**:
1. Check for API keys in environment variables
2. If keys exist → Make real API calls
3. If no keys → Use mock data from `mock_data/` directory

### Supported APIs
- **Chartmetric**: Track scoring, playlist data, trends
- **Spotify**: Streaming data, track metrics
- **Luminate**: Regional performance, radio spins
- **Claude**: (Future) AI document extraction

## Environment Variables

### Required (Auto-configured by Replit)
- `DATABASE_URL` - PostgreSQL connection
- `SESSION_SECRET` - JWT secret key
- `PGHOST`, `PGPORT`, `PGUSER`, `PGPASSWORD`, `PGDATABASE`

### Optional (Add via Replit Secrets)
- `CHARTMETRIC_API_KEY`
- `SPOTIFY_CLIENT_ID`
- `SPOTIFY_CLIENT_SECRET`
- `LUMINATE_API_KEY`
- `CLAUDE_API_KEY`

## Workflows

Two workflows are configured:

1. **backend** (Console, Port 8000)
   - Command: `bash run_backend.sh`
   - Runs FastAPI with uvicorn

2. **frontend** (Webview, Port 5000)
   - Command: `cd frontend && npm run dev`
   - Runs Vite dev server with proxy to backend

## Recent Changes

### November 9, 2025 - Initial Implementation
- Created full-stack application with React frontend and FastAPI backend
- Implemented database models and migrations
- Built valuation engine with weighted calculation
- Built scoring system with commercial potential rating
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

### LSP Warnings
- Minor type checking warnings in backend (non-blocking)
- React Router future flag warnings (informational)

### Limitations
- PDF parsing is basic (structured Excel recommended)
- Mock data is static (will be dynamic with real APIs)
- Single-client architecture (no multi-tenancy yet)

## Development Notes

### Running Locally
```bash
# Backend
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000

# Frontend
cd frontend && npm run dev
```

### Database Migrations
Database schema is auto-created on application startup via SQLAlchemy's `create_all()`.

### File Upload Processing
1. User uploads Schedule A (PDF/Excel)
2. Backend parses file using openpyxl/PyPDF2
3. Creates songwriter and song records
4. Fetches analytics from APIs (or mock data)
5. Calculates valuation and score
6. Stores everything in database

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
- Colors: Purple (#8B5CF6), Orange (#F59E0B), Dark (#1F2937)

## Contact

This platform was built for MIME Publishing (Made In Memphis Entertainment, LLC).
