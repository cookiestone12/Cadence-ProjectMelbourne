# MIME Catalog Intelligence Platform - Internal Demo

## Overview
An internal demo dashboard showcasing MIME Publishing's catalog intelligence tool. This platform demonstrates advanced capabilities for catalog valuation, scoring, and search, intended for future external client offerings. The project's core purpose is to provide comprehensive analytics for musical catalogs, including multi-tiered valuations, a 4-factor scoring system, and integration with mock external data sources to simulate real-world performance metrics.

## User Preferences
### Coding Style
- Python: PEP 8 style, type hints where helpful
- JavaScript/React: Functional components, hooks
- CSS: Tailwind utility classes
- Imports: Absolute imports for backend modules

## System Architecture

### Tech Stack
- **Frontend**: React 18, Tailwind CSS, Vite
- **Backend**: FastAPI (Python 3.11)
- **Database**: PostgreSQL
- **Authentication**: JWT (minimal for demo)

### Core Features
- **Catalog View**: Summary, score breakdown, songs table, integrated upload.
- **Search View**: Universal search across catalog and external mock data.
- **Song Detail**: Comprehensive analytics with valuations, scores, and metrics.
- **3-Tier Valuations**: Low, Base, and High scenarios with estimated revenue projections, incorporating stream types (premium/ad-supported) and territory breakdowns.
- **4-Factor Scoring**: Evaluates Catalog Value, Growth Momentum, Metadata Health, and Exploitation Potential (0-25 points each, totaling 0-100).
- **Mock External Data**: Simulation of Chartmetric, Spotify, and Luminate responses.
- **Demo Catalog Seeding**: Auto-populates 5 demo songs on first run.
- **Catalog Grouping**: Songs organized by catalog with ownership percentages.
- **File Upload**: Drag-and-drop Schedule A processing (internal demo only).
- **MIME Branding**: Purple/orange theme with an "Internal Demo" badge.
- **Revenue Estimate (Admin Collection)**: Calculates revenue based on controlled streams and label split scenarios (80/20, 60/40), differentiating between publishing and master revenue, and premium vs. ad-supported streams.

### Database Schema
- **users**: Authentication.
- **catalogs**: Catalog metadata.
- **songwriters**: Songwriter information.
- **songs**: Core song data with ownership, valuations (`valuation_low`, `valuation_base`, `valuation_high`, `estimated_revenue`), and scoring (`score`, `score_breakdown`), `streams_by_type`, `territory_streams`.
- **settings**: System configuration.

### Core Engines
- **Valuation Engine**: Returns estimated revenue and three valuation tiers (Low, Base, High) based on streams, playlists, Chartmetric score, and regional performance. Incorporates publishing vs. master revenue, and premium vs. ad-supported stream differentiation.
- **Scoring Engine**: Returns a breakdown across four factors: Catalog Value, Growth Momentum, Metadata Health, and Exploitation Potential.

## External Dependencies
- **PostgreSQL**: Primary database for all application data.
- **Mock Chartmetric API**: Simulated external API for music analytics.
- **Mock Spotify API**: Simulated external API for music streaming data.
- **Mock Luminate API**: Simulated external API for music industry data.
- **Vite**: Frontend build tool.
- **Tailwind CSS**: Utility-first CSS framework.
- **React**: Frontend JavaScript library.
- **FastAPI**: Backend Python web framework.
- **SQLAlchemy**: Python SQL toolkit and ORM.
- **Uvicorn**: ASGI server for FastAPI.