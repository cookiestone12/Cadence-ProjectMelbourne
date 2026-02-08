# Ampersound Intelligence - Deployment & Scaling Guide

A comprehensive guide for deploying the Ampersound platform outside of Replit. This document covers Docker deployment, environment configuration, database migration, scaling strategies, and production best practices.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Quick Start (Docker)](#quick-start-docker)
- [Environment Variables](#environment-variables)
- [Database Setup](#database-setup)
- [Deployment Options](#deployment-options)
- [Scaling Guidelines](#scaling-guidelines)
- [Monitoring & Observability](#monitoring--observability)
- [Security Checklist](#security-checklist)
- [Backup & Recovery](#backup--recovery)
- [Architecture Overview](#architecture-overview)

---

## Prerequisites

Before deploying Ampersound, ensure you have the following installed:

- **Docker** 20.10+ and **Docker Compose** 2.0+
- **PostgreSQL** 15+ (for local development or managed database)
- **Node.js** 20+ (for frontend builds)
- **Python** 3.11+ (for backend development/debugging)
- **Git** (for version control)
- **OpenSSL/TLS** support for HTTPS configuration

For managed databases and deployment platforms, see [Deployment Options](#deployment-options).

---

## Quick Start (Docker)

The fastest way to run Ampersound is with Docker Compose, which orchestrates the application container and PostgreSQL database.

### 1. Clone and Setup

```bash
git clone <repository-url>
cd ampersound
cp .env.example .env
```

### 2. Configure Environment

Edit `.env` with your configuration (see [Environment Variables](#environment-variables)):

```bash
# Essential variables
DATABASE_URL=postgresql://ampersound:ampersound_dev@db:5432/ampersound
SESSION_SECRET=your-strong-random-secret-here
```

### 3. Build and Run

```bash
# Build images and start all services
docker-compose up --build

# Run in background
docker-compose up -d --build
```

This launches:
- **Frontend**: React 18 + Vite application
- **Backend**: FastAPI server with gunicorn workers
- **Database**: PostgreSQL 15 with persistent volume

### 4. Verify Deployment

```bash
# Check container status
docker-compose ps

# View logs
docker-compose logs -f app

# Test API health
curl http://localhost:8000/api/health

# Access application
# Open http://localhost:8000 in your browser
```

### 5. Stop Services

```bash
# Stop containers (preserves data)
docker-compose down

# Stop and remove all data
docker-compose down -v
```

---

## Environment Variables

All configuration is managed through environment variables. See `.env.example` for a complete template.

### Required Variables

| Variable | Purpose | Example |
|----------|---------|---------|
| `DATABASE_URL` | PostgreSQL connection string | `postgresql://user:pass@host:5432/ampersound` |
| `SESSION_SECRET` | JWT signing secret (32+ chars) | Use `openssl rand -base64 32` |

### Server Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `PORT` | `8000` | Server listen port |
| `WEB_CONCURRENCY` | `4` | Gunicorn worker count; scale with CPU cores |
| `LOG_LEVEL` | `INFO` | Logging verbosity (INFO, DEBUG, WARNING, ERROR) |
| `LOG_FORMAT` | `text` | Log format (`text` or `json`) |
| `CORS_ORIGINS` | `*` | Comma-separated allowed origins; restrict in production |
| `SQL_DEBUG` | `false` | Enable SQLAlchemy SQL logging (development only) |

### Integration Keys (Optional)

| Variable | Service | When Needed |
|----------|---------|-------------|
| `SPOTIFY_CLIENT_ID` | Spotify API | Enabling catalog imports from Spotify |
| `SPOTIFY_CLIENT_SECRET` | Spotify API | Required with CLIENT_ID |
| `AI_INTEGRATIONS_OPENAI_API_KEY` | OpenAI API | AI-powered features (valuation, analysis) |
| `CHARTMETRIC_API_KEY` | Chartmetric | Music data enrichment |
| `LUMINATE_API_KEY` | Luminate | Streaming analytics |
| `LUMINATE_API_SECRET` | Luminate | Required with API_KEY |
| `CLAUDE_API_KEY` | Anthropic Claude | Alternative AI provider |

### Example Production Configuration

```bash
# .env (production)
DATABASE_URL=postgresql://app:SecurePassword@db.example.com:5432/ampersound
SESSION_SECRET=your-32-character-random-secret-string-here
PORT=8000
WEB_CONCURRENCY=8
LOG_LEVEL=INFO
LOG_FORMAT=json
CORS_ORIGINS=https://app.example.com,https://www.example.com
SPOTIFY_CLIENT_ID=your_spotify_client_id
SPOTIFY_CLIENT_SECRET=your_spotify_client_secret
AI_INTEGRATIONS_OPENAI_API_KEY=sk-...
```

---

## Database Setup

### Fresh Database Installation

When deploying to a new database, initialize the schema with Alembic migrations:

```bash
# Inside the container or in your environment
alembic upgrade head

# Or with docker-compose
docker-compose exec app alembic upgrade head
```

This creates all required tables and relationships. No manual schema creation is needed.

### Migrating from Replit

To move data from the Replit database to your self-hosted database:

#### Step 1: Export from Replit

```bash
# From Replit terminal
pg_dump $DATABASE_URL --format custom --file ampersound_backup.dump

# Download the file via Replit UI
```

#### Step 2: Import to New Database

```bash
# Restore to target database
pg_restore --verbose \
  --host=your-db-host \
  --username=app \
  --dbname=ampersound \
  ampersound_backup.dump

# You'll be prompted for the password
```

#### Step 3: Verify Migration

```bash
# Connect to new database
psql postgresql://app:password@your-db-host:5432/ampersound

# Check table counts
SELECT schemaname, COUNT(*) as table_count 
FROM pg_tables 
GROUP BY schemaname;

# Verify critical tables
SELECT COUNT(*) FROM "Organization";
SELECT COUNT(*) FROM "Song";
SELECT COUNT(*) FROM "Creator";
```

#### Step 4: Run Pending Migrations

```bash
# Apply any schema changes since the backup
alembic upgrade head
```

### Database Maintenance

For production databases, schedule regular maintenance:

```bash
# Analyze query plans (weekly)
ANALYZE;

# Reindex (monthly for large tables)
REINDEX INDEX CONCURRENTLY index_name;

# Vacuum (weekly)
VACUUM ANALYZE;
```

---

## Deployment Options

### Option 1: Docker (Recommended for Most Use Cases)

**Best for**: Quick deployment, development, small to medium deployments.

A single Docker image combines the frontend (React/Vite) and backend (FastAPI/gunicorn) into one container. See `Dockerfile` and `docker-compose.yml` for reference.

#### Configuration

The Docker image automatically:
1. Builds the React frontend with `npm run build`
2. Installs Python dependencies
3. Copies frontend build artifacts into the backend
4. Runs gunicorn with the backend FastAPI application

#### Environment Variable Override

In `docker-compose.yml`, adjust resource allocation for your workload:

```yaml
services:
  app:
    # ... other config ...
    environment:
      WEB_CONCURRENCY: "8"  # More workers for high concurrency
      LOG_FORMAT: "json"
      CORS_ORIGINS: "https://app.example.com"
```

#### Scaling with Docker

For horizontal scaling with multiple instances:

```bash
# Run multiple containers behind nginx load balancer
docker-compose up -d --scale app=3

# Configure nginx upstream to distribute traffic
# Use external database (not docker-compose db service)
```

**Note**: Docker Compose is designed for single-host deployments. For multi-host Docker, use Docker Swarm or Kubernetes.

---

### Option 2: Separate Services (For Large Deployments)

**Best for**: High-traffic applications, independent scaling, dedicated infrastructure.

Deploy frontend, backend, and database as separate services.

#### Frontend Deployment

```bash
# Build static files
cd frontend
npm run build
# Output: frontend/dist/

# Serve with nginx or CDN
# Option A: Self-hosted nginx
docker run -d \
  -p 80:80 \
  -v $(pwd)/frontend/dist:/usr/share/nginx/html \
  nginx:latest

# Option B: CDN (Cloudflare, AWS CloudFront, etc.)
# Upload frontend/dist to your CDN provider
```

#### Backend Deployment

```bash
# Run without Docker (systemd service example)
# Create /etc/systemd/system/ampersound-backend.service

[Unit]
Description=Ampersound Backend
After=network.target postgresql.service

[Service]
Type=notify
User=ampersound
WorkingDirectory=/opt/ampersound
ExecStart=gunicorn backend.main:app -c backend/gunicorn_config.py
Environment="DATABASE_URL=postgresql://..."
Environment="SESSION_SECRET=..."
Restart=always

[Install]
WantedBy=multi-user.target

# Enable and start
systemctl enable ampersound-backend
systemctl start ampersound-backend
```

#### Database Deployment

Use a managed service:
- **AWS RDS PostgreSQL** (most scalable)
- **Google Cloud SQL**
- **Supabase** (PostgreSQL + hosting)
- **DigitalOcean Managed Databases**
- **Self-hosted PostgreSQL** (requires backup/HA setup)

Configuration:

```bash
# Update backend environment
DATABASE_URL=postgresql://app:password@prod-db.example.com:5432/ampersound
```

---

### Option 3: Platform-as-a-Service (PaaS)

**Best for**: Minimal operations, automatic scaling, fully managed infrastructure.

These platforms simplify deployment by handling Docker orchestration, load balancing, and SSL certificates.

#### Railway

```bash
# Install Railway CLI
npm i -g @railway/cli

# Login and init project
railway login
railway init

# Deploy
railway up

# Environment variables
railway variables set DATABASE_URL=...
railway variables set SESSION_SECRET=...
```

#### Render

1. Create account at render.com
2. Create new Web Service
3. Connect GitHub repository
4. Build command: `npm run build --prefix frontend && pip install -r backend/requirements.txt`
5. Start command: `gunicorn backend.main:app -c backend/gunicorn_config.py`
6. Add environment variables for `DATABASE_URL`, `SESSION_SECRET`, etc.
7. Add PostgreSQL database service
8. Deploy

#### Fly.io

```bash
# Install flyctl
curl -L https://fly.io/install.sh | sh

# Login
flyctl auth login

# Launch (uses Dockerfile)
flyctl launch

# Set environment variables
flyctl secrets set SESSION_SECRET=...
flyctl secrets set DATABASE_URL=...

# Deploy
flyctl deploy
```

#### Heroku (Legacy)

Heroku discontinued free tier but remains an option for small deployments.

```bash
# Install Heroku CLI
brew install heroku/brew/heroku

# Login
heroku login

# Create app
heroku create ampersound-app

# Add PostgreSQL
heroku addons:create heroku-postgresql:standard-0

# Deploy
git push heroku main

# Set environment
heroku config:set SESSION_SECRET=...
```

---

## Scaling Guidelines

### Horizontal Scaling (Multiple Instances)

The backend is **stateless** and designed for horizontal scaling:

- **JWT Authentication**: No server-side sessions; each request is independently authenticated
- **No Local State**: All data stored in PostgreSQL
- **Uploads**: Stored in a shared volume or object storage (S3/GCS)

#### Scaling Strategy

```
┌─────────────────────────────────────────┐
│         Load Balancer (nginx/ALB)       │
├──────────────┬──────────────┬───────────┤
│   Backend 1  │   Backend 2  │ Backend 3 │
│  (gunicorn)  │  (gunicorn)  │(gunicorn) │
└──────────────┴──────────────┴───────────┘
                      │
              ┌───────▼────────┐
              │   PostgreSQL   │
              │ (connection    │
              │  pool)         │
              └────────────────┘
```

#### Configuration

```bash
# Scale gunicorn workers per instance
WEB_CONCURRENCY=8  # For 4-core machine: 2*cores + 1

# Behind load balancer, run multiple instances
docker-compose up -d --scale app=3

# For Kubernetes (automatic scaling)
replicas: 3
resources:
  limits:
    cpu: 500m
    memory: 512Mi
```

### Database Scaling

#### Connection Pooling

Large deployments should use **PgBouncer** to prevent connection exhaustion:

```ini
# pgbouncer.ini
[databases]
ampersound = host=db.example.com port=5432 dbname=ampersound

[pgbouncer]
pool_mode = transaction
max_client_conn = 1000
default_pool_size = 25
reserve_pool_size = 5
reserve_pool_timeout = 3
```

Connect applications to PgBouncer instead of PostgreSQL directly:

```bash
DATABASE_URL=postgresql://app:password@pgbouncer.local:6432/ampersound
```

#### Read Replicas (For Analytics)

For high-volume analytics queries:

```bash
# Configure PostgreSQL streaming replication
# Or use managed service (RDS, Cloud SQL)

# In application, route analytics queries to replica
ANALYTICS_DATABASE_URL=postgresql://app:password@replica.example.com:5432/ampersound
```

#### Regular Maintenance

Schedule in low-traffic windows:

```bash
# Weekly VACUUM (reclaim space)
VACUUM ANALYZE;

# Monthly REINDEX
REINDEX INDEX CONCURRENTLY idx_song_status;

# Track bloat (tables/indexes > 100 MB with >20% waste)
SELECT schemaname, tablename, pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename))
FROM pg_tables
WHERE pg_total_relation_size(schemaname||'.'||tablename) > 100000000
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
```

### Caching Strategy

#### Redis for Session & Rate Limiting

Install Redis and configure the application:

```bash
# docker-compose addition
services:
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
```

Use for:
- Session caching (avoid database hits)
- Rate limiting on auth endpoints
- Request deduplication

#### CDN for Static Assets

```bash
# Build frontend
npm run build --prefix frontend

# Upload frontend/dist to CDN (Cloudflare, CloudFront, etc.)
# Update CORS_ORIGINS to include CDN domain
CORS_ORIGINS=https://cdn.example.com,https://app.example.com

# Invalidate cache on deployment
# (CDN-specific commands vary by provider)
```

#### Query Caching

Cache expensive operations in Redis:

```python
# Example: Cache valuation calculations
CACHE_TTL = 86400  # 1 day

# Check cache before computing
# Store results in Redis after computation
```

---

## Monitoring & Observability

### Structured Logging

Enable JSON logging for log aggregation services:

```bash
LOG_FORMAT=json
LOG_LEVEL=INFO
```

Log output includes:
- Timestamp (ISO 8601)
- Request ID (for tracing across services)
- HTTP method and path
- Response status and duration
- Error messages with stack traces

Example JSON log:

```json
{
  "timestamp": "2026-02-08T14:30:45.123Z",
  "level": "INFO",
  "request_id": "a1b2c3d4",
  "method": "POST",
  "path": "/api/songs",
  "status": 201,
  "duration_ms": 145,
  "message": "Song created"
}
```

#### Log Aggregation Setup

**CloudWatch (AWS)**:

```bash
# Install CloudWatch agent
pip install watchtower

# In application
import logging
from watchtower import CloudWatchLogHandler

handler = CloudWatchLogHandler()
logging.getLogger().addHandler(handler)
```

**Datadog**:

```bash
# Send logs directly to Datadog
LOG_AGGREGATION_ENDPOINT=https://http-intake.logs.datadoghq.com/v1/input/
DATADOG_API_KEY=your_key
```

**Stackdriver (GCP)**:

```bash
# GCP automatically collects logs from running services
# View in Cloud Logging console
```

### Error Tracking (Sentry)

Monitor production errors in real-time:

```bash
# Install Sentry SDK
pip install sentry-sdk[fastapi]
```

Configure in `backend/main.py`:

```python
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration

sentry_sdk.init(
    dsn=os.getenv("SENTRY_DSN"),
    integrations=[FastApiIntegration()],
    traces_sample_rate=0.1,
    environment=os.getenv("ENVIRONMENT", "production")
)
```

Set environment variable:

```bash
SENTRY_DSN=https://your-key@sentry.io/project-id
```

### Health Checks

The application includes a health check endpoint:

```bash
# Check application health
curl http://localhost:8000/api/health
# Returns: {"status":"healthy","service":"Gotcha Catalog Manager"}
```

Configure load balancers to use this endpoint:

```yaml
# Docker Compose health check
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:8000/api/health"]
  interval: 30s
  timeout: 10s
  retries: 3
```

### Database Monitoring

Monitor connection pool health:

```python
# In logging configuration
from sqlalchemy import event
from sqlalchemy.pool import Pool

@event.listens_for(Pool, "connect")
def receive_connect(dbapi_conn, connection_record):
    logger.info(f"Database connection established")

@event.listens_for(Pool, "close")
def receive_close(dbapi_conn, connection_record):
    logger.info(f"Database connection closed")
```

Set alerts for:
- Connection pool exhaustion
- Slow queries (>1 second)
- Connection timeouts
- Disk space usage (critical at 85%+)

---

## Security Checklist

Review and complete all items before production deployment:

### Authentication & Secrets

- [ ] **SESSION_SECRET**: Generate with `openssl rand -base64 32`; **never use default or shared**
- [ ] **API Keys**: Store Spotify, OpenAI, and other keys in environment variables only
- [ ] **Database Credentials**: Use strong passwords (16+ characters, mixed case, numbers, symbols)
- [ ] **Rotation**: Rotate SESSION_SECRET and API keys every 90 days

### Network Security

- [ ] **CORS_ORIGINS**: Replace `*` with specific domains (e.g., `https://app.example.com`)
- [ ] **HTTPS/TLS**: Enable at load balancer or reverse proxy; use certificates from Let's Encrypt
- [ ] **Database SSL**: Enable SSL for database connections in production
  ```bash
  DATABASE_URL=postgresql://...?sslmode=require
  ```

### Access Control

- [ ] **Rate Limiting**: Implement on auth endpoints (`/api/auth/login`, `/api/auth/register`)
  ```python
  # Example: 10 login attempts per minute per IP
  from slowapi import Limiter
  @limiter.limit("10/minute")
  ```
- [ ] **Authentication**: Ensure all sensitive endpoints require JWT tokens
- [ ] **RBAC**: Implement role-based access control for admin functions

### Dependencies

- [ ] **Vulnerability Scan**: Run regularly
  ```bash
  pip install pip-audit
  pip-audit

  npm audit
  ```
- [ ] **Updates**: Monitor for security updates to FastAPI, SQLAlchemy, React, etc.
- [ ] **Lock Files**: Commit `uv.lock` and `package-lock.json` to version control

### Infrastructure

- [ ] **Secrets Management**: Use dedicated secrets management (Vault, AWS Secrets Manager, GitHub Secrets)
- [ ] **Database Backups**: Automated daily backups with encrypted storage
- [ ] **Firewall Rules**: Restrict database access to application servers only
- [ ] **SSH Keys**: Use ed25519 keys; disable password authentication
- [ ] **Monitoring**: Set up alerts for unusual activity (failed logins, resource exhaustion)

### Compliance

- [ ] **Logs**: Maintain audit logs for 90+ days
- [ ] **Data Privacy**: Review data storage and access policies
- [ ] **GDPR/CCPA**: Implement data export and deletion features if handling EU/CA users
- [ ] **PCI DSS**: If processing payments, follow PCI compliance guidelines

---

## Backup & Recovery

### Automated Backups

#### PostgreSQL Backup (Self-Hosted)

```bash
# Daily backup script (backup.sh)
#!/bin/bash
BACKUP_DIR="/backups/ampersound"
DATE=$(date +%Y-%m-%d_%H-%M-%S)

pg_dump -h localhost -U ampersound -d ampersound \
  --format=custom \
  --file=$BACKUP_DIR/ampersound_$DATE.dump

# Compress
gzip $BACKUP_DIR/ampersound_$DATE.dump

# Keep 30 days
find $BACKUP_DIR -type f -mtime +30 -delete

# Schedule with crontab
# 0 2 * * * /usr/local/bin/backup.sh
```

#### Managed Database Backups

Use automated backups provided by your service:

- **AWS RDS**: Automatic backups (35-day retention by default)
- **GCP Cloud SQL**: Automated daily backups
- **Supabase**: Automatic backups, point-in-time recovery

### File Upload Backups

If using S3 or GCS for uploads:

```bash
# Enable versioning (AWS S3)
aws s3api put-bucket-versioning \
  --bucket ampersound-uploads \
  --versioning-configuration Status=Enabled

# Or enable GCS versioning
gsutil versioning set on gs://ampersound-uploads/
```

### Recovery Procedures

#### Full Database Restore

```bash
# List available backups
ls -lh /backups/ampersound/

# Restore from backup (creates new database)
createdb ampersound_restore
gunzip < /backups/ampersound/ampersound_2026-02-08.dump.gz | \
  pg_restore --verbose --no-owner --no-privileges \
  --dbname=ampersound_restore

# Verify
psql ampersound_restore -c "SELECT COUNT(*) FROM \"Organization\";"

# Switch to restored database
ALTER DATABASE ampersound RENAME TO ampersound_backup;
ALTER DATABASE ampersound_restore RENAME TO ampersound;
```

#### Alembic Migration Rollback

If a migration causes issues:

```bash
# View migration history
alembic history

# Rollback one migration
alembic downgrade -1

# Rollback to specific revision
alembic downgrade 1234567890ab

# After fixing, reapply
alembic upgrade head
```

#### Point-in-Time Recovery

For managed services:

```bash
# AWS RDS
aws rds restore-db-instance-from-db-snapshot \
  --db-instance-identifier ampersound-restored \
  --db-snapshot-identifier ampersound-snapshot \
  --restore-time "2026-02-08T14:00:00Z"

# GCP Cloud SQL
gcloud sql backups restore --backup-instance=INSTANCE_ID BACKUP_ID
```

### Disaster Recovery Plan

1. **Detection**: Automated monitoring alerts detect issues
2. **Failover**: Switch to standby database (if configured)
3. **Restore**: Restore from most recent clean backup
4. **Verification**: Run data integrity checks
5. **Communication**: Notify users of recovery status
6. **Post-Mortem**: Document root cause and preventative measures

---

## Architecture Overview

### Technology Stack

**Frontend**
- React 18: Component-based UI framework
- Vite: Fast build tool for modern web development
- Tailwind CSS: Utility-first CSS framework
- Axios: HTTP client for API requests
- React Router: Client-side navigation

**Backend**
- FastAPI: Modern Python web framework for APIs
- SQLAlchemy: SQL toolkit and ORM
- Pydantic: Data validation and parsing
- Alembic: Database schema migrations
- Gunicorn: WSGI HTTP server (production)
- Uvicorn: ASGI server (development)

**Database**
- PostgreSQL 15: Relational database
- JSONB support for flexible data
- Full-text search capabilities
- Connection pooling with PgBouncer (optional)

**Authentication**
- JWT (JSON Web Tokens): Stateless authentication via `python-jose`
- Bcrypt: Password hashing with salt
- Token-based for API requests: `Authorization: Bearer <token>`

### Data Model

The application uses **multi-tenant architecture** with organization-scoped data isolation:

```
Organization
├── Users (admin, staff, readonly)
├── Creators
├── Songs
│   ├── Metadata (title, duration, genre)
│   ├── Credits (composer, lyricist, publisher)
│   └── Royalties (streaming, mechanical)
├── Contracts
├── Releases
└── Placements
```

Key design principles:
- Organizations are isolated; users can only access their organization's data
- All queries filtered by organization context
- Cascading deletes maintain referential integrity

### API Architecture

RESTful API design with routes organized by resource:

```
/api/auth               - Authentication (login, register, refresh)
/api/organizations      - Organization management
/api/creators           - Creator roster
/api/songs              - Song catalog and metadata
/api/credits            - Track credits and contributors
/api/contracts          - Contract management
/api/releases           - Release information
/api/placements         - Placement tracking
/api/royalties          - Royalty reporting
/api/valuations         - Valuation calculations
/api/analytics          - Dashboard and reporting
/api/schedule-a         - ASCAP Schedule A imports
/api/exports            - Data export in multiple formats
```

### Request Flow

```
Client Request
    ↓
[Load Balancer]
    ↓
[Frontend Assets] ← React/Vite build (index.html, assets)
    ↓
[API Route] ← FastAPI endpoint
    ↓
[Auth Middleware] ← JWT validation
    ↓
[Business Logic] ← Service layer
    ↓
[Database] ← SQLAlchemy + PostgreSQL
    ↓
Response (JSON)
```

### Deployment Diagram

```
User Browser
    ↓
[CDN / SSL Terminator]
    ↓
[Load Balancer]
    ├→ App Instance 1
    ├→ App Instance 2
    └→ App Instance 3
    ↓
[PostgreSQL Cluster]
    ├→ Primary (write)
    └→ Replicas (read-only analytics)
    ↓
[File Storage] (S3/GCS for uploads)
    ↓
[External APIs] (Spotify, OpenAI, Chartmetric)
```

---

## Additional Resources

- **Alembic Documentation**: https://alembic.sqlalchemy.org
- **FastAPI Documentation**: https://fastapi.tiangolo.com
- **Docker Documentation**: https://docs.docker.com
- **PostgreSQL Documentation**: https://www.postgresql.org/docs
- **React Documentation**: https://react.dev

---

## Support & Troubleshooting

### Common Issues

**Database Connection Refused**
```bash
# Check PostgreSQL is running
docker-compose ps | grep db

# Test connection
psql $DATABASE_URL -c "SELECT 1"
```

**Frontend Not Loading**
```bash
# Verify build artifacts exist
ls -la frontend/dist/

# Check static file mounting in backend
curl http://localhost:8000/assets/
```

**High Memory Usage**
```bash
# Check gunicorn worker count
# Reduce WEB_CONCURRENCY to match available RAM
WEB_CONCURRENCY=4  # Default: (cpu_count * 2) + 1
```

**Slow Queries**
```bash
# Enable SQL debug logging
SQL_DEBUG=true

# Check slow query log (PostgreSQL)
log_min_duration_statement = 1000  # Log queries > 1 second
```

For additional support, refer to individual service documentation or your hosting provider's support channels.
