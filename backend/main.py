from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from jose import JWTError
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from .routes import (
    auth, catalog, settings,
    organizations, creators, songs, credits,
    checklist, exports, valuations, valuation_reports, schedule_a,
    contracts, contracts_mgmt, contract_docs, account_links, admin, notifications, actions, csv_upload,
    works, releases, bulk, spotify_import, royalties, placements, analytics,
    tenant_admin, creative_directory, registration_reports, audit_log, expenses,
    client_sharing, integrations, audio, brief_builder, royalty_processing,
    push, storage_scan, client_portal, account_merge, streaming_credits,
    document_sharing, support, assistant, schedule_a_imports, internal_dev
)
from .utils.logging_config import logger
from .utils.settings import (
    APP_ENV, IS_PRODUCTION, IS_DEVELOPMENT, BUILD_VERSION, parse_cors_origins,
)
from .utils.request_context import (
    set_request_id, set_route, request_id_var, user_id_var, org_id_var, route_var,
)
import os
import re
import time
import uuid
import logging
import traceback as tb_mod
from datetime import datetime, timezone
from pathlib import Path

if not os.getenv("SESSION_SECRET"):
    raise RuntimeError("SESSION_SECRET environment variable must be set for production use")

from .utils.docs_auth import require_docs_auth

# We disable the built-in /docs, /redoc, /openapi.json URLs and
# re-register them below with require_docs_auth as a dependency
# (Basic Auth in production, no-op in development). The FastAPI
# constructor's `dependencies=` argument does NOT apply to these
# built-in handlers, so wrapping them is the only way to gate them.
app = FastAPI(
    title="Cadence Catalog Intelligence API",
    description=(
        "Multi-tenant rights, royalty, and catalog administration "
        "platform for music publishers, labels, and managers. "
        "Endpoints are grouped by domain (Auth, Catalog, Royalties, "
        "Creators, Songs, Contracts, Placements, ...). All "
        "non-public endpoints require a Bearer JWT obtained from "
        "POST /api/auth/login."
    ),
    version=os.getenv("BUILD_VERSION", "1.0.0"),
    swagger_ui_parameters={"docExpansion": "none", "filter": True},
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
)


from fastapi.openapi.docs import get_redoc_html, get_swagger_ui_html
from fastapi.openapi.utils import get_openapi


@app.get("/openapi.json", include_in_schema=False)
def _openapi_json(_: None = Depends(require_docs_auth)):
    return get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )


@app.get("/docs", include_in_schema=False)
def _swagger_docs(_: None = Depends(require_docs_auth)):
    return get_swagger_ui_html(
        openapi_url="/openapi.json",
        title=f"{app.title} — Swagger UI",
        swagger_ui_parameters=app.swagger_ui_parameters,
    )


@app.get("/redoc", include_in_schema=False)
def _redoc_docs(_: None = Depends(require_docs_auth)):
    return get_redoc_html(
        openapi_url="/openapi.json",
        title=f"{app.title} — ReDoc",
    )


# --------------------------------------------------------------------------
# MODULE-LEVEL one-shot maintenance.
#
# This runs ONCE per process at import time, before any worker forks and
# before any request is served. It exists because we have repeatedly been
# burned by `@app.on_event("startup")` + `preload_app=True` in gunicorn:
# the startup event fires inside the master, the deferred-thread approach
# gets cut off when workers fork, and silent failures left every song's
# `status_health_score` stuck at 0 in production for hours. Module-level
# code is the only place that's GUARANTEED to execute on every gunicorn /
# uvicorn boot regardless of worker model. Wrapped in a broad try/except
# so a maintenance failure can't take down request serving.
# --------------------------------------------------------------------------
def _module_level_health_recompute():
    try:
        from .db_setup import seed_checklist_items, sync_stale_health_scores
        seed_checklist_items()
        sync_stale_health_scores()
        logger.info("module-level health recompute completed")
    except Exception as e:
        logger.error(f"module-level health recompute failed: {e}", exc_info=True)


_module_level_health_recompute()


@app.on_event("startup")
def startup_event():
    import threading
    threading.Thread(target=_deferred_startup_tasks, daemon=True).start()


