# Cadence — Deployment & Operations Runbook

> **Audience:** an engineer joining Cadence on day one. Reading
> this doc and clicking through the deployment URL should be
> enough to get fully operational within an hour.
>
> **Current host:** Replit Deployments. The doc is written so a
> future move to AWS / GCP changes only the bits called out in
> §6 (and zero application code).

## Contents
1. [Architecture overview](#1-architecture-overview)
2. [Environment variables](#2-environment-variables)
3. [First-time deploy](#3-first-time-deploy-replit)
4. [Routine operations](#4-routine-operations)
5. [Staging environment](#5-staging-environment)
6. [Migrating to AWS](#6-migrating-to-aws)
7. [Security checklist](#7-security-checklist)
8. [Future work](#8-future-work)

---

## 1. Architecture overview

```
                 ┌───────────────────────────────────────┐
                 │            Browser / Client           │
                 │  (React 18 SPA served from /)         │
                 └────────────────┬──────────────────────┘
                                  │  HTTPS (TLS terminated by Replit)
                                  ▼
              ┌────────────────────────────────────────────┐
              │  Replit Deployment URL                     │
              │  *.replit.app  (or custom CNAME)           │
              │  - mTLS proxy → app container              │
              │  - sets X-Forwarded-Proto: https           │
              └────────────────┬───────────────────────────┘
                               │  http://app:8000  (in-container)
                               ▼
        ┌────────────────────────────────────────────────────┐
        │  FastAPI app (uvicorn / gunicorn)                  │
        │  - backend/main.py                                 │
        │  - /api/*                routes                    │
        │  - /api/internal/*       staff endpoints           │
        │  - /api/internal/portal/* staff portal proxy       │
        │  - /docs /redoc /openapi (Basic Auth in prod)      │
        │  - /health               unauth liveness probe     │
        │  - APScheduler  (digest emails, chart fetch, etc.) │
        │  - serves built frontend/dist/ as static fallback  │
        └────────────────┬─────────────────┬─────────────────┘
                         │                 │
                         │ SQLAlchemy      │ Outbound
                         ▼                 ▼
              ┌──────────────────┐  ┌─────────────────────┐
              │  PostgreSQL 15   │  │  Third-party APIs   │
              │  (Replit-hosted) │  │  OpenAI · Resend ·  │
              │  one DB per env  │  │  Spotify · Dropbox ·│
              └──────────────────┘  │  YouTube · Last.fm  │
                                    └─────────────────────┘
```

### Service inventory

| Service                     | Purpose (one line)                                                |
|-----------------------------|-------------------------------------------------------------------|
| Replit Deployment           | Public HTTPS endpoint, TLS termination, autoscaling.              |
| FastAPI / uvicorn           | HTTP API + background scheduler + static frontend bundle.         |
| PostgreSQL (Replit)         | Single source of truth; one DB per environment.                   |
| Alembic                     | Schema migrations under `pg_advisory_lock` (see `db_setup.py`).   |
| APScheduler                 | In-process cron: email digests, chart ingestion, release flips.   |
| OpenAI (gpt-4o-mini)        | CSV column mapping, contract parsing, audio analysis, brief AI.   |
| Resend                      | Transactional email (welcome, digests, support, sharing).         |
| Spotify Web API             | Playlist import, track search, release lookup.                    |
| Dropbox API                 | Optional cloud-storage linking for audio assets.                  |
| YouTube Data API            | Chart ingestion (streaming intelligence).                         |
| Last.fm API                 | Chart ingestion (streaming intelligence).                         |
| Web Push (VAPID)            | Browser push notifications (PWA).                                 |

---

## 2. Environment variables

> Set these on Replit via **Tools → Secrets** (production
> deployment) or **Workspace → Secrets** (development). The
> backend reads them through `backend/utils/settings.py` whenever
> possible.

### Required

| Name              | Example / value                                       | Consumed by                                             |
|-------------------|-------------------------------------------------------|---------------------------------------------------------|
| `DATABASE_URL`    | `postgresql://user:pw@host:5432/cadence`              | SQLAlchemy engine, Alembic, every route.                |
| `SESSION_SECRET`  | `secret` (≥32 chars, random)                          | JWT signing (`backend/utils/auth.py`).                  |
| `APP_ENV`         | `development` \| `production`                         | CORS lockdown, HTTPS enforcement, error redaction.      |
| `CORS_ORIGINS`    | `https://app.cadence-ci.com,https://staff.cadence-ci.com` | CORS middleware. **Required in production.**        |

### Strongly recommended (production)

| Name                | Example / value                              | Consumed by                                       |
|---------------------|----------------------------------------------|---------------------------------------------------|
| `DOCS_USERNAME`     | `cadence-docs`                               | Basic Auth on `/docs`, `/redoc`, `/openapi.json`. |
| `DOCS_PASSWORD`     | `secret`                                     | Same — fail-closed if unset in prod.              |
| `LOG_FORMAT`        | `json`                                       | Structured logs (`backend/utils/logging_config`). |
| `LOG_LEVEL`         | `INFO`                                       | Root log level.                                   |
| `BUILD_VERSION`     | git SHA / release tag                        | Surfaced on `/health` and in `/docs` title.       |

### Optional integrations

| Name                              | Example          | Consumed by                                  |
|-----------------------------------|------------------|----------------------------------------------|
| `AI_INTEGRATIONS_OPENAI_API_KEY`  | `secret`         | All OpenAI-backed routes (CSV mapping, contract parser, audio analysis, brief builder, assistant chat, Schedule A extractor). Auto-set by the Replit OpenAI integration. |
| `AI_INTEGRATIONS_OPENAI_BASE_URL` | `secret`         | Same — OpenAI API base URL.                  |
| `RESEND_API_KEY`                  | `secret`         | Transactional email via Resend (auto-set by the Replit Resend integration). |
| `SPOTIFY_CLIENT_ID`               | `secret`         | Spotify integration — playlist import, search, release lookup. Rotated 2026-04-27 (Task #145) — see "Spotify rotation runbook" below for the always-do-both-halves procedure. |
| `SPOTIFY_CLIENT_SECRET`           | `secret`         | Spotify integration.                         |
| `DROPBOX_APP_KEY`                 | `secret`         | Cloud-storage linking (Dropbox audio scan).  |
| `DROPBOX_APP_SECRET`              | `secret`         | Cloud-storage linking.                       |
| `GOOGLE_CLIENT_ID`                | `secret`         | Cloud-storage linking (Google Drive audio scan). |
| `GOOGLE_CLIENT_SECRET`            | `secret`         | Cloud-storage linking (Google Drive).        |
| `YOUTUBE_API_KEY`                 | `secret`         | Chart ingestion (streaming intelligence).    |
| `LASTFM_API_KEY`                  | `secret`         | Chart ingestion (streaming intelligence).    |
| `CHARTMETRIC_API_KEY`             | `secret`         | Chartmetric streaming/chart data feed.       |
| `LUMINATE_API_KEY`                | `secret`         | Luminate (Nielsen) sales/streaming feed.     |
| `LUMINATE_API_SECRET`             | `secret`         | Luminate paired secret.                      |
| `CLAUDE_API_KEY`                  | `secret`         | Optional Claude AI provider (surfaced in `/settings` integration probe). |
| `VAPID_PRIVATE_KEY`               | `secret`         | Web Push (PWA push notifications).           |
| `VAPID_PUBLIC_KEY`                | `BLg…`           | Web Push (exposed to client).                |
| `VAPID_SUBJECT`                   | `mailto:support@cadence-ci.com` | Web Push subject for VAPID claims.|
| `STAGING_DATABASE_URL`            | postgres URL     | `scripts/seed_staging.py` (never read by app).|
| `LOG_RING_CAPACITY`               | `10000`          | In-process log ring buffer for `/internal/logs`.|
| `SQL_DEBUG`                       | `true`           | Enables SQLAlchemy DEBUG logging (very chatty — dev only). |
| `PORT`                            | `8000`           | Gunicorn bind port (ignored on Replit, which sets it). |

### Host-provided (do NOT set yourself)

These are populated by the Replit runtime / connector layer.
Listed here only so an operator who sees them in the env doesn't
mistake them for configuration knobs.

| Name                              | Source           | Notes                                        |
|-----------------------------------|------------------|----------------------------------------------|
| `REPL_IDENTITY`                   | Replit runtime   | Used by the Spotify / Resend connector clients to authenticate against Replit's connector proxy. |
| `WEB_REPL_RENEWAL`                | Replit runtime   | Same.                                        |
| `REPLIT_CONNECTORS_HOSTNAME`      | Replit runtime   | Same — connector proxy hostname.             |
| `REPLIT_DEPLOYMENT_ID`            | Replit deploy    | Fallback for `BUILD_VERSION` if unset.       |
| `REPL_SLUG`                       | Replit runtime   | Same — last-resort fallback for `BUILD_VERSION`. |
| `ALLOWED_ORIGINS`                 | legacy alias     | Read as a fallback for `CORS_ORIGINS`. Prefer `CORS_ORIGINS` in new deployments. |

Anything not listed in this section or the two preceding tables is
treated as "not configured" — the relevant integration falls
through to a clear error rather than a silent fallback. If you
add a new `os.getenv(...)` to backend code, append it here in the
same PR.

---

## 3. First-time deploy (Replit)

1. **Set secrets.** In the Replit workspace open **Tools →
   Secrets** and set everything from §2 marked *Required* plus
   `DOCS_USERNAME` / `DOCS_PASSWORD`. Set `APP_ENV=production`.
   Set `CORS_ORIGINS` to the exact origin your frontend will be
   served from (comma-separated if multiple).

2. **Provision the production database.** In Replit's
   **Database** tab create a new PostgreSQL DB. Replit
   auto-populates `DATABASE_URL`.

3. **Click Deploy.** Use the **Deploy** button in Replit and pick
   **Reserved VM** (recommended for the in-process scheduler) or
   **Autoscale** (acceptable; the scheduler runs only on the
   first instance). The build command is `bash run_backend.sh`,
   which runs `python -m backend.db_setup` (Alembic migrations
   under advisory lock) and then exec's uvicorn. **The deploy
   fails fast if migrations don't apply cleanly** — that is the
   intended behavior, not a bug.

4. **Verify health.** Once deployment finishes:
   ```bash
   curl https://<your-app>.replit.app/health
   # → {"status":"ok","db":"ok","version":"..."}
   ```
   If `db` is anything other than `ok`, do not promote traffic.

5. **Verify docs.** With Basic Auth credentials from step 1:
   ```bash
   curl -u "$DOCS_USERNAME:$DOCS_PASSWORD" \
     https://<your-app>.replit.app/openapi.json | jq '.info'
   ```
   Visit `/docs` in a browser and confirm the Swagger UI loads.

6. **Point your domain at the deployment.** In your DNS provider
   (Google Domains, Cloudflare, Route 53, etc.) create:
   ```
   Type:  CNAME
   Host:  app  (or @ if apex; use ALIAS at apex)
   Value: <your-app>.replit.app.
   TTL:   300
   ```
   Then in Replit **Deployments → Settings → Custom Domain**
   add `app.your-domain.com`. Replit issues an ACM-equivalent
   cert automatically; allow ~5 minutes for the TLS handshake to
   start succeeding.

---

## 4. Routine operations

### Provision a Cadence staff user
1. Sign in to `https://<your-app>/internal` as MasterPAdmin.
2. **Users → Provision staff user.** Supply username, email,
   initial password. The new user receives a welcome email via
   Resend and can immediately sign in to `/internal`.
3. To revoke, click **Deprovision** on their row. This flips
   `is_cadence_staff=False` AND revokes every active
   `UserSession`, cutting any in-flight JWT on the next request.

### Onboard a client organization
1. `/internal/onboarding`.
2. **Create organization** (name + type). The new org appears
   under **/internal/organizations** with an auto-generated
   8-char access code.
3. Share the access code with the client; they sign up at `/`
   and redeem the code during registration to land in the new
   org as OWNER. Use **Set custom code** if they prefer a
   memorable string, or **Rotate** to invalidate a leaked one.

### Run a migration manually
```bash
# in the Replit shell of a deployed instance, or in your local
# checkout pointing at the right DATABASE_URL
alembic current          # what revision is the DB on?
alembic history --verbose
alembic upgrade heads    # apply forward
alembic downgrade -1     # rollback one step (use with care)
```
Production startup runs `alembic upgrade heads` automatically
under a Postgres advisory lock (`pg_advisory_lock`), so multiple
instances starting simultaneously cannot race the migration.

### Schema parity check

A merge that lands a migration which diverges from
`backend/models/models.py` is the exact regression that Task #83
exposed (missing PK indexes, spurious DB defaults). To prevent the
next one slipping past code review:

```bash
DATABASE_URL=postgresql://… python scripts/check_schema_parity.py
```

The script:

1. Spins up two random Postgres schemas in the configured database
   (`parity_alembic_<rand>`, `parity_models_<rand>`); both are
   dropped on exit (success or failure), so it's safe to point at
   any environment, including production.
2. Bootstraps the first schema with `Base.metadata.create_all` and
   then applies every Alembic revision over the top, tolerating
   "already exists" overlaps from the bootstrap but treating any
   other failure (including divergent `ALTER COLUMN` errors) as
   drift.
3. Builds the second schema with `Base.metadata.create_all` alone.
4. Diffs the two via `sqlalchemy.inspect()` (table set, column
   names, nullability, types, primary keys, indexes) and exits 0
   on parity, 1 on drift, 2 on setup error.

It is wired into `scripts/post-merge.sh` (the post-merge hook that
runs after every task merge), so a divergent migration fails the
hook before reaching production. The same logic also runs as a
pytest case (`backend/tests/test_schema_parity.py`) for local dev,
where it auto-skips if `DATABASE_URL` isn't Postgres.

When the check fails, the report names every offending object —
reconcile by editing either the migration in `alembic/versions/`
or the model in `backend/models/models.py` and re-run.

### View logs
- **In-app:** `/internal/logs` shows the last 10k records from
  the in-process ring buffer (filter by level / since). Good for
  recent debugging.
- **Replit deploy logs:** the **Deployments** tab streams
  stdout/stderr from the container — used for boot failures,
  Alembic errors, and crashes.
- **Structured JSON logs:** set `LOG_FORMAT=json` in production
  so logs include `request_id`, `user_id`, `route`, `duration_ms`
  for downstream shipping.

### Browse the database (read-only)
1. `/internal/database` lists every table (only
   `alembic_version` is hidden).
2. Click a table to see paginated, per-column-filterable rows.
3. Use **Export CSV** for ad-hoc reporting. Every view + export
   is captured in the audit log (`INTERNAL_DB_VIEW`,
   `INTERNAL_DB_EXPORT`) with the actor's user id.

### Spotify rotation runbook

Whenever you change the Spotify account Cadence is using, you
must rotate **both halves** in the same session. Skipping
either half leaves Cadence in a half-broken state where some
flows still hit the old account.

**The two halves**

1. **Replit Spotify connection (OAuth)** — used by
   `_get_replit_access_token()` in
   `backend/services/spotify_service.py` for any flow tied to
   a logged-in listener (playlist import, release lookup,
   track auto-fill from a pasted Spotify URL).
2. **Developer-app fallback (`SPOTIFY_CLIENT_ID` /
   `SPOTIFY_CLIENT_SECRET` secrets)** — used by
   `_get_client_credentials_token()` for unauthenticated
   catalog/search calls (chart ingester, AI track matcher).

Replit Secrets are global, so updating these two secrets
covers both `development` and the Reserved VM `production`
deploy on its next restart — no separate prod-side secret
write is required.

**Procedure**

1. Create the new Spotify Developer app on
   [developer.spotify.com](https://developer.spotify.com).
   On the form: Redirect URI can be any well-formed URL
   (Cadence's client-credentials flow doesn't use it); check
   **Web API** only.
2. Update `SPOTIFY_CLIENT_ID` and `SPOTIFY_CLIENT_SECRET`
   secrets with the new dev app's values.
3. Re-trigger OAuth on the project's Spotify connection so
   the user signs in with the new listener account. The
   connector replaces its stored refresh token in place.
4. Restart the `backend` workflow in dev. Run an in-process
   smoke test calling
   `spotify_service.lookup_release_metadata()` against any
   known Spotify track URL — expect real metadata back, not a
   `SpotifyForbiddenError`.
5. Republish from the **Deployments** tab so the Reserved VM
   picks up the new secrets, then repeat the smoke test
   against the live URL.

**Spotify-side gates that block step 4** (both observed
verbatim during the 2026-04-27 rotation; if you hit either,
fix it on developer.spotify.com — no Cadence code change
needed):

- 403 *"Active premium subscription required for the owner of
  the app. When the subscription status changes, it can take
  a few hours before requests are allowed again."* — the
  Spotify account that **owns** the dev app must have an
  active Premium subscription. This blocks the
  client-credentials half.
- 403 *"Check settings on developer.spotify.com/dashboard,
  the user may not be registered."* — while the dev app is in
  Development Mode (the default for new apps), the listener
  account that signed in via OAuth must be added to the dev
  app's **Users and Access** list. This blocks the OAuth half.

The long-term fix for both is to apply for Spotify's
**Extended Quota Mode** review for the dev app, which removes
the Premium and allowlist requirements.

---

## 5. Staging environment

We keep staging completely separate from production at the
database layer — no cross-environment writes are possible.

1. **Provision a second Postgres.** Cheapest options:
   - Replit DB in a separate Repl
   - [Supabase](https://supabase.com) free tier
   - [Neon](https://neon.tech) free tier
2. **Capture its connection string** and export locally:
   ```bash
   export STAGING_DATABASE_URL=postgresql://user:pw@host:5432/cadence_staging
   ```
3. **Seed it:**
   ```bash
   python scripts/seed_staging.py
   ```
   The script:
   - refuses to run if `STAGING_DATABASE_URL` is unset
   - refuses to run if `STAGING_DATABASE_URL == DATABASE_URL`
     (defensive: don't seed prod by accident)
   - runs `alembic upgrade heads` against staging
   - idempotently creates a single `Cadence Sandbox` org with
     test users at every role, 5 creators, 20 songs, 2
     statements, 1 contract — every row name-prefixed
     `sandbox_` so an operator can scrub it with a single
     `WHERE name LIKE 'sandbox_%'`.
4. **Point a local app at it:**
   ```bash
   DATABASE_URL=$STAGING_DATABASE_URL APP_ENV=development \
     bash run_backend.sh
   ```
   Use the seeded usernames (`sandbox_owner`, `sandbox_admin`,
   `sandbox_member`, `sandbox_client`, password `Sandbox!234`)
   to exercise role-specific flows. (Roles map to the
   `OrganizationMemberRole` enum: OWNER / ADMIN / MEMBER / CLIENT —
   there is no READ_ONLY role today.)

---

## 6. Migrating to AWS

The application code is environment-agnostic — moving off Replit
changes ops, not code.

### What changes
| Change | How                                                                |
|--------|--------------------------------------------------------------------|
| `DATABASE_URL` | Point at RDS Postgres instance.                            |
| `CORS_ORIGINS` | Point at the new public hostname.                          |
| DNS            | Move CNAME from `*.replit.app` to the ALB DNS name.        |

### What does NOT change
- Any line of application code (`backend/`, `frontend/`).
- Any Alembic migration in `alembic/versions/`.
- The `/health`, `/docs`, `/internal/*` contracts.

### Recommended AWS topology
- **ECR** — image registry (push the reference Dockerfile).
- **ECS Fargate** — runs the container; 1 task minimum (the
  in-process scheduler must run on exactly one instance).
- **RDS Postgres 15** — managed DB, multi-AZ in production.
- **ALB** — TLS termination, sticky sessions not required.
- **ACM** — issues the ALB certificate.
- **Route 53** — DNS, ALIAS record at apex pointing at the ALB.
- **CloudWatch Logs** — wire `LOG_FORMAT=json` and ship.

### Reference Dockerfile
`Dockerfile` at the repo root is a multi-stage build:
1. `node:20-slim` builds the Vite frontend.
2. `python:3.11-slim` installs requirements, copies the built
   bundle, and runs `bash run_backend.sh` (which migrates and
   then exec's uvicorn).

It is **not used by the current Replit deploy** — it exists as
proof the app is containerizable, ready to drop into ECR.

```bash
docker build -t cadence:latest .
docker run --rm -p 8000:8000 \
  -e DATABASE_URL=postgresql://… \
  -e SESSION_SECRET=… \
  -e APP_ENV=production \
  -e CORS_ORIGINS=https://app.example.com \
  cadence:latest
```

---

## 7. Security checklist

Run through this at every production deploy. Each item is a
concrete pass/fail an operator can verify in <60 seconds.

- [ ] `APP_ENV=production` set on the deployment.
- [ ] `SESSION_SECRET` is ≥32 random chars and not the dev value.
- [ ] `CORS_ORIGINS` is set to an explicit allowlist (no `*`).
- [ ] `DOCS_USERNAME` + `DOCS_PASSWORD` set; visiting `/docs`
      anonymously returns 401, not 200.
- [ ] `curl https://…/health` returns 200 with `db: ok`.
- [ ] `curl http://…/health` (no S) is upgraded by the host or
      blocked by the HTTPS-enforcement middleware (X-Forwarded-Proto
      check is fail-closed for non-`/health` routes).
- [ ] Custom domain has a valid TLS cert (browser shows lock).
- [ ] No `print()` debug statements in production logs.
- [ ] Master admin password (`MasterPAdmin`) has been rotated
      from any default and stored only in Replit Secrets.
- [ ] At least one Cadence staff user exists in addition to
      MasterPAdmin (so a single account loss doesn't lock out the
      operator team).
- [ ] `/internal/users` shows no orphan `is_cadence_staff=true`
      users from prior personnel.
- [ ] Database backups confirmed in the host UI (Replit DB tab
      or RDS automated backups).

---

## 8. Future work

The infrastructure pass (Tasks #72–#77) intentionally left
several items as backlogs to be picked up incrementally as each
module is touched in normal feature work:

1. **OpenAPI summaries for the ~380 long-tail endpoints.** The
   top 100 routes have hand-written `summary=` /
   `description=`; the rest fall back to a name-synthesized
   summary. Backfill order is documented in
   `docs/openapi.json` review notes (and was the §6 backlog of
   the previous DEPLOYMENT.md stub).
2. **~~Drift items in `backend/db_setup.py`'s DDL backstop.~~**
   ✅ **COMPLETED — Task #83 (Apr 2026).** Every historical
   `ALTER TABLE` / `CREATE INDEX` / `CREATE TABLE` /
   data-backfill statement that previously lived in
   `ensure_schema_updates()` has been promoted into Alembic
   revision `d3e4f5a6b7c8`
   (`alembic/versions/d3e4f5a6b7c8_consolidate_ddl_drift_backstop.py`).
   The revision is written with Postgres-native idempotent
   constructs (`ADD COLUMN IF NOT EXISTS`, `CREATE INDEX IF NOT
   EXISTS`, `DO $$ ... $$` blocks) so it is a no-op on databases
   where the backstop had already applied the same DDL.
   `ensure_schema_updates()` is now a thin shim that logs a
   single deprecation notice per process and returns; it is kept
   (rather than deleted) as a placeholder for any future drift
   work. New schema changes must go through Alembic from now on
   — see §4 for the migration workflow.
3. **Real log shipper.** The in-process ring buffer powering
   `/internal/logs` is convenient for recent debugging but
   bounded to 10k records and lost on restart. For longer
   retention and cross-instance correlation, ship the structured
   JSON logs to CloudWatch / Datadog / Loki.
4. **Single-line Alembic history.** Multiple heads currently
   exist in `alembic/versions/`; merge them into a single linear
   history (already proposed as a project-task follow-up).
5. **Automated tests for `/api/internal/portal/*`.** The staff
   portal endpoints are exercised manually today; the proposed
   test follow-up will lock down auth gating + audit-write
   behavior.
