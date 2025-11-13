# MIME Catalog Intelligence Platform
## Technical Whitepaper & System Documentation

**Version:** 1.0  
**Last Updated:** November 2025  
**Document Type:** Technical Architecture & Implementation Guide

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [System Architecture](#system-architecture)
3. [Core Features & Functionality](#core-features--functionality)
4. [Multi-Platform Revenue Methodology](#multi-platform-revenue-methodology)
5. [Database Schema](#database-schema)
6. [API Specification](#api-specification)
7. [Upload Ingestion Logic](#upload-ingestion-logic)
8. [Frontend Architecture](#frontend-architecture)
9. [Valuation & Scoring Engines](#valuation--scoring-engines)
10. [Deployment Guide](#deployment-guide)
11. [Technical Stack](#technical-stack)

---

## Executive Summary

### Platform Overview

The MIME Catalog Intelligence Platform is an internal demonstration dashboard showcasing advanced catalog valuation, scoring, and analytics capabilities for musical intellectual property. The platform is designed to demonstrate MIME Publishing's technological capabilities to future external clients while providing comprehensive insights into catalog performance, revenue potential, and exploitation opportunities.

### Key Capabilities

- **Multi-Platform Revenue Tracking**: Accurate streaming revenue calculations across 5 major platforms (Spotify, Apple Music, YouTube Music, Amazon Music, Tidal) representing ~62.5% of global market share
- **3-Tier Valuation System**: Low (8×), Base (12×), and High (18×) valuation scenarios with separated publishing and master components
- **4-Factor Scoring Algorithm**: Comprehensive evaluation across Catalog Value, Growth Momentum, Metadata Health, and Exploitation Potential
- **Tier-Aware Data Ingestion**: Intelligent upload processing that preserves premium vs ad-supported stream breakdowns
- **Real-Time Analytics**: Integration with mock external data sources (Chartmetric, Spotify, Luminate)
- **Black Box Revenue Tracking**: Age-based collectible publishing value calculations

### Business Value

This platform demonstrates MIME Publishing's ability to:
1. Accurately value music catalogs using industry-standard methodologies
2. Track multi-platform streaming performance with platform-specific economics
3. Identify growth opportunities and exploitation potential
4. Provide transparent, data-driven investment analysis
5. Scale analytics capabilities for external client services

---

## System Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                         Frontend Layer                       │
│  React 18 + Tailwind CSS + Vite (Port 5000)                │
│  - Catalog View  - Song Detail  - Search  - Upload         │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       │ REST API (JSON)
                       │
┌──────────────────────▼──────────────────────────────────────┐
│                      Backend Layer                           │
│  FastAPI (Python 3.11) on Port 8000                        │
│  - Catalog Routes  - Analytics  - Upload Processing        │
└──────────────────────┬──────────────────────────────────────┘
                       │
        ┌──────────────┼──────────────┐
        │              │              │
        ▼              ▼              ▼
┌──────────────┐ ┌──────────┐ ┌────────────────┐
│  PostgreSQL  │ │  Mock    │ │  Valuation &   │
│   Database   │ │  APIs    │ │  Scoring       │
│              │ │          │ │  Engines       │
└──────────────┘ └──────────┘ └────────────────┘
```

### Technology Stack

#### Frontend
- **Framework**: React 18.2.0
- **Build Tool**: Vite 5.0.8
- **Styling**: Tailwind CSS 3.4.1
- **Routing**: React Router DOM 6.21.3
- **HTTP Client**: Axios 1.6.5
- **State Management**: React hooks (useState, useEffect)

#### Backend
- **Framework**: FastAPI (Python 3.11)
- **ORM**: SQLAlchemy 2.0.23
- **Server**: Uvicorn (ASGI)
- **Authentication**: JWT (minimal for demo)
- **Database**: PostgreSQL 15+

#### Infrastructure
- **Hosting**: Replit environment
- **Ports**: Backend (8000), Frontend (5000)
- **File Storage**: Local filesystem for uploads

### Data Flow Architecture

```
User Upload → Frontend Validation → Backend API → Parse CSV/Excel
    ↓
Tier-Aware Ingestion Logic (4-case fallback)
    ↓
Mock External API Enrichment (Chartmetric, Spotify, Luminate)
    ↓
Multi-Platform Revenue Calculation
    ↓
Valuation Engine (3 tiers × 2 types = 6 values)
    ↓
Scoring Engine (4 factors)
    ↓
Database Persistence (Songs + Analytics)
    ↓
Frontend Display (Tables, Modals, Charts)
```

---

## Core Features & Functionality

### 1. Catalog View Dashboard

**Purpose**: Primary interface for viewing catalog summary and individual song performance

**Components**:
- **Catalog Summary Card**
  - Total valuation (Low/Base/High) with multiplier labels
  - Separated Publishing and Master valuations
  - Total songs count
  - Average score display
  - Score breakdown visualization (4 factors)

- **Songs Table**
  - Sortable columns: Title, Artist, Publishing %, Master %, Publishing Revenue, Master Revenue, Score
  - Color-coded scores (Green >75, Yellow 50-75, Red <50)
  - Click-to-view song details
  - Integrated upload button

**Technical Implementation**:
```javascript
// Fetches catalog summary and songs
GET /api/catalog/summary
GET /api/catalog/songs

// Returns separated publishing/master data
{
  total_valuation_low_pub: 120000,
  total_valuation_low_master: 180000,
  avg_score: 78.5,
  score_breakdown: {...}
}
```

### 2. Song Detail Modal

**Purpose**: Comprehensive per-song analytics and valuation breakdown

**Data Displayed**:
- **Basic Info**: Title, artist, release date, song age
- **Ownership**: Publishing %, Master %
- **Streaming Data**: 
  - Total streams by platform (5 platforms)
  - Premium vs Ad-Supported breakdown
  - Monthly listeners
- **Territory Performance**: Top 3 territories with stream counts
- **Score Breakdown**: 
  - Catalog Value (0-25)
  - Growth Momentum (0-25)
  - Metadata Health (0-25)
  - Exploitation Potential (0-25)
- **Revenue**:
  - Publishing Revenue (actual from tracked platforms)
  - Master Revenue (actual from tracked platforms)
  - Estimated Total Market Revenue
- **Valuations**:
  - Low (8× multiplier): Publishing + Master
  - Base (12× multiplier): Publishing + Master
  - High (18× multiplier): Publishing + Master
- **Black Box Metrics**:
  - Collectible percentage (based on age)
  - Estimated black box loss

**Technical Implementation**:
```javascript
// Fetches detailed song data
GET /api/catalog/songs/{song_id}

// Returns comprehensive analytics
{
  title: "Song Name",
  analytics: {
    streams_by_type: {
      spotify: {premium: 1000000, ad_supported: 500000},
      apple_music: {premium: 800000, ad_supported: 0},
      ...
    },
    territory_streams: {...},
    top_playlists: [...]
  },
  valuation_low_pub: 50000,
  valuation_low_master: 75000,
  score_breakdown: {...}
}
```

### 3. Multi-Platform Revenue Tracking

**Purpose**: Accurate revenue calculation across all major streaming platforms

**Tracked Platforms**:
1. **Spotify** (Market Share: ~31%)
2. **Apple Music** (Market Share: ~15%, Premium-only)
3. **YouTube Music** (Market Share: ~8%)
4. **Amazon Music** (Market Share: ~5%)
5. **Tidal** (Market Share: ~3.5%, Premium-only)

**Total Coverage**: ~62.5% of global streaming market

**Platform-Specific Economics**:

| Platform | Master (Premium) | Master (Ad-Supported) | Publishing (Premium) | Publishing (Ad-Supported) |
|----------|------------------|----------------------|---------------------|--------------------------|
| Spotify | $0.004 | $0.004 | $0.0012 | $0.0004 |
| Apple Music | $0.01 | N/A | $0.0012 | N/A |
| YouTube Music | $0.008 | $0.008 | $0.0012 | $0.0004 |
| Amazon Music | $0.004 | $0.004 | $0.0012 | $0.0004 |
| Tidal | $0.013 | N/A | $0.0012 | N/A |

**Revenue Calculation Formula**:
```python
for platform in ['spotify', 'apple_music', 'youtube_music', 'amazon_music', 'tidal']:
    premium_streams = streams_by_type[platform]['premium']
    ad_supported_streams = streams_by_type[platform]['ad_supported']
    
    # Publishing uses consistent rates
    publishing_revenue += (
        (premium_streams * 0.0012 * publishing_ownership_pct) +
        (ad_supported_streams * 0.0004 * publishing_ownership_pct)
    )
    
    # Master uses platform-specific rates
    master_revenue += (
        (premium_streams * platform_master_rate_premium * master_ownership_pct) +
        (ad_supported_streams * platform_master_rate_ad * master_ownership_pct)
    )
```

**Key Design Decisions**:
- Publishing rates are consistent across platforms (mechanical licensing standards)
- Master rates vary significantly by platform (2-3× range)
- Premium-only platforms (Apple, Tidal) have 0 ad-supported streams
- Revenue represents "Known Revenue" from tracked platforms (~62.5% of market)
- Total market revenue is estimated using market share extrapolation

### 4. Tier-Aware Upload Ingestion

**Purpose**: Preserve user-provided premium/ad-supported stream breakdowns while providing intelligent fallbacks

**4-Case Ingestion Logic**:

```python
# Case 1: Tier-level data provided (dict with premium/ad_supported keys)
if isinstance(platform_data, dict) and 'premium' in platform_data:
    premium = platform_data['premium']
    ad_supported = platform_data['ad_supported']
    # Preserve exactly as provided

# Case 2: Total streams provided (numeric)
elif isinstance(platform_data, (int, float)):
    if platform in ['apple_music', 'tidal']:
        # Premium-only platforms
        premium = platform_data
        ad_supported = 0
    else:
        # Apply 70/30 heuristic (industry standard)
        premium = platform_data * 0.7
        ad_supported = platform_data * 0.3

# Case 3: Spotify fallback
elif 'spotify_streams' in song_data:
    # Use Spotify with 70/30 split
    total_streams = song_data['spotify_streams']
    premium = total_streams * 0.7
    ad_supported = total_streams * 0.3

# Case 4: Market-share estimation
else:
    # Estimate from other platforms using market share
    estimated_total = calculate_from_market_share(other_platforms)
    premium = estimated_total * 0.7 if not premium_only else estimated_total
    ad_supported = 0 if premium_only else estimated_total * 0.3
```

**Deduplication Logic**:
- Songs deduplicated by Spotify link (if provided) OR title + artist combination
- Re-uploading existing song updates Analytics and recalculates valuations
- Ensures fresh tier-aware data is always preserved

### 5. 3-Tier Valuation System

**Valuation Tiers**:
- **Low (8× multiplier)**: Conservative estimate for risk-averse investors
- **Base (12× multiplier)**: Standard industry valuation
- **High (18× multiplier)**: Optimistic estimate for high-growth catalogs

**Separated Publishing vs Master**:
Each tier produces 6 separate values:
- `valuation_low_pub`, `valuation_low_master`
- `valuation_base_pub`, `valuation_base_master`
- `valuation_high_pub`, `valuation_high_master`

**Calculation**:
```python
def calculate_valuation(analytics, publishing_revenue, master_revenue):
    # Base multipliers
    LOW_MULTIPLIER = 8
    BASE_MULTIPLIER = 12
    HIGH_MULTIPLIER = 18
    
    # Calculate each tier
    valuation_low_pub = publishing_revenue * LOW_MULTIPLIER
    valuation_low_master = master_revenue * LOW_MULTIPLIER
    
    valuation_base_pub = publishing_revenue * BASE_MULTIPLIER
    valuation_base_master = master_revenue * BASE_MULTIPLIER
    
    valuation_high_pub = publishing_revenue * HIGH_MULTIPLIER
    valuation_high_master = master_revenue * HIGH_MULTIPLIER
    
    return {
        'valuation_low': valuation_low_pub + valuation_low_master,
        'valuation_base': valuation_base_pub + valuation_base_master,
        'valuation_high': valuation_high_pub + valuation_high_master,
        'valuation_low_pub': valuation_low_pub,
        'valuation_low_master': valuation_low_master,
        'valuation_base_pub': valuation_base_pub,
        'valuation_base_master': valuation_base_master,
        'valuation_high_pub': valuation_high_pub,
        'valuation_high_master': valuation_high_master,
        'estimated_revenue': publishing_revenue + master_revenue
    }
```

### 6. 4-Factor Scoring System

**Score Components** (0-100 total):

1. **Catalog Value (0-25 points)**
   - Based on total streams and revenue potential
   - Weighs both publishing and master revenue

2. **Growth Momentum (0-25 points)**
   - 3-month growth trend
   - 12-month growth trend
   - Playlist inclusion rate

3. **Metadata Health (0-25 points)**
   - ISRC presence
   - ISWC presence
   - Complete songwriter information
   - Release date accuracy

4. **Exploitation Potential (0-25 points)**
   - Playlist count and quality
   - Regional diversification
   - Chartmetric score
   - Black box collectibility

**Score Visualization**:
- **Green (75-100)**: Excellent, high-value catalog
- **Yellow (50-74)**: Good, standard catalog
- **Red (0-49)**: Needs improvement

### 7. Black Box Revenue Tracking

**Purpose**: Calculate collectible publishing revenue and estimated losses from "black box" sources (unmatched royalties)

**Age-Based Collectibility**:
- **0-3 years old**: 100% collectible (recent, metadata fresh)
- **3-5 years old**: 50% collectible (some aging, partial losses)
- **5+ years old**: 10% collectible (significant historical losses)

**Calculation**:
```python
from datetime import datetime

def calculate_black_box_metrics(song_age_years, publishing_revenue):
    if song_age_years <= 3:
        collectible_pct = 1.0
    elif song_age_years <= 5:
        collectible_pct = 0.5
    else:
        collectible_pct = 0.1
    
    collectible_value = publishing_revenue * collectible_pct
    estimated_loss = publishing_revenue * (1 - collectible_pct)
    
    return {
        'collectible_percentage': collectible_pct * 100,
        'collectible_value': collectible_value,
        'estimated_black_box_loss': estimated_loss
    }
```

### 8. Search Functionality

**Purpose**: Universal search across internal catalog and mock external data

**Search Behavior**:
1. Searches local catalog by title or artist name
2. If no local matches found, returns mock external data from:
   - Mock Chartmetric API
   - Mock Spotify API
   - Mock Luminate API

**Use Case**: Demonstrates capability to integrate external data sources for comprehensive market intelligence

### 9. Excel Export

**Purpose**: Generate comprehensive downloadable reports for offline analysis

**Report Structure** (4 sheets):

1. **Catalog Summary Sheet**
   - Total valuations (all 6 tier × type combinations)
   - Average score and breakdown
   - Total songs count
   - Generation timestamp

2. **Territory Breakdown Sheet**
   - Per-territory stream counts
   - Geographic performance analysis
   - Market penetration metrics

3. **Song Details Sheet**
   - All songs with complete data
   - Publishing and master revenue
   - Valuations (all tiers)
   - Scores and breakdowns

4. **Methodology Sheet**
   - Platform-specific rates table
   - Calculation formulas
   - Tier multiplier explanations
   - Assumptions and disclaimers

---

## Multi-Platform Revenue Methodology

### Overview

The MIME platform calculates streaming revenue using accurate, platform-specific economics that reflect real-world 2024-2025 rates. This methodology separates **Publishing** (mechanical/composition rights) from **Master** (sound recording rights) and differentiates between **Premium** (subscription) and **Ad-Supported** (free tier) streams.

### Platform Rate Research

Rates were researched from:
- Industry reports (RIAA, IFPI)
- Platform documentation
- Music industry publications
- Artist advocacy groups

**Research Date**: Q4 2024 / Q1 2025

### Publishing Rates (Consistent Across Platforms)

Publishing rates are standardized based on mechanical licensing regulations:

- **Premium Streams**: $0.0012 per stream
- **Ad-Supported Streams**: $0.0004 per stream

**Rationale**: Publishing rates follow statutory mechanical licensing rates and do not vary significantly by platform due to regulatory frameworks.

### Master Recording Rates (Platform-Specific)

Master recording rates vary significantly by platform based on:
- Platform's revenue model
- Negotiated label agreements
- Market positioning (premium vs free)
- Geographic distribution

| Platform | Type | Premium Rate | Ad-Supported Rate | Notes |
|----------|------|--------------|-------------------|-------|
| Spotify | Mixed | $0.004 | $0.004 | Largest platform, blended rate |
| Apple Music | Premium-only | $0.01 | N/A | Higher rate due to subscription-only model |
| YouTube Music | Mixed | $0.008 | $0.008 | Mid-range rate, strong ad revenue |
| Amazon Music | Mixed | $0.004 | $0.004 | Similar to Spotify |
| Tidal | Premium-only | $0.013 | N/A | Highest rate, audiophile-focused |

### Premium vs Ad-Supported Differentiation

**Premium Streams**:
- Generated by paid subscribers
- Higher payout rates
- More stable revenue
- Better user engagement

**Ad-Supported Streams**:
- Generated by free tier users
- Lower payout rates (typically 25-33% of premium)
- Higher volume in some markets
- More variable revenue

**Platform-Specific Rules**:
- **Apple Music**: 100% premium (no free tier)
- **Tidal**: 100% premium (no free tier)
- **Spotify**: ~70% premium, ~30% ad-supported (global average)
- **YouTube Music**: ~60% ad-supported, ~40% premium
- **Amazon Music**: ~70% premium, ~30% ad-supported

### Revenue Calculation Process

**Step 1: Extract Platform Streams**
```python
streams_by_type = {
    'spotify': {'premium': 1000000, 'ad_supported': 428571},
    'apple_music': {'premium': 500000, 'ad_supported': 0},
    'youtube_music': {'premium': 300000, 'ad_supported': 200000},
    'amazon_music': {'premium': 200000, 'ad_supported': 85714},
    'tidal': {'premium': 100000, 'ad_supported': 0}
}
```

**Step 2: Apply Ownership Percentages**
```python
publishing_ownership = 75.0  # 75% publishing ownership
master_ownership = 50.0      # 50% master ownership

publishing_pct = publishing_ownership / 100.0  # 0.75
master_pct = master_ownership / 100.0          # 0.50
```

**Step 3: Calculate Revenue by Platform**
```python
total_publishing_revenue = 0
total_master_revenue = 0

for platform, streams in streams_by_type.items():
    premium = streams['premium']
    ad_supported = streams['ad_supported']
    
    # Publishing (consistent rates)
    pub_premium_revenue = premium * 0.0012 * publishing_pct
    pub_ad_revenue = ad_supported * 0.0004 * publishing_pct
    platform_publishing_revenue = pub_premium_revenue + pub_ad_revenue
    
    # Master (platform-specific rates)
    master_premium_rate = PLATFORM_RATES[platform]['premium']
    master_ad_rate = PLATFORM_RATES[platform]['ad_supported']
    
    master_premium_revenue = premium * master_premium_rate * master_pct
    master_ad_revenue = ad_supported * master_ad_rate * master_pct
    platform_master_revenue = master_premium_revenue + master_ad_revenue
    
    total_publishing_revenue += platform_publishing_revenue
    total_master_revenue += platform_master_revenue
```

**Step 4: Calculate Total Revenue**
```python
total_known_revenue = total_publishing_revenue + total_master_revenue
```

### Example Calculation

**Song**: "Example Track"
- **Publishing Ownership**: 75%
- **Master Ownership**: 50%

**Streams**:
- Spotify: 1,000,000 premium, 428,571 ad-supported
- Apple Music: 500,000 premium
- YouTube Music: 300,000 premium, 200,000 ad-supported
- Amazon Music: 200,000 premium, 85,714 ad-supported
- Tidal: 100,000 premium

**Publishing Revenue**:
```
Spotify: (1M × 0.0012 × 0.75) + (428,571 × 0.0004 × 0.75) = $900 + $129 = $1,029
Apple: (500K × 0.0012 × 0.75) = $450
YouTube: (300K × 0.0012 × 0.75) + (200K × 0.0004 × 0.75) = $270 + $60 = $330
Amazon: (200K × 0.0012 × 0.75) + (85,714 × 0.0004 × 0.75) = $180 + $26 = $206
Tidal: (100K × 0.0012 × 0.75) = $90

Total Publishing Revenue = $2,105
```

**Master Revenue**:
```
Spotify: (1M × 0.004 × 0.5) + (428,571 × 0.004 × 0.5) = $2,000 + $857 = $2,857
Apple: (500K × 0.01 × 0.5) = $2,500
YouTube: (300K × 0.008 × 0.5) + (200K × 0.008 × 0.5) = $1,200 + $800 = $2,000
Amazon: (200K × 0.004 × 0.5) + (85,714 × 0.004 × 0.5) = $400 + $171 = $571
Tidal: (100K × 0.013 × 0.5) = $650

Total Master Revenue = $8,578
```

**Total Known Revenue**: $2,105 + $8,578 = **$10,683**

**Note**: This represents revenue from 5 platforms (~62.5% of market). Total market revenue would be extrapolated: $10,683 / 0.625 ≈ **$17,093**

### Market Coverage & Estimation

**Tracked Platforms Coverage**:
- Represents ~62.5% of global streaming market
- Revenue shown is "Known Revenue" from tracked platforms
- Total market revenue estimated by dividing by 0.625

**Other Platforms** (not tracked, ~37.5% of market):
- Deezer
- Pandora
- SoundCloud
- Regional platforms (QQ Music, NetEase, etc.)
- Smaller DSPs

**Estimation Formula**:
```python
total_market_revenue = known_revenue / 0.625
```

### Frontend Display Strategy

**Tooltips Explain**:
- "Revenue from 5 major platforms (~62.5% of market)"
- Platform-specific master rates shown
- Publishing rates noted as consistent
- Methodology transparency

**UI Design**:
- Separated Publishing and Master columns throughout
- Color-coded revenue indicators
- Hover tooltips for methodology
- Clear labeling: "Known Revenue (5 platforms)"

---

## Database Schema

### Overview

The MIME platform uses PostgreSQL with SQLAlchemy ORM for data persistence. The schema is designed to support multi-platform analytics, separated publishing/master revenue, and comprehensive scoring.

### Entity-Relationship Diagram

```
┌─────────────┐         ┌──────────────┐         ┌─────────────┐
│    Users    │         │   Catalogs   │         │ Songwriters │
│             │         │              │         │             │
│ id (PK)     │         │ id (PK)      │         │ id (PK)     │
│ email       │         │ name         │         │ name        │
│ password    │         │ description  │         │ ipi_number  │
│ created_at  │         │ created_at   │         │ pro         │
└─────────────┘         └──────┬───────┘         └──────┬──────┘
                               │                        │
                               │                        │
                               │    ┌───────────────────┘
                               │    │
                               ▼    ▼
                        ┌──────────────────┐
                        │      Songs       │
                        │                  │
                        │ id (PK)          │
                        │ title            │
                        │ artist_name      │
                        │ release_date     │
                        │ catalog_id (FK)  │
                        │ songwriter_id(FK)│
                        │ publishing_%     │
                        │ master_%         │
                        │ valuation_low_pub│
                        │ valuation_low_m..│
                        │ valuation_base..  │
                        │ valuation_high.. │
                        │ score            │
                        │ score_breakdown  │
                        └────────┬─────────┘
                                 │
                                 │ 1:1
                                 │
                                 ▼
                        ┌──────────────────┐
                        │    Analytics     │
                        │                  │
                        │ id (PK)          │
                        │ song_id (FK)     │
                        │ spotify_streams  │
                        │ chartmetric_scor │
                        │ playlist_count   │
                        │ streams_by_type  │ (JSONB)
                        │ territory_stream │ (JSONB)
                        │ top_playlists    │ (JSONB)
                        │ regional_data    │ (JSONB)
                        └──────────────────┘
```

### Table Definitions

#### 1. Users Table

```sql
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**Purpose**: Authentication and user management (minimal for demo)

**Fields**:
- `id`: Auto-incrementing primary key
- `email`: Unique user email for login
- `password_hash`: Hashed password (JWT authentication)
- `full_name`: Display name
- `created_at`, `updated_at`: Audit timestamps

#### 2. Catalogs Table

```sql
CREATE TABLE catalogs (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    owner_id INTEGER REFERENCES users(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**Purpose**: Organize songs into catalog groupings

**Fields**:
- `id`: Auto-incrementing primary key
- `name`: Catalog name (e.g., "2024 Acquisitions")
- `description`: Optional catalog description
- `owner_id`: Foreign key to users table
- `created_at`, `updated_at`: Audit timestamps

#### 3. Songwriters Table

```sql
CREATE TABLE songwriters (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    ipi_number VARCHAR(50),
    pro VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**Purpose**: Store songwriter/composer information

**Fields**:
- `id`: Auto-incrementing primary key
- `name`: Songwriter full name
- `ipi_number`: International Performer Index number
- `pro`: Performing Rights Organization (e.g., "ASCAP", "BMI")
- `created_at`: Audit timestamp

#### 4. Songs Table (Core Entity)

```sql
CREATE TABLE songs (
    id SERIAL PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    artist_name VARCHAR(255) NOT NULL,
    release_date DATE,
    spotify_link VARCHAR(500),
    
    -- Foreign Keys
    catalog_id INTEGER REFERENCES catalogs(id),
    songwriter_id INTEGER REFERENCES songwriters(id),
    
    -- Ownership Percentages
    publishing_percentage DECIMAL(5, 2) DEFAULT 0.00,
    master_percentage DECIMAL(5, 2) DEFAULT 0.00,
    
    -- Publishing Valuations
    valuation_low_pub DECIMAL(12, 2) DEFAULT 0.00,
    valuation_base_pub DECIMAL(12, 2) DEFAULT 0.00,
    valuation_high_pub DECIMAL(12, 2) DEFAULT 0.00,
    
    -- Master Valuations
    valuation_low_master DECIMAL(12, 2) DEFAULT 0.00,
    valuation_base_master DECIMAL(12, 2) DEFAULT 0.00,
    valuation_high_master DECIMAL(12, 2) DEFAULT 0.00,
    
    -- Combined Valuations
    valuation_low DECIMAL(12, 2) DEFAULT 0.00,
    valuation_base DECIMAL(12, 2) DEFAULT 0.00,
    valuation_high DECIMAL(12, 2) DEFAULT 0.00,
    
    -- Revenue
    estimated_revenue DECIMAL(12, 2) DEFAULT 0.00,
    
    -- Scoring
    score INTEGER DEFAULT 0,
    score_breakdown JSONB,
    
    -- Metadata
    isrc VARCHAR(50),
    iswc VARCHAR(50),
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Constraints
    CONSTRAINT unique_spotify_link UNIQUE (spotify_link),
    CONSTRAINT unique_title_artist UNIQUE (title, artist_name)
);
```

**Purpose**: Core song entity with valuations and scoring

**Key Fields**:
- **Ownership**: `publishing_percentage`, `master_percentage` (0-100)
- **Valuations**: 9 separate fields (3 tiers × 3 types)
- **Score**: `score` (0-100), `score_breakdown` (JSONB with 4 factors)
- **Metadata**: `isrc`, `iswc` for metadata health scoring

**Constraints**:
- Unique Spotify link (prevents duplicates)
- Unique title + artist combination (deduplication)

#### 5. Analytics Table

```sql
CREATE TABLE analytics (
    id SERIAL PRIMARY KEY,
    song_id INTEGER UNIQUE REFERENCES songs(id) ON DELETE CASCADE,
    
    -- Spotify Metrics
    spotify_streams BIGINT DEFAULT 0,
    spotify_monthly_listeners INTEGER DEFAULT 0,
    
    -- External Scores
    chartmetric_score INTEGER DEFAULT 0,
    
    -- Playlists
    playlist_count INTEGER DEFAULT 0,
    top_playlists JSONB,
    
    -- Multi-Platform Streams (JSONB)
    streams_by_type JSONB,
    
    -- Territory Data (JSONB)
    territory_streams JSONB,
    
    -- Regional Performance (JSONB)
    regional_data JSONB,
    
    -- Trend Data (JSONB)
    trend_data JSONB,
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**Purpose**: Store comprehensive analytics data for each song

**Key JSONB Fields**:

1. **streams_by_type**:
```json
{
  "spotify": {
    "premium": 1000000,
    "ad_supported": 428571
  },
  "apple_music": {
    "premium": 500000,
    "ad_supported": 0
  },
  "youtube_music": {
    "premium": 300000,
    "ad_supported": 200000
  },
  "amazon_music": {
    "premium": 200000,
    "ad_supported": 85714
  },
  "tidal": {
    "premium": 100000,
    "ad_supported": 0
  }
}
```

2. **territory_streams**:
```json
{
  "US": 5000000,
  "GB": 2000000,
  "DE": 1500000,
  "FR": 1000000,
  "CA": 800000
}
```

3. **top_playlists**:
```json
[
  {
    "name": "Today's Top Hits",
    "followers": 32000000,
    "position": 12
  },
  {
    "name": "RapCaviar",
    "followers": 15000000,
    "position": 8
  }
]
```

4. **regional_data**:
```json
{
  "top_regions": ["North America", "Europe", "Asia"],
  "regional_breakdown": {
    "North America": 0.45,
    "Europe": 0.35,
    "Asia": 0.15,
    "Other": 0.05
  }
}
```

5. **trend_data**:
```json
{
  "growth_3_month": 0.25,
  "growth_12_month": 0.45,
  "peak_rank": 15,
  "current_rank": 28
}
```

**Relationship**: 1:1 with Songs (each song has exactly one analytics record)

#### 6. Settings Table

```sql
CREATE TABLE settings (
    id SERIAL PRIMARY KEY,
    key VARCHAR(255) UNIQUE NOT NULL,
    value TEXT,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**Purpose**: System configuration and feature flags

**Common Settings**:
- `demo_mode`: "true" / "false"
- `default_publishing_rate_premium`: "0.0012"
- `default_publishing_rate_ad`: "0.0004"
- `valuation_multiplier_low`: "8"
- `valuation_multiplier_base`: "12"
- `valuation_multiplier_high`: "18"

### Indexes

```sql
-- Performance Indexes
CREATE INDEX idx_songs_catalog_id ON songs(catalog_id);
CREATE INDEX idx_songs_songwriter_id ON songs(songwriter_id);
CREATE INDEX idx_songs_score ON songs(score);
CREATE INDEX idx_analytics_song_id ON analytics(song_id);

-- Search Indexes
CREATE INDEX idx_songs_title ON songs(title);
CREATE INDEX idx_songs_artist ON songs(artist_name);
CREATE INDEX idx_songs_title_artist ON songs(title, artist_name);

-- JSONB Indexes (for efficient querying)
CREATE INDEX idx_analytics_streams_by_type ON analytics USING GIN (streams_by_type);
CREATE INDEX idx_analytics_territory_streams ON analytics USING GIN (territory_streams);
```

---

## API Specification

### Base Configuration

**Base URL**: `http://localhost:8000/api`  
**Protocol**: HTTP/HTTPS  
**Format**: JSON  
**Authentication**: JWT Bearer Token (minimal for demo)

### Endpoints

#### 1. Get Catalog Summary

**Endpoint**: `GET /catalog/summary`

**Description**: Returns aggregated catalog statistics including total valuations, average scores, and score breakdown.

**Request**:
```http
GET /api/catalog/summary HTTP/1.1
Host: localhost:8000
```

**Response**:
```json
{
  "total_songs": 5,
  "total_valuation_low": 450000.00,
  "total_valuation_base": 675000.00,
  "total_valuation_high": 1012500.00,
  "total_valuation_low_pub": 180000.00,
  "total_valuation_low_master": 270000.00,
  "total_valuation_base_pub": 270000.00,
  "total_valuation_base_master": 405000.00,
  "total_valuation_high_pub": 405000.00,
  "total_valuation_high_master": 607500.00,
  "avg_score": 78.5,
  "score_breakdown": {
    "catalog_value": 22.5,
    "growth_momentum": 19.8,
    "metadata_health": 18.2,
    "exploitation_potential": 18.0
  }
}
```

**Status Codes**:
- `200 OK`: Success
- `500 Internal Server Error`: Database error

#### 2. Get All Songs

**Endpoint**: `GET /catalog/songs`

**Description**: Returns list of all songs with basic info, valuations, and scores.

**Request**:
```http
GET /api/catalog/songs HTTP/1.1
Host: localhost:8000
```

**Response**:
```json
{
  "songs": [
    {
      "id": 1,
      "title": "Summer Nights",
      "artist_name": "The Wanderers",
      "release_date": "2023-06-15",
      "publishing_percentage": 75.0,
      "master_percentage": 50.0,
      "publishing_revenue": 2105.50,
      "master_revenue": 8578.25,
      "valuation_low": 85472.00,
      "valuation_base": 128208.00,
      "valuation_high": 192312.00,
      "valuation_low_pub": 16844.00,
      "valuation_low_master": 68628.00,
      "score": 85,
      "score_breakdown": {
        "catalog_value": 23,
        "growth_momentum": 21,
        "metadata_health": 22,
        "exploitation_potential": 19
      }
    }
  ]
}
```

**Status Codes**:
- `200 OK`: Success
- `500 Internal Server Error`: Database error

#### 3. Get Song Detail

**Endpoint**: `GET /catalog/songs/{song_id}`

**Description**: Returns comprehensive analytics and valuation data for a specific song.

**Request**:
```http
GET /api/catalog/songs/1 HTTP/1.1
Host: localhost:8000
```

**Response**:
```json
{
  "id": 1,
  "title": "Summer Nights",
  "artist_name": "The Wanderers",
  "release_date": "2023-06-15",
  "spotify_link": "https://open.spotify.com/track/abc123",
  "publishing_percentage": 75.0,
  "master_percentage": 50.0,
  "valuation_low": 85472.00,
  "valuation_base": 128208.00,
  "valuation_high": 192312.00,
  "valuation_low_pub": 16844.00,
  "valuation_low_master": 68628.00,
  "valuation_base_pub": 25266.00,
  "valuation_base_master": 102942.00,
  "valuation_high_pub": 37899.00,
  "valuation_high_master": 154413.00,
  "estimated_revenue": 10683.75,
  "score": 85,
  "score_breakdown": {
    "catalog_value": 23,
    "growth_momentum": 21,
    "metadata_health": 22,
    "exploitation_potential": 19
  },
  "analytics": {
    "spotify_streams": 1428571,
    "spotify_monthly_listeners": 125000,
    "chartmetric_score": 82,
    "playlist_count": 15,
    "streams_by_type": {
      "spotify": {
        "premium": 1000000,
        "ad_supported": 428571
      },
      "apple_music": {
        "premium": 500000,
        "ad_supported": 0
      },
      "youtube_music": {
        "premium": 300000,
        "ad_supported": 200000
      },
      "amazon_music": {
        "premium": 200000,
        "ad_supported": 85714
      },
      "tidal": {
        "premium": 100000,
        "ad_supported": 0
      }
    },
    "territory_streams": {
      "US": 5000000,
      "GB": 2000000,
      "DE": 1500000
    },
    "top_playlists": [
      {
        "name": "Today's Top Hits",
        "followers": 32000000,
        "position": 12
      }
    ],
    "trend_data": {
      "growth_3_month": 0.25,
      "growth_12_month": 0.45
    }
  },
  "songwriter": {
    "id": 1,
    "name": "John Smith",
    "ipi_number": "00123456789",
    "pro": "ASCAP"
  },
  "catalog": {
    "id": 1,
    "name": "2024 Catalog"
  },
  "black_box": {
    "collectible_percentage": 100.0,
    "collectible_value": 2105.50,
    "estimated_loss": 0.00
  }
}
```

**Status Codes**:
- `200 OK`: Success
- `404 Not Found`: Song ID doesn't exist
- `500 Internal Server Error`: Database error

#### 4. Upload Schedule A

**Endpoint**: `POST /catalog/upload`

**Description**: Upload CSV/Excel file containing song data with tier-aware stream ingestion and deduplication.

**Request**:
```http
POST /api/catalog/upload HTTP/1.1
Host: localhost:8000
Content-Type: multipart/form-data

------WebKitFormBoundary
Content-Disposition: form-data; name="file"; filename="schedule_a.csv"
Content-Type: text/csv

title,artist_name,publishing_percentage,master_percentage,spotify_streams,spotify_premium,spotify_ad_supported,apple_music_premium
"Summer Nights","The Wanderers",75,50,1428571,1000000,428571,500000
------WebKitFormBoundary--
```

**CSV Format**:

**Required Columns**:
- `title`: Song title
- `artist_name`: Artist/performer name
- `publishing_percentage`: Publishing ownership (0-100)
- `master_percentage`: Master recording ownership (0-100)

**Optional Columns** (tier-aware):
- `spotify_streams`: Total Spotify streams (fallback)
- `spotify_premium`: Spotify premium streams
- `spotify_ad_supported`: Spotify ad-supported streams
- `apple_music_premium`: Apple Music streams (premium-only)
- `youtube_music_premium`: YouTube Music premium streams
- `youtube_music_ad_supported`: YouTube Music ad-supported streams
- `amazon_music_premium`: Amazon Music premium streams
- `amazon_music_ad_supported`: Amazon Music ad-supported streams
- `tidal_premium`: Tidal streams (premium-only)
- `release_date`: Song release date (YYYY-MM-DD)
- `spotify_link`: Spotify track URL
- `isrc`: International Standard Recording Code
- `iswc`: International Standard Musical Work Code
- `songwriter_name`: Composer/writer name
- `ipi_number`: Songwriter IPI number
- `pro`: Performing Rights Organization

**Response**:
```json
{
  "message": "Successfully uploaded 5 songs",
  "songs": [
    {"id": 1, "title": "Summer Nights"},
    {"id": 2, "title": "Urban Dreams"}
  ]
}
```

**Status Codes**:
- `200 OK`: Success
- `400 Bad Request`: Invalid file format or missing required columns
- `500 Internal Server Error`: Processing error

**Tier-Aware Processing**:

The upload endpoint intelligently handles different data formats:

1. **Explicit Tier Data** (preserves exactly):
   ```csv
   title,spotify_premium,spotify_ad_supported
   "Song A",1000000,428571
   ```

2. **Total Streams Only** (applies heuristics):
   ```csv
   title,spotify_streams
   "Song A",1428571
   ```
   → Splits to 1M premium (70%) + 428,571 ad-supported (30%)

3. **Premium-Only Platforms** (Apple, Tidal):
   ```csv
   title,apple_music_premium
   "Song A",500000
   ```
   → apple_music: {premium: 500000, ad_supported: 0}

4. **Missing Platform Data** (estimates from market share):
   - If Spotify provided but Amazon missing
   - Calculates Amazon from Spotify using market share ratio
   - Applies same heuristics (70/30 or premium-only)

**Deduplication**:
- Checks for existing song by `spotify_link` (if provided)
- Falls back to `title + artist_name` match
- Updates existing song's Analytics and recalculates valuations
- Preserves tier-aware data from new upload

#### 5. Search Songs

**Endpoint**: `GET /search?q={query}`

**Description**: Search local catalog and mock external data by title or artist.

**Request**:
```http
GET /api/search?q=summer HTTP/1.1
Host: localhost:8000
```

**Response**:
```json
{
  "results": [
    {
      "source": "local",
      "id": 1,
      "title": "Summer Nights",
      "artist": "The Wanderers",
      "total_streams": 1428571,
      "monthly_streams": 125000,
      "score": 85
    },
    {
      "source": "external_chartmetric",
      "title": "Summer Vibes",
      "artist": "DJ Cool",
      "chartmetric_score": 75,
      "spotify_streams": 2500000
    }
  ]
}
```

**Status Codes**:
- `200 OK`: Success (returns empty array if no matches)
- `400 Bad Request`: Missing query parameter

#### 6. Export Catalog

**Endpoint**: `GET /catalog/export`

**Description**: Generate downloadable Excel report with 4 sheets.

**Request**:
```http
GET /api/catalog/export HTTP/1.1
Host: localhost:8000
```

**Response**:
```http
HTTP/1.1 200 OK
Content-Type: application/vnd.openxmlformats-officedocument.spreadsheetml.sheet
Content-Disposition: attachment; filename="mime_catalog_export_2025-11-13.xlsx"

[Binary Excel file data]
```

**Excel Structure**:

1. **Sheet 1: Catalog Summary**
   - Total valuations (all tiers)
   - Average scores
   - Song count
   - Generation date

2. **Sheet 2: Territory Breakdown**
   - Territory | Streams | % of Total
   - Sorted by stream count

3. **Sheet 3: Song Details**
   - All songs with complete data
   - Publishing/Master revenue
   - Valuations
   - Scores

4. **Sheet 4: Methodology**
   - Platform rates table
   - Calculation formulas
   - Assumptions

**Status Codes**:
- `200 OK`: Success
- `500 Internal Server Error`: Export generation error

---

## Upload Ingestion Logic

### Overview

The upload ingestion system is designed to intelligently process song data while preserving user-provided tier-aware information (premium vs ad-supported stream breakdowns) and falling back gracefully when data is incomplete.

### Processing Flow

```
CSV/Excel Upload
    ↓
Parse Rows (pandas/csv)
    ↓
For Each Song:
    ├─ Extract Basic Info (title, artist, ownership %)
    ├─ Extract Platform Stream Data
    ├─ Apply 4-Case Tier-Aware Logic
    ├─ Enrich with Mock External APIs
    ├─ Check for Existing Song (Deduplication)
    │  ├─ If Exists: Update Analytics & Recalculate
    │  └─ If New: Create Song & Analytics
    ├─ Calculate Multi-Platform Revenue
    ├─ Calculate Valuations (3 tiers × 2 types)
    ├─ Calculate Score (4 factors)
    └─ Persist to Database
    ↓
Return Success Response
```

### 4-Case Tier-Aware Logic

The system handles 4 different data quality scenarios for each platform:

#### Case 1: Explicit Tier-Level Data (Highest Quality)

**Input**: Dictionary with `premium` and `ad_supported` keys
```python
{
  "spotify": {
    "premium": 1000000,
    "ad_supported": 428571
  }
}
```

**Action**: Preserve exactly as provided
```python
streams_by_type['spotify'] = {
    'premium': 1000000,
    'ad_supported': 428571
}
```

**Use Case**: User has detailed DSP reports with tier breakdowns

#### Case 2: Total Streams Only (Good Quality)

**Input**: Numeric value representing total streams
```python
{
  "spotify": 1428571  # Just a number
}
```

**Action**: Apply platform-specific heuristics
```python
if platform in ['apple_music', 'tidal']:
    # Premium-only platforms
    premium = total_streams
    ad_supported = 0
else:
    # Mixed platforms: 70/30 industry standard split
    premium = total_streams * 0.7
    ad_supported = total_streams * 0.3

streams_by_type['spotify'] = {
    'premium': 1000000,  # 70%
    'ad_supported': 428571  # 30%
}
```

**Use Case**: User has total stream counts but not tier breakdown

#### Case 3: Spotify Fallback (Medium Quality)

**Input**: Only Spotify data provided, other platforms missing
```python
{
  "spotify_streams": 1428571,
  # youtube_music, amazon_music, etc. missing
}
```

**Action**: Use Spotify as baseline, estimate others from market share
```python
# Use Spotify with 70/30 split
spotify_premium = spotify_streams * 0.7
spotify_ad_supported = spotify_streams * 0.3

# Estimate other platforms from Spotify using market share
for platform in ['youtube_music', 'amazon_music', 'tidal']:
    market_share_ratio = MARKET_SHARE[platform] / MARKET_SHARE['spotify']
    estimated_total = spotify_streams * market_share_ratio
    
    if platform in ['tidal']:
        premium = estimated_total
        ad_supported = 0
    else:
        premium = estimated_total * 0.7
        ad_supported = estimated_total * 0.3
```

**Use Case**: User only has Spotify data (common for smaller catalogs)

#### Case 4: Market-Share Estimation (Lowest Quality)

**Input**: Some platforms provided, others completely missing
```python
{
  "spotify": 1428571,
  "apple_music": 500000,
  # youtube_music missing - need to estimate
}
```

**Action**: Calculate average from known platforms, estimate missing
```python
# Calculate average streams from known platforms
known_platforms = ['spotify', 'apple_music']
total_known_streams = sum([
    streams[p] * MARKET_SHARE[p] 
    for p in known_platforms
])
avg_streams_per_share = total_known_streams / sum([
    MARKET_SHARE[p] 
    for p in known_platforms
])

# Estimate missing platform
youtube_estimated = avg_streams_per_share * MARKET_SHARE['youtube_music']

# Apply tier heuristics
youtube_premium = youtube_estimated * 0.7
youtube_ad_supported = youtube_estimated * 0.3
```

**Use Case**: Partial data from multiple sources

### Market Share Constants

```python
MARKET_SHARE = {
    'spotify': 0.31,        # 31% of global streaming
    'apple_music': 0.15,    # 15%
    'youtube_music': 0.08,  # 8%
    'amazon_music': 0.05,   # 5%
    'tidal': 0.035          # 3.5%
}
# Total tracked: 62.5%
```

### Deduplication Strategy

**Priority 1: Spotify Link**
```python
if song_data.get('spotify_link'):
    existing_song = db.query(Song).filter(
        Song.spotify_link == song_data['spotify_link']
    ).first()
```

**Priority 2: Title + Artist**
```python
if not existing_song:
    existing_song = db.query(Song).filter(
        Song.title == song_data['title'],
        Song.artist_name == song_data['artist_name']
    ).first()
```

**If Existing Song Found**:
1. Update ownership percentages
2. Update Analytics with new `streams_by_type` (preserving tier data)
3. `db.flush()` to make changes visible
4. Recalculate revenue from fresh Analytics data
5. Recalculate valuations using updated analytics
6. Update song with new valuations and scores
7. Commit transaction

**If New Song**:
1. Create placeholder song record
2. `db.flush()` to get song ID
3. Create Analytics with tier-aware `streams_by_type`
4. Calculate revenue from Analytics data
5. Calculate valuations and scores
6. Update song with calculated values
7. Commit transaction

### Code Implementation

```python
def process_song_upload(song_data: dict, db: Session):
    """
    Process uploaded song data with tier-aware ingestion.
    """
    # Build streams_by_type using 4-case logic
    streams_by_type = {}
    
    for platform in ['spotify', 'apple_music', 'youtube_music', 'amazon_music', 'tidal']:
        # Case 1: Explicit tier data
        if f"{platform}_premium" in song_data:
            premium = song_data[f"{platform}_premium"]
            ad_supported = song_data.get(f"{platform}_ad_supported", 0)
            streams_by_type[platform] = {
                'premium': premium,
                'ad_supported': ad_supported
            }
        
        # Case 2: Total streams
        elif platform in song_data and isinstance(song_data[platform], (int, float)):
            total = song_data[platform]
            if platform in ['apple_music', 'tidal']:
                premium = total
                ad_supported = 0
            else:
                premium = total * 0.7
                ad_supported = total * 0.3
            streams_by_type[platform] = {
                'premium': premium,
                'ad_supported': ad_supported
            }
        
        # Case 3 & 4: Fallback/estimation logic
        else:
            # ... estimation code ...
            pass
    
    # Check for existing song
    existing_song = None
    if song_data.get('spotify_link'):
        existing_song = db.query(Song).filter(
            Song.spotify_link == song_data['spotify_link']
        ).first()
    if not existing_song:
        existing_song = db.query(Song).filter(
            Song.title == song_data['title'],
            Song.artist_name == song_data['artist_name']
        ).first()
    
    if existing_song:
        # Update path
        update_existing_song(existing_song, song_data, streams_by_type, db)
    else:
        # Create path
        create_new_song(song_data, streams_by_type, db)
```

### Data Validation

**Required Fields**:
- `title` (non-empty string)
- `artist_name` (non-empty string)
- `publishing_percentage` (0-100)
- `master_percentage` (0-100)

**Optional but Recommended**:
- At least one platform stream count
- Release date
- ISRC/ISWC codes
- Songwriter information

**Validation Errors**:
```python
if not song_data.get('title'):
    raise ValueError("Title is required")

if song_data['publishing_percentage'] < 0 or song_data['publishing_percentage'] > 100:
    raise ValueError("Publishing percentage must be 0-100")

if not any(platform in song_data for platform in PLATFORMS):
    warnings.warn("No stream data provided, valuations may be inaccurate")
```

---

## Frontend Architecture

### Technology Stack

- **Framework**: React 18.2.0 (functional components + hooks)
- **Routing**: React Router DOM 6.21.3
- **Styling**: Tailwind CSS 3.4.1 (utility-first)
- **HTTP**: Axios 1.6.5
- **Build**: Vite 5.0.8 (fast HMR)

### Component Structure

```
src/
├── components/
│   ├── Navigation.jsx          # Top navigation bar
│   └── SongDetailModal.jsx     # Song detail popup
├── pages/
│   ├── CatalogView.jsx         # Main catalog dashboard
│   ├── Search.jsx              # Search interface
│   ├── Upload.jsx              # File upload page
│   ├── Login.jsx               # Authentication
│   └── Settings.jsx            # Configuration
├── App.jsx                     # Route configuration
├── main.jsx                    # React entry point
└── index.css                   # Global Tailwind styles
```

### Key Components

#### 1. CatalogView.jsx (Main Dashboard)

**Purpose**: Primary interface showing catalog summary and songs table

**State Management**:
```javascript
const [catalogData, setCatalogData] = useState(null);
const [songs, setSongs] = useState([]);
const [selectedSong, setSelectedSong] = useState(null);
const [loading, setLoading] = useState(true);
```

**Data Fetching**:
```javascript
useEffect(() => {
  const fetchData = async () => {
    const [catalogRes, songsRes] = await Promise.all([
      axios.get('/api/catalog/summary'),
      axios.get('/api/catalog/songs')
    ]);
    setCatalogData(catalogRes.data);
    setSongs(songsRes.data.songs);
  };
  fetchData();
}, []);
```

**UI Sections**:

1. **Catalog Summary Card**
```jsx
<div className="bg-white rounded-lg shadow p-6">
  <h2>Catalog Summary</h2>
  
  {/* Valuations with Multiplier Labels */}
  <div className="grid grid-cols-3 gap-4">
    <div>
      <span className="text-purple-600">8× Low</span>
      <p className="text-2xl font-bold">
        ${formatCurrency(catalogData.total_valuation_low)}
      </p>
      <p className="text-sm text-gray-500">
        Pub: ${formatCurrency(catalogData.total_valuation_low_pub)}
      </p>
      <p className="text-sm text-gray-500">
        Master: ${formatCurrency(catalogData.total_valuation_low_master)}
      </p>
    </div>
    {/* Base and High tiers... */}
  </div>
  
  {/* Score Breakdown */}
  <div className="mt-6">
    <h3>Score Breakdown</h3>
    <div className="space-y-2">
      {Object.entries(catalogData.score_breakdown).map(([factor, score]) => (
        <div key={factor} className="flex items-center">
          <span className="w-48">{formatFactorName(factor)}</span>
          <div className="flex-1 bg-gray-200 rounded">
            <div 
              className="bg-purple-600 h-4 rounded"
              style={{ width: `${(score / 25) * 100}%` }}
            />
          </div>
          <span className="ml-2">{score}/25</span>
        </div>
      ))}
    </div>
  </div>
</div>
```

2. **Songs Table**
```jsx
<table className="w-full">
  <thead>
    <tr>
      <th>Title</th>
      <th>Artist</th>
      <th>Publishing %</th>
      <th>Master %</th>
      <th>
        Publishing Revenue
        <InfoTooltip text="Revenue from 5 major platforms (~62.5% of market)" />
      </th>
      <th>
        Master Revenue
        <InfoTooltip text="Platform-specific master rates applied" />
      </th>
      <th>Score</th>
    </tr>
  </thead>
  <tbody>
    {songs.map(song => (
      <tr 
        key={song.id} 
        onClick={() => setSelectedSong(song)}
        className="cursor-pointer hover:bg-gray-50"
      >
        <td>{song.title}</td>
        <td>{song.artist_name}</td>
        <td>{song.publishing_percentage}%</td>
        <td>{song.master_percentage}%</td>
        <td>${formatCurrency(song.publishing_revenue)}</td>
        <td>${formatCurrency(song.master_revenue)}</td>
        <td>
          <span className={getScoreColor(song.score)}>
            {song.score}
          </span>
        </td>
      </tr>
    ))}
  </tbody>
</table>
```

**Tooltips**:
```jsx
function InfoTooltip({ text }) {
  return (
    <div className="inline-block relative group">
      <span className="ml-1 text-gray-400 cursor-help">ℹ️</span>
      <div className="hidden group-hover:block absolute z-10 w-64 p-2 bg-gray-800 text-white text-sm rounded shadow-lg">
        {text}
      </div>
    </div>
  );
}
```

#### 2. SongDetailModal.jsx

**Purpose**: Comprehensive song analytics popup

**Props**:
```javascript
{
  song: Object,        // Selected song data
  onClose: Function    // Close modal callback
}
```

**Structure**:
```jsx
<div className="fixed inset-0 bg-black bg-opacity-50 z-50">
  <div className="bg-white rounded-lg max-w-4xl mx-auto mt-20 p-8">
    {/* Header */}
    <div className="flex justify-between items-start">
      <h2 className="text-3xl font-bold">{song.title}</h2>
      <button onClick={onClose}>×</button>
    </div>
    
    {/* Basic Info Grid */}
    <div className="grid grid-cols-2 gap-6 mt-6">
      <div>
        <label>Artist</label>
        <p>{song.artist_name}</p>
      </div>
      <div>
        <label>Release Date</label>
        <p>{formatDate(song.release_date)}</p>
      </div>
      <div>
        <label>Publishing Ownership</label>
        <p>{song.publishing_percentage}%</p>
      </div>
      <div>
        <label>Master Ownership</label>
        <p>{song.master_percentage}%</p>
      </div>
    </div>
    
    {/* Streaming Data by Platform */}
    <div className="mt-8">
      <h3>Multi-Platform Streams</h3>
      <div className="space-y-4">
        {Object.entries(song.analytics.streams_by_type).map(([platform, data]) => (
          <div key={platform} className="border-l-4 border-purple-600 pl-4">
            <div className="flex justify-between">
              <span className="font-semibold capitalize">
                {platform.replace('_', ' ')}
              </span>
              <span>
                {formatNumber(data.premium + data.ad_supported)} total
              </span>
            </div>
            <div className="text-sm text-gray-600">
              <span>Premium: {formatNumber(data.premium)}</span>
              {data.ad_supported > 0 && (
                <span className="ml-4">
                  Ad-Supported: {formatNumber(data.ad_supported)}
                </span>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
    
    {/* Territory Performance */}
    <div className="mt-8">
      <h3>Top Territories</h3>
      <div className="grid grid-cols-3 gap-4">
        {Object.entries(song.analytics.territory_streams)
          .sort((a, b) => b[1] - a[1])
          .slice(0, 3)
          .map(([territory, streams]) => (
            <div key={territory} className="bg-gray-50 p-4 rounded">
              <p className="text-lg font-semibold">{territory}</p>
              <p className="text-2xl text-purple-600">
                {formatNumber(streams)}
              </p>
            </div>
          ))}
      </div>
    </div>
    
    {/* Score Breakdown */}
    <div className="mt-8">
      <h3>Score Breakdown ({song.score}/100)</h3>
      <div className="grid grid-cols-2 gap-4">
        {Object.entries(song.score_breakdown).map(([factor, score]) => (
          <div key={factor}>
            <div className="flex justify-between mb-1">
              <span>{formatFactorName(factor)}</span>
              <span className="font-semibold">{score}/25</span>
            </div>
            <div className="bg-gray-200 rounded-full h-2">
              <div 
                className="bg-purple-600 h-2 rounded-full"
                style={{ width: `${(score / 25) * 100}%` }}
              />
            </div>
          </div>
        ))}
      </div>
    </div>
    
    {/* Valuations Table */}
    <div className="mt-8">
      <h3>Valuations</h3>
      <table className="w-full">
        <thead>
          <tr>
            <th>Tier</th>
            <th>Publishing</th>
            <th>Master</th>
            <th>Total</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td>Low (8×)</td>
            <td>${formatCurrency(song.valuation_low_pub)}</td>
            <td>${formatCurrency(song.valuation_low_master)}</td>
            <td className="font-bold">
              ${formatCurrency(song.valuation_low)}
            </td>
          </tr>
          <tr>
            <td>Base (12×)</td>
            <td>${formatCurrency(song.valuation_base_pub)}</td>
            <td>${formatCurrency(song.valuation_base_master)}</td>
            <td className="font-bold">
              ${formatCurrency(song.valuation_base)}
            </td>
          </tr>
          <tr>
            <td>High (18×)</td>
            <td>${formatCurrency(song.valuation_high_pub)}</td>
            <td>${formatCurrency(song.valuation_high_master)}</td>
            <td className="font-bold">
              ${formatCurrency(song.valuation_high)}
            </td>
          </tr>
        </tbody>
      </table>
    </div>
    
    {/* Black Box Metrics */}
    <div className="mt-8 bg-orange-50 p-4 rounded">
      <h3>Black Box Analysis</h3>
      <div className="grid grid-cols-2 gap-4">
        <div>
          <label>Collectible %</label>
          <p className="text-2xl font-bold text-orange-600">
            {song.black_box.collectible_percentage}%
          </p>
        </div>
        <div>
          <label>Estimated Loss</label>
          <p className="text-2xl font-bold text-red-600">
            ${formatCurrency(song.black_box.estimated_loss)}
          </p>
        </div>
      </div>
    </div>
  </div>
</div>
```

#### 3. Upload.jsx

**Purpose**: File upload interface with drag-and-drop

**State**:
```javascript
const [file, setFile] = useState(null);
const [uploading, setUploading] = useState(false);
const [result, setResult] = useState(null);
```

**File Upload**:
```javascript
const handleUpload = async () => {
  const formData = new FormData();
  formData.append('file', file);
  
  setUploading(true);
  try {
    const res = await axios.post('/api/catalog/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    });
    setResult(res.data);
  } catch (error) {
    alert('Upload failed: ' + error.message);
  } finally {
    setUploading(false);
  }
};
```

**Drag & Drop**:
```jsx
<div 
  className="border-2 border-dashed border-gray-300 rounded-lg p-12 text-center"
  onDragOver={(e) => e.preventDefault()}
  onDrop={(e) => {
    e.preventDefault();
    setFile(e.dataTransfer.files[0]);
  }}
>
  {file ? (
    <div>
      <p>Selected: {file.name}</p>
      <button onClick={handleUpload} disabled={uploading}>
        {uploading ? 'Uploading...' : 'Upload Schedule A'}
      </button>
    </div>
  ) : (
    <p>Drag CSV/Excel file here or click to select</p>
  )}
</div>
```

### Styling & Theming

**Tailwind Configuration**:
```javascript
// tailwind.config.js
module.exports = {
  theme: {
    extend: {
      colors: {
        purple: {
          600: '#7c3aed',  // MIME primary purple
        },
        orange: {
          500: '#f97316',  // MIME secondary orange
        }
      }
    }
  }
}
```

**Color Usage**:
- **Purple (#7c3aed)**: Primary brand color, buttons, accents
- **Orange (#f97316)**: Secondary color, highlights, warnings
- **Green**: Score >75
- **Yellow**: Score 50-75
- **Red**: Score <50

---

## Valuation & Scoring Engines

### Valuation Engine

**Purpose**: Calculate estimated revenue and 3-tier valuations (Low/Base/High) separated by publishing and master.

**Location**: `backend/services/valuation_engine.py`

**Input**:
```python
{
  'analytics': {
    'spotify_streams': 1428571,
    'chartmetric_score': 82,
    'playlist_count': 15,
    'regional_data': {...},
    'trend_data': {...}
  },
  'publishing_revenue': 2105.50,
  'master_revenue': 8578.25
}
```

**Algorithm**:

```python
def calculate_valuation(analytics, publishing_revenue, master_revenue):
    """
    Calculate 3-tier valuations separated by publishing and master.
    
    Multipliers:
    - Low (8×): Conservative estimate
    - Base (12×): Industry standard
    - High (18×): Growth-optimistic
    """
    
    # Base multipliers
    LOW_MULTIPLIER = 8
    BASE_MULTIPLIER = 12
    HIGH_MULTIPLIER = 18
    
    # Calculate each tier for publishing
    valuation_low_pub = publishing_revenue * LOW_MULTIPLIER
    valuation_base_pub = publishing_revenue * BASE_MULTIPLIER
    valuation_high_pub = publishing_revenue * HIGH_MULTIPLIER
    
    # Calculate each tier for master
    valuation_low_master = master_revenue * LOW_MULTIPLIER
    valuation_base_master = master_revenue * BASE_MULTIPLIER
    valuation_high_master = master_revenue * HIGH_MULTIPLIER
    
    # Combined totals
    valuation_low = valuation_low_pub + valuation_low_master
    valuation_base = valuation_base_pub + valuation_base_master
    valuation_high = valuation_high_pub + valuation_high_master
    
    return {
        'estimated_revenue': publishing_revenue + master_revenue,
        'valuation_low': valuation_low,
        'valuation_base': valuation_base,
        'valuation_high': valuation_high,
        'valuation_low_pub': valuation_low_pub,
        'valuation_low_master': valuation_low_master,
        'valuation_base_pub': valuation_base_pub,
        'valuation_base_master': valuation_base_master,
        'valuation_high_pub': valuation_high_pub,
        'valuation_high_master': valuation_high_master
    }
```

**Multiplier Rationale**:
- **8×**: Risk-averse investment, accounts for catalog decline
- **12×**: Standard industry multiple for stable catalogs
- **18×**: High-growth catalogs with strong momentum

**Revenue Input**:
- `publishing_revenue`: Already calculated from multi-platform streams × publishing rates × ownership %
- `master_revenue`: Already calculated from multi-platform streams × master rates × ownership %

### Scoring Engine

**Purpose**: Evaluate catalog quality across 4 dimensions (0-100 total score)

**Location**: `backend/services/scoring_engine.py`

**Score Components**:

#### 1. Catalog Value (0-25 points)

**Factors**:
- Total streams (higher is better)
- Estimated revenue (higher is better)
- Chartmetric score (0-100 scale)

**Algorithm**:
```python
def calculate_catalog_value(analytics):
    total_streams = analytics['spotify_streams']  # Primary metric
    revenue = analytics.get('estimated_revenue', 0)
    chartmetric = analytics.get('chartmetric_score', 0)
    
    # Stream-based score (0-10 points)
    if total_streams > 10_000_000:
        stream_score = 10
    elif total_streams > 5_000_000:
        stream_score = 8
    elif total_streams > 1_000_000:
        stream_score = 6
    elif total_streams > 500_000:
        stream_score = 4
    else:
        stream_score = 2
    
    # Revenue-based score (0-10 points)
    if revenue > 50000:
        revenue_score = 10
    elif revenue > 20000:
        revenue_score = 8
    elif revenue > 10000:
        revenue_score = 6
    elif revenue > 5000:
        revenue_score = 4
    else:
        revenue_score = 2
    
    # Chartmetric score (0-5 points)
    chartmetric_score = (chartmetric / 100) * 5
    
    return stream_score + revenue_score + chartmetric_score  # Max 25
```

#### 2. Growth Momentum (0-25 points)

**Factors**:
- 3-month growth rate
- 12-month growth rate
- Playlist inclusion count

**Algorithm**:
```python
def calculate_growth_momentum(analytics):
    trend_data = analytics.get('trend_data', {})
    growth_3m = trend_data.get('growth_3_month', 0)
    growth_12m = trend_data.get('growth_12_month', 0)
    playlist_count = analytics.get('playlist_count', 0)
    
    # 3-month growth (0-10 points)
    if growth_3m > 0.50:  # >50% growth
        growth_3m_score = 10
    elif growth_3m > 0.25:  # >25% growth
        growth_3m_score = 8
    elif growth_3m > 0.10:  # >10% growth
        growth_3m_score = 6
    elif growth_3m > 0:     # Positive growth
        growth_3m_score = 4
    else:                   # Declining
        growth_3m_score = 0
    
    # 12-month growth (0-10 points)
    if growth_12m > 1.0:    # >100% growth
        growth_12m_score = 10
    elif growth_12m > 0.50:  # >50% growth
        growth_12m_score = 8
    elif growth_12m > 0.25:  # >25% growth
        growth_12m_score = 6
    elif growth_12m > 0:     # Positive growth
        growth_12m_score = 4
    else:                    # Declining
        growth_12m_score = 0
    
    # Playlist inclusion (0-5 points)
    if playlist_count > 50:
        playlist_score = 5
    elif playlist_count > 20:
        playlist_score = 4
    elif playlist_count > 10:
        playlist_score = 3
    elif playlist_count > 5:
        playlist_score = 2
    else:
        playlist_score = 1
    
    return growth_3m_score + growth_12m_score + playlist_score  # Max 25
```

#### 3. Metadata Health (0-25 points)

**Factors**:
- ISRC presence (International Standard Recording Code)
- ISWC presence (International Standard Musical Work Code)
- Complete songwriter information
- Release date accuracy

**Algorithm**:
```python
def calculate_metadata_health(song, analytics):
    score = 0
    
    # ISRC present (8 points)
    if song.get('isrc'):
        score += 8
    
    # ISWC present (8 points)
    if song.get('iswc'):
        score += 8
    
    # Songwriter info complete (5 points)
    if song.get('songwriter_id'):
        songwriter = get_songwriter(song['songwriter_id'])
        if songwriter.get('ipi_number') and songwriter.get('pro'):
            score += 5
    
    # Release date present (4 points)
    if song.get('release_date'):
        score += 4
    
    return score  # Max 25
```

**Importance**: Proper metadata ensures accurate royalty collection and reduces black box losses.

#### 4. Exploitation Potential (0-25 points)

**Factors**:
- Regional diversification (not concentrated in one market)
- Top playlist quality (follower counts)
- Chartmetric score
- Black box collectibility

**Algorithm**:
```python
def calculate_exploitation_potential(analytics, song_age):
    regional_data = analytics.get('regional_data', {})
    top_playlists = analytics.get('top_playlists', [])
    chartmetric = analytics.get('chartmetric_score', 0)
    
    # Regional diversification (0-8 points)
    if regional_data:
        breakdown = regional_data.get('regional_breakdown', {})
        # Check if streams are well-distributed (no single region >60%)
        max_concentration = max(breakdown.values()) if breakdown else 1.0
        if max_concentration < 0.40:  # <40% in any region = well diversified
            regional_score = 8
        elif max_concentration < 0.60:  # <60%
            regional_score = 5
        else:  # Concentrated in one region
            regional_score = 2
    else:
        regional_score = 0
    
    # Top playlist quality (0-8 points)
    if top_playlists:
        # Check for major playlists (>10M followers)
        major_playlists = [p for p in top_playlists if p['followers'] > 10_000_000]
        if len(major_playlists) >= 2:
            playlist_score = 8
        elif len(major_playlists) >= 1:
            playlist_score = 6
        elif len(top_playlists) >= 5:
            playlist_score = 4
        else:
            playlist_score = 2
    else:
        playlist_score = 0
    
    # Chartmetric score contribution (0-5 points)
    chartmetric_score = (chartmetric / 100) * 5
    
    # Black box collectibility (0-4 points)
    if song_age <= 3:
        blackbox_score = 4  # 100% collectible
    elif song_age <= 5:
        blackbox_score = 2  # 50% collectible
    else:
        blackbox_score = 0  # Only 10% collectible
    
    return regional_score + playlist_score + chartmetric_score + blackbox_score  # Max 25
```

#### Overall Score Calculation

```python
def calculate_score(analytics, song):
    """
    Calculate overall score (0-100) with 4-factor breakdown.
    """
    catalog_value = calculate_catalog_value(analytics)
    growth_momentum = calculate_growth_momentum(analytics)
    metadata_health = calculate_metadata_health(song, analytics)
    exploitation_potential = calculate_exploitation_potential(
        analytics, 
        calculate_song_age(song.get('release_date'))
    )
    
    overall_score = (
        catalog_value + 
        growth_momentum + 
        metadata_health + 
        exploitation_potential
    )
    
    return {
        'overall_score': overall_score,
        'catalog_value': catalog_value,
        'growth_momentum': growth_momentum,
        'metadata_health': metadata_health,
        'exploitation_potential': exploitation_potential
    }
```

**Output**:
```python
{
    'overall_score': 78,
    'catalog_value': 22,      # out of 25
    'growth_momentum': 19,    # out of 25
    'metadata_health': 18,    # out of 25
    'exploitation_potential': 19  # out of 25
}
```

---

## Deployment Guide

### Prerequisites

- Python 3.11+
- Node.js 18+
- PostgreSQL 15+
- Git

### Backend Setup

**1. Install Python Dependencies**
```bash
cd backend
pip install -r requirements.txt
```

**requirements.txt**:
```
fastapi==0.109.0
uvicorn==0.25.0
sqlalchemy==2.0.23
psycopg2-binary==2.9.9
python-jose==3.3.0
passlib==1.7.4
python-multipart==0.0.6
pandas==2.1.4
openpyxl==3.1.2
```

**2. Configure Database**

Create `.env` file:
```bash
DATABASE_URL=postgresql://user:password@localhost:5432/mime_catalog
SECRET_KEY=your-secret-key-here
```

**3. Initialize Database**
```bash
python -c "from models.models import Base, engine; Base.metadata.create_all(engine)"
```

**4. Seed Demo Data**
```bash
python seed_data.py
```

**5. Run Backend**
```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### Frontend Setup

**1. Install Dependencies**
```bash
cd frontend
npm install
```

**2. Configure API URL**

Create `frontend/.env`:
```
VITE_API_URL=http://localhost:8000
```

**3. Run Frontend**
```bash
npm run dev
```

Frontend will be available at `http://localhost:5000`

### Production Deployment

**Backend (Replit)**:
```bash
# run_backend.sh
#!/bin/bash
cd backend
uvicorn main:app --host 0.0.0.0 --port 8000
```

**Frontend (Replit)**:
```bash
# Vite production build serves on port 5000
cd frontend
npm run build
npm run preview -- --host 0.0.0.0 --port 5000
```

**Workflows Configuration**:
- Backend workflow: `bash run_backend.sh`
- Frontend workflow: `cd frontend && npm run dev`

### Environment Variables

**Backend**:
- `DATABASE_URL`: PostgreSQL connection string
- `SECRET_KEY`: JWT signing key
- `CORS_ORIGINS`: Allowed frontend origins (default: `http://localhost:5000`)

**Frontend**:
- `VITE_API_URL`: Backend API base URL

### Database Migrations

For schema changes:
```bash
# After modifying models.models.py
python -c "from models.models import Base, engine; Base.metadata.create_all(engine)"
```

For production, use Alembic:
```bash
alembic revision --autogenerate -m "Description"
alembic upgrade head
```

---

## Technical Stack

### Complete Technology Inventory

**Frontend**:
- React 18.2.0
- React Router DOM 6.21.3
- Axios 1.6.5
- Tailwind CSS 3.4.1
- Vite 5.0.8
- PostCSS 8.4.33

**Backend**:
- Python 3.11
- FastAPI 0.109.0
- Uvicorn 0.25.0 (ASGI server)
- SQLAlchemy 2.0.23 (ORM)
- Psycopg2 2.9.9 (PostgreSQL adapter)
- Python-Jose 3.3.0 (JWT)
- Pandas 2.1.4 (CSV/Excel processing)
- OpenPyXL 3.1.2 (Excel generation)

**Database**:
- PostgreSQL 15+

**Development Tools**:
- Git (version control)
- ESLint (frontend linting)
- Black (Python formatting)
- pytest (backend testing)

**Infrastructure**:
- Replit (hosting platform)
- Nix (package management)

---

## Appendix

### Platform Rate Sources

**Research conducted**: October-November 2024

**Sources**:
1. Streaming royalty calculator tools (multiple independent sources)
2. Music industry publications (Billboard, Music Business Worldwide)
3. Artist advocacy groups (UMAW, MLC)
4. Platform documentation (where available)

**Note**: Rates are subject to change and vary by country, contract terms, and catalog size. The rates implemented represent industry averages for independent rights holders.

### Glossary

- **ISRC**: International Standard Recording Code - unique identifier for recordings
- **ISWC**: International Standard Musical Work Code - unique identifier for compositions
- **IPI**: Interested Parties Information - unique identifier for songwriters/publishers
- **PRO**: Performing Rights Organization (e.g., ASCAP, BMI, SESAC)
- **DSP**: Digital Service Provider (streaming platforms)
- **Mechanical Royalties**: Publishing royalties from reproductions
- **Master Recording**: Sound recording copyright (separate from composition)
- **Publishing**: Composition/songwriting copyright
- **Black Box**: Unmatched royalties held by collecting societies
- **Chartmetric**: Music analytics platform providing artist rankings

### Contact & Support

For questions about this platform or MIME Publishing services:
- **Email**: tech@mimepublishing.com
- **Documentation**: This whitepaper
- **Demo**: Internal access only

---

**End of Technical Whitepaper**

*This document is confidential and intended for internal use and client demonstrations only.*