def _deferred_startup_tasks():
    import traceback
    log = logging.getLogger("cadence")

    try:
        from .db_setup import seed_super_admin
        seed_super_admin()
    except Exception as e:
        log.warning(f"seed_super_admin failed at startup: {e}")

    # Internal developer tools (Task #89): create new tables, capture
    # deploy fingerprint, persist a deploy_event row, and warm the
    # runtime config cache.
    try:
        from .models.database import engine
        from .models.models import (
            RuntimeConfig, DeployEvent, SavedQuery, QueryHistoryEntry,
        )
        from sqlalchemy import inspect as _inspect
        _insp = _inspect(engine)
        _existing = set(_insp.get_table_names())
        for tbl in [
            RuntimeConfig.__table__, DeployEvent.__table__,
            SavedQuery.__table__, QueryHistoryEntry.__table__,
        ]:
            if tbl.name not in _existing:
                tbl.create(engine, checkfirst=True)
                log.info(f"Created table {tbl.name}")
    except Exception as e:
        log.warning(f"Internal-dev table creation failed: {e}")

    try:
        from .services import deploy_info, runtime_config
        deploy_info.capture()
        deploy_info.record_boot()
        runtime_config.warmup()
    except Exception as e:
        log.warning(f"Deploy/config startup failed: {e}")

    try:
        from .services.email_scheduler import start_scheduler
        start_scheduler()
    except Exception as e:
        log.warning(f"Email scheduler failed to start: {e}")

    try:
        from .db_setup import seed_checklist_items, sync_stale_health_scores
        seed_checklist_items()
        sync_stale_health_scores()
    except Exception:
        log.error(f"Checklist seed / health resync failed: {traceback.format_exc()}")

    _backfill_publishing_percentages(log, traceback)

    try:
        from .db_setup import sync_release_status
        sync_release_status()
    except Exception as e:
        log.warning(f"Release status sync failed: {e}")

    try:
        from .services import schedule_a_storage
        removed = schedule_a_storage.cleanup_stale_staged()
        if removed:
            log.info(f"Cleaned up {removed} stale staged Schedule A uploads")
    except Exception as e:
        log.warning(f"Staged Schedule A cleanup failed: {e}")

    log.info("Deferred startup tasks completed")


def _seed_checklist(log, traceback):
    changed = False
    try:
        from .models.database import SessionLocal, engine
        from .models.models import ChecklistItem, SongChecklistStatus
        from sqlalchemy import inspect
        inspector = inspect(engine)
        existing_tables = set(inspector.get_table_names())
        for tbl in [ChecklistItem.__table__, SongChecklistStatus.__table__]:
            if tbl.name not in existing_tables:
                tbl.create(engine, checkfirst=True)
                log.info(f"Created table {tbl.name}")
        db = SessionLocal()
        try:
            REMOVED_CODES = ["AD-01", "LG-01", "DSP-01", "DSP-02", "SY-02"]
            removed_items = db.query(ChecklistItem).filter(
                ChecklistItem.code.in_(REMOVED_CODES)
            ).all()
            if removed_items:
                removed_ids = [item.id for item in removed_items]
                db.query(SongChecklistStatus).filter(
                    SongChecklistStatus.checklist_item_id.in_(removed_ids)
                ).delete(synchronize_session=False)
                for item in removed_items:
                    db.delete(item)
                db.commit()
                changed = True
                log.info(f"Removed {len(removed_items)} deprecated checklist items")

            existing_count = db.query(ChecklistItem).count()
            if existing_count == 0:
                CHECKLIST_SEED = [
                    {"code": "AD-02", "category": "ADMIN", "description": "Contract executed/signed", "weight": 15},
                    {"code": "AD-03", "category": "ADMIN", "description": "Invoice submitted", "weight": 10},
                    {"code": "LG-02", "category": "LEGAL", "description": "Publishing splits confirmed", "weight": 10},
                    {"code": "MD-01", "category": "METADATA", "description": "ISRC assigned", "weight": 5},
                    {"code": "MD-02", "category": "METADATA", "description": "ISWC assigned", "weight": 5},
                    {"code": "MD-03", "category": "METADATA", "description": "Credits finalized", "weight": 5},
                    {"code": "DSP-03", "category": "DSP", "description": "Spotify link verified", "weight": 5},
                    {"code": "SY-01", "category": "SYNC", "description": "Registered with PRO", "weight": 10},
                    {"code": "SY-03", "category": "SYNC", "description": "MLC registered", "weight": 5},
                    {"code": "PY-01", "category": "PAYMENT", "description": "Payment received", "weight": 20},
                ]
                for item_data in CHECKLIST_SEED:
                    db.add(ChecklistItem(**item_data))
                db.commit()
                log.info(f"Seeded {len(CHECKLIST_SEED)} checklist items")
            else:
                missing_items = [
                    {"code": "SY-03", "category": "SYNC", "description": "MLC registered", "weight": 5},
                ]
                for item_data in missing_items:
                    exists = db.query(ChecklistItem).filter(ChecklistItem.code == item_data["code"]).first()
                    if not exists:
                        db.add(ChecklistItem(**item_data))
                        log.info(f"Added missing checklist item {item_data['code']}")
                db.commit()
        finally:
            db.close()
    except Exception:
        log.error(f"Checklist seed failed: {traceback.format_exc()}")
    return changed


