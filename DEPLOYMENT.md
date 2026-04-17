# Cadence Deployment Guide

> Operational runbook for the Cadence Catalog Intelligence platform.
>
> **Status:** Stub — full content is delivered in Task #77.
> This file exists today to anchor the OpenAPI documentation
> backlog (item 6 below) referenced by Task #75.

## 1. Environments
TBD (Task #77).

## 2. Required environment variables
TBD (Task #77). At minimum:
- `DATABASE_URL`
- `SESSION_SECRET`
- `APP_ENV` (`development` | `production`)
- `CORS_ORIGINS` (comma-separated, required in production)
- `DOCS_USERNAME`, `DOCS_PASSWORD` — Basic Auth for `/docs`,
  `/redoc`, `/openapi.json` in production. If unset, the docs
  endpoints fail closed with HTTP 503.

## 3. First-time deploy
TBD (Task #77).

## 4. Database migrations
TBD (Task #77). Owned by Task #73 / #78 — see Alembic config in
`alembic.ini`.

## 5. Health checks & observability
TBD (Task #77). `GET /health` is the unauth liveness probe and
returns real DB connectivity.

## 6. Incremental OpenAPI documentation backlog
Task #75 shipped:
- Per-router `tags=["<Domain>"]` on every route module so
  `/docs` and `/redoc` group endpoints by domain.
- A startup helper (`backend/utils/openapi_backfill.py`) that
  synthesizes a `summary=` from the endpoint function name on
  every route that doesn't already have a hand-written one.
- Hand-written `summary=` + `description=` on the **top ~100
  highest-traffic** routes (auth, organizations, creators,
  songs, contracts, royalties, placements, releases, works,
  credits).
- Production HTTP Basic Auth on `/docs`, `/redoc`,
  `/openapi.json` (dev keeps them open).
- `scripts/export_openapi.py` writes the current schema to
  `docs/openapi.json` so PR reviewers can diff it.

The remaining ~380 routes still rely on the auto-synthesized
summaries. They are scannable but not as informative as the
hand-written ones. **Backfilling hand-written summaries +
descriptions for the long tail is an incremental backlog**
done module-by-module as each module is touched in normal
feature work. Order of priority when picking up the backlog:

1. `routes/contracts_mgmt.py` (Rights Management)
2. `routes/royalty_processing.py`
3. `routes/schedule_a.py`, `routes/schedule_a_imports.py`
4. `routes/audio.py`, `routes/brief_builder.py`
5. `routes/notifications.py`, `routes/actions.py`
6. `routes/client_portal.py`, `routes/client_sharing.py`
7. `routes/creative_directory.py`
8. `routes/audit_log.py`, `routes/admin.py`,
   `routes/tenant_admin.py`, `routes/internal.py`
9. Everything else.

After each batch, re-run `python scripts/export_openapi.py` so
`docs/openapi.json` stays current and PR diffs surface schema
changes.

## 7. Rollback
TBD (Task #77).
