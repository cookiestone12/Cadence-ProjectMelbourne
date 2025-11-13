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
- **Catalog View**: Summary with multiplier labels (8×, 12×, 18×), score breakdown, songs table with separated publishing/master revenue columns, integrated upload.
- **Search View**: Universal search across catalog and external mock data.
- **Song Detail Modal**: Pop-out modal displaying comprehensive analytics per song including release date, age, streams (premium/ad-supported), top 3 territories, ownership %, score breakdown, revenue (publishing/master), black box metrics, and valuations with multipliers.
- **3-Tier Valuations**: Low (8×), Base (12×), and High (18×) scenarios with multiplier labels displayed throughout UI.
- **4-Factor Scoring**: Evaluates Catalog Value, Growth Momentum, Metadata Health, and Exploitation Potential (0-25 points each, totaling 0-100).
- **Mock External Data**: Simulation of Chartmetric, Spotify, and Luminate responses.
- **Demo Catalog Seeding**: Auto-populates 5 demo songs with varying release dates (1-8 years old) on first run.
- **Catalog Grouping**: Songs organized by catalog with ownership percentages.
- **File Upload**: Drag-and-drop Schedule A processing with tier-aware ingestion and deduplication (internal demo only).
- **MIME Branding**: Purple/orange theme with an "Internal Demo" badge.
- **Multi-Platform Revenue Tracking**: Tracks streams across 5 major platforms (Spotify, Apple Music, YouTube Music, Amazon Music, Tidal) representing ~62.5% of global market. Uses accurate 2024-2025 platform-specific master recording rates ($0.003-$0.01284/stream) while publishing rates remain consistent ($0.0012 premium, $0.0004 ad-supported). Revenue separated into Publishing and Master columns throughout UI.
- **Tier-Aware Ingestion**: Upload endpoint preserves uploader-provided premium/ad-supported stream breakdowns when available, falling back to market-share estimation for missing data. Supports re-upload deduplication with fresh valuation recalculation.
- **Black Box Tracking**: Collectible publishing value and estimated black box loss calculations based on song age (0-3 years: 100%, 3-5 years: 50%, 5+ years: 10% collectible).
- **Excel Export**: Comprehensive 4-sheet reports (Catalog Summary, Territory Breakdown, Song Details, Methodology) with downloadable XLSX format.

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