def _resync_all_health_scores(log, traceback):
    try:
        from .models.database import SessionLocal
        from .utils.health_sync import sync_song_to_checklist
        from .models.models import Song
        db = SessionLocal()
        try:
            songs = db.query(Song).all()
            for song in songs:
                sync_song_to_checklist(db, song)
            db.commit()
            log.info(f"Resynced health scores for {len(songs)} songs")
        finally:
            db.close()
    except Exception:
        log.error(f"Health score resync failed: {traceback.format_exc()}")


def _backfill_publishing_percentages(log, traceback):
    try:
        from .models.database import SessionLocal
        from .models.models import Song, RightsSplit, ContractAsset
        from sqlalchemy import func as sqlfunc
        db = SessionLocal()
        try:
            song_pub_totals = db.query(
                ContractAsset.asset_id,
                sqlfunc.sum(RightsSplit.share_percentage)
            ).join(
                RightsSplit, RightsSplit.contract_asset_id == ContractAsset.id
            ).filter(
                ContractAsset.asset_type == "SONG",
                RightsSplit.rights_type == "PUBLISHING",
            ).group_by(ContractAsset.asset_id).all()

            updated = 0
            for song_id, total_pub in song_pub_totals:
                song = db.query(Song).filter(Song.id == song_id).first()
                if song and song.publishing_percentage != float(total_pub):
                    song.publishing_percentage = float(total_pub)
                    updated += 1

            if updated > 0:
                db.commit()
                log.info(f"Backfilled publishing_percentage for {updated} songs")
        finally:
            db.close()
    except Exception:
        log.error(f"Publishing percentage backfill failed: {traceback.format_exc()}")



@app.on_event("shutdown")
def shutdown_event():
    try:
        from .services.email_scheduler import shutdown_scheduler
        shutdown_scheduler()
    except Exception:
        pass

app_logger = logging.getLogger("cadence")

from starlette.types import ASGIApp, Receive, Scope, Send


class RequestContextMiddleware:
    """Generates a request_id, exposes it via ContextVar so downstream
    log calls inherit it, sets X-Request-ID on every response, and
    logs request start/end with duration_ms.

    Bypasses logging for noisy static asset paths so the ring buffer
    stays useful."""

    _SKIP_LOG_PREFIXES = ("/assets/", "/uploads/")
    _REQUEST_ID_PATTERN = re.compile(r"^[A-Za-z0-9_\-]{1,128}$")

    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        from starlette.requests import Request as _Req
        request = _Req(scope)
        path = request.url.path
        method = request.method

        incoming_id = request.headers.get("x-request-id")
        if incoming_id and self._REQUEST_ID_PATTERN.match(incoming_id):
            request_id = incoming_id
        else:
            request_id = uuid.uuid4().hex
        rid_token = request_id_var.set(request_id)
        rt_token = route_var.set(path)
        uid_token = user_id_var.set(None)
        oid_token = org_id_var.set(None)

        start = time.time()
        status_code = 0
        skip_log = any(path.startswith(p) for p in self._SKIP_LOG_PREFIXES)

        async def send_wrapper(message):
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message.get("status", 0)
                headers = list(message.get("headers", []))
                headers.append((b"x-request-id", request_id.encode("ascii")))
                message["headers"] = headers
            await send(message)

        if not skip_log:
            app_logger.info(
                f"{method} {path} started",
                extra={"method": method, "path": path},
            )

        try:
            await self.app(scope, receive, send_wrapper)
        finally:
            duration_ms = round((time.time() - start) * 1000, 2)
            if not skip_log:
                app_logger.info(
                    f"{method} {path} -> {status_code} ({duration_ms}ms)",
                    extra={
                        "method": method,
                        "path": path,
                        "status_code": status_code,
                        "duration_ms": duration_ms,
                    },
                )
            request_id_var.reset(rid_token)
            route_var.reset(rt_token)
            user_id_var.reset(uid_token)
            org_id_var.reset(oid_token)


class HTTPSEnforcementMiddleware:
    """In production, reject any request that arrived as plain HTTP.
    Replit's proxy terminates TLS and forwards the original scheme via
    X-Forwarded-Proto, so we trust that header rather than the raw
    scheme (which would be 'http' for every proxied request).

    Skipped for /health so internal probes can hit it over HTTP."""

    def __init__(self, app: ASGIApp):
        self.app = app

    _HEALTH_PATHS = ("/health", "/api/health")

    async def __call__(self, scope: Scope, receive: Receive, send: Send):
        if scope["type"] != "http" or not IS_PRODUCTION:
            await self.app(scope, receive, send)
            return

        path = scope.get("path", "")
        if any(path == p or path.startswith(p + "/") for p in self._HEALTH_PATHS):
            await self.app(scope, receive, send)
            return

        proto = None
        for name, value in scope.get("headers", []):
            if name == b"x-forwarded-proto":
                proto = value.decode("latin-1").split(",")[0].strip().lower()
                break

        # Fail-closed: if the proto header is missing in production, we
        # cannot prove the request arrived over TLS. Reject rather than
        # assume HTTPS. (Replit's proxy always sets this header.)
        if proto != "https":
            response = JSONResponse(
                {"error": "HTTPS required", "request_id": request_id_var.get()},
                status_code=426,
            )
            await response(scope, receive, send)
            return

        await self.app(scope, receive, send)


cors_origins = parse_cors_origins()
if IS_PRODUCTION and ("*" in cors_origins or not cors_origins):
    app_logger.warning(
        "APP_ENV=production but CORS origins are not locked down "
        f"(got {cors_origins!r}). Set CORS_ORIGINS to an explicit "
        "comma-separated list of allowed origins."
    )
    if "*" in cors_origins:
        cors_origins = [o for o in cors_origins if o != "*"]

app_logger.info(
    f"Starting Cadence API: env={APP_ENV} build={BUILD_VERSION} "
    f"cors_origins={cors_origins or '(none)'}"
)

# Middleware stack (Starlette runs LAST-ADDED first / outermost):
#   1. RequestContextMiddleware (outermost) — sets request_id BEFORE
#      anything else and injects X-Request-ID into every response,
#      including 426s rejected by the HTTPS middleware below.
#   2. CORSMiddleware (middle) — wraps the app so CORS headers are
#      attached to error responses too.
#   3. HTTPSEnforcementMiddleware (innermost) — short-circuits with
#      a 426 in production when X-Forwarded-Proto isn't https. The
#      rejection still passes back through RequestContext, so the
#      response carries X-Request-ID.
app.add_middleware(HTTPSEnforcementMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID"],
)
app.add_middleware(RequestContextMiddleware)


@app.exception_handler(SQLAlchemyError)
async def sqlalchemy_exception_handler(request: Request, exc: SQLAlchemyError):
    app_logger.error(
        f"Database error on {request.method} {request.url.path}: {exc}",
        exc_info=True,
    )
    body = {"error": "Database error", "request_id": request_id_var.get()}
    if IS_DEVELOPMENT:
        body["detail"] = str(exc)
    return JSONResponse(body, status_code=503)


@app.exception_handler(JWTError)
async def jwt_exception_handler(request: Request, exc: JWTError):
    return JSONResponse(
        {
            "error": "Invalid or expired token",
            "request_id": request_id_var.get(),
        },
        status_code=401,
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    app_logger.error(
        f"Unhandled exception on {request.method} {request.url.path}: {exc}",
        exc_info=True,
    )
    if IS_PRODUCTION:
        body = {
            "error": "An unexpected error occurred",
            "request_id": request_id_var.get(),
        }
    else:
        body = {
            "error": "An unexpected error occurred",
            "request_id": request_id_var.get(),
            "detail": str(exc),
            "traceback": tb_mod.format_exception(type(exc), exc, exc.__traceback__),
        }
    return JSONResponse(body, status_code=500)


@app.get("/")
async def serve_root(request: Request):
    accept = request.headers.get("accept", "")
    if "text/html" not in accept:
        return JSONResponse({"status": "healthy", "service": "Cadence Catalog Intelligence"})
    frontend_dist = Path(__file__).parent.parent / "frontend" / "dist"
    index_file = frontend_dist / "index.html"
    if index_file.exists():
        return FileResponse(index_file, headers={"Cache-Control": "no-cache, no-store, must-revalidate"})
    return JSONResponse({"status": "healthy", "service": "Cadence Catalog Intelligence"})


def _check_db_connectivity() -> str:
    """Run SELECT 1 against the primary database. Returns 'connected'
    or 'unreachable'. Never raises."""
    try:
        from .models.database import engine
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return "connected"
    except Exception as e:
        app_logger.warning(f"Health check DB probe failed: {e}")
        return "unreachable"


@app.get("/health", tags=["Infrastructure"], summary="Liveness + DB connectivity probe")
def health_root():
    """Unauthenticated health endpoint for uptime monitors and load
    balancer probes. Reports real DB connectivity (executes SELECT 1)."""
    db_status = _check_db_connectivity()
    return {
        "status": "ok" if db_status == "connected" else "degraded",
        "version": BUILD_VERSION,
        "env": APP_ENV,
        "db": db_status,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/api/health", tags=["Infrastructure"], summary="Legacy health endpoint")
def health_check():
    """Legacy alias of /health kept for backward compatibility with
    existing frontend probes."""
    return health_root()

app.include_router(auth.router)
app.include_router(catalog.router)
app.include_router(settings.router)
app.include_router(organizations.router)
app.include_router(creators.router)
app.include_router(songs.router)
app.include_router(credits.router)
app.include_router(checklist.router)
app.include_router(exports.router)
app.include_router(valuations.router)
app.include_router(valuation_reports.router)
app.include_router(schedule_a.router)
app.include_router(contracts.router)
app.include_router(contracts_mgmt.router)
app.include_router(contract_docs.router)
app.include_router(account_links.router)
app.include_router(admin.router)
app.include_router(admin.internal_router)
from .routes import internal as internal_routes
app.include_router(internal_routes.router)
from .routes import internal_portal
app.include_router(internal_portal.router)
app.include_router(internal_dev.router)
app.include_router(notifications.router)
app.include_router(actions.router)
app.include_router(csv_upload.router)
app.include_router(works.router)
app.include_router(releases.router)
app.include_router(bulk.router)
app.include_router(spotify_import.router)
app.include_router(royalties.router)
app.include_router(placements.router)
app.include_router(analytics.router)
app.include_router(tenant_admin.router)
app.include_router(creative_directory.router)
app.include_router(creative_directory.public_router)
app.include_router(registration_reports.router)
app.include_router(audit_log.router)
app.include_router(expenses.router)
app.include_router(client_sharing.router)
app.include_router(integrations.router)
app.include_router(audio.router)
app.include_router(brief_builder.router)
app.include_router(royalty_processing.router)
app.include_router(push.router)
app.include_router(storage_scan.router)
app.include_router(client_portal.router)
app.include_router(account_merge.router)
app.include_router(account_merge.admin_router)
app.include_router(streaming_credits.router)
app.include_router(streaming_credits.public_router)
app.include_router(streaming_credits.admin_chart_router)
app.include_router(document_sharing.router)
app.include_router(support.router)
app.include_router(assistant.router)
app.include_router(schedule_a_imports.router)

from .routes import leads
app.include_router(leads.router)
app.include_router(leads.admin_router)

# Synthesize a one-line summary on every route that doesn't already
# have a hand-written one so /docs and /redoc are scannable instead
# of being 482 bare function names. Run inside a startup hook so the
# route table is fully assembled before we walk it.
from .utils.openapi_backfill import backfill_route_summaries


@app.on_event("startup")
def _backfill_openapi_summaries():
    backfill_route_summaries(app)

uploads_dir = Path(__file__).parent / "uploads"
uploads_dir.mkdir(parents=True, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=str(uploads_dir)), name="uploads")

frontend_dist = Path(__file__).parent.parent / "frontend" / "dist"
if frontend_dist.exists() and (frontend_dist / "assets").exists():
    app.mount("/assets", StaticFiles(directory=str(frontend_dist / "assets")), name="assets")

@app.get("/{full_path:path}")
async def serve_spa(full_path: str):
    if full_path.startswith("api/"):
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Not found")

    dist = Path(__file__).parent.parent / "frontend" / "dist"
    if not dist.exists():
        return JSONResponse({"error": "Not found"}, status_code=404)

    try:
        requested_path = (dist / full_path).resolve()
        dist_resolved = dist.resolve()

        if not requested_path.is_relative_to(dist_resolved):
            return FileResponse(dist / "index.html", headers={"Cache-Control": "no-cache, no-store, must-revalidate"})

        if requested_path.is_file():
            if full_path.startswith("assets/"):
                return FileResponse(requested_path, headers={"Cache-Control": "public, max-age=31536000, immutable"})
            return FileResponse(requested_path, headers={"Cache-Control": "no-cache, no-store, must-revalidate"})
    except (ValueError, RuntimeError):
        pass

    return FileResponse(dist / "index.html", headers={"Cache-Control": "no-cache, no-store, must-revalidate"})


if __name__ == "__main__":
    from .db_setup import main as db_setup_main
    db_setup_main()
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
