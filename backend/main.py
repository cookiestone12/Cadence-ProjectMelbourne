from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from .routes import (
    auth, catalog, settings,
    organizations, creators, songs, credits,
    checklist, exports, valuations, valuation_reports, schedule_a,
    contracts, contracts_mgmt, contract_docs, account_links, admin, notifications, actions, csv_upload,
    works, releases, bulk, spotify_import, royalties, placements, analytics,
    tenant_admin, creative_directory, registration_reports, audit_log, expenses,
    client_sharing, integrations, audio, brief_builder, royalty_processing,
    push, storage_scan, client_portal, account_merge, streaming_credits,
    document_sharing, support, assistant
)
from .utils.logging_config import logger
import os
import time
import uuid
import logging
from pathlib import Path

if not os.getenv("SESSION_SECRET"):
    raise RuntimeError("SESSION_SECRET environment variable must be set for production use")

app = FastAPI(title="Cadence Catalog Intelligence API")


@app.on_event("startup")
def startup_event():
    try:
        from .services.email_scheduler import start_scheduler
        start_scheduler()
    except Exception as e:
        logging.getLogger("cadence").warning(f"Email scheduler failed to start: {e}")

    import threading
    def _deferred_health_sync():
        log = logging.getLogger("cadence")
        try:
            from .models.database import engine, SessionLocal
            from .models.models import ChecklistItem, Song, SongChecklistStatus
            from sqlalchemy import inspect
            inspector = inspect(engine)
            existing_tables = inspector.get_table_names()
            tables_to_create = []
            if "checklist_items" not in existing_tables:
                tables_to_create.append(ChecklistItem.__table__)
            if "song_checklist_statuses" not in existing_tables:
                tables_to_create.append(SongChecklistStatus.__table__)
            if tables_to_create:
                from .models.models import Base
                Base.metadata.create_all(engine, tables=tables_to_create)
                log.info(f"Created missing tables: {[t.name for t in tables_to_create]}")
            db = SessionLocal()
            try:
                existing_codes = {item.code for item in db.query(ChecklistItem).all()}
                CHECKLIST_SEED = [
                    {"code": "AD-01", "category": "ADMIN", "description": "Contract sent to placement partner", "weight": 10},
                    {"code": "AD-02", "category": "ADMIN", "description": "Contract executed/signed", "weight": 15},
                    {"code": "AD-03", "category": "ADMIN", "description": "Invoice submitted", "weight": 10},
                    {"code": "LG-01", "category": "LEGAL", "description": "Rights clearance completed", "weight": 15},
                    {"code": "LG-02", "category": "LEGAL", "description": "Publishing splits confirmed", "weight": 10},
                    {"code": "MD-01", "category": "METADATA", "description": "ISRC assigned", "weight": 5},
                    {"code": "MD-02", "category": "METADATA", "description": "ISWC assigned", "weight": 5},
                    {"code": "MD-03", "category": "METADATA", "description": "Credits finalized", "weight": 5},
                    {"code": "DSP-01", "category": "DSP", "description": "Registered with DSPs", "weight": 10},
                    {"code": "DSP-02", "category": "DSP", "description": "Apple Music link verified", "weight": 5},
                    {"code": "DSP-03", "category": "DSP", "description": "Spotify link verified", "weight": 5},
                    {"code": "SY-01", "category": "SYNC", "description": "Registered with PRO", "weight": 10},
                    {"code": "SY-02", "category": "SYNC", "description": "Publisher notified", "weight": 5},
                    {"code": "PY-01", "category": "PAYMENT", "description": "Payment received", "weight": 20},
                ]
                added = 0
                for item_data in CHECKLIST_SEED:
                    if item_data["code"] not in existing_codes:
                        db.add(ChecklistItem(**item_data))
                        added += 1
                if added:
                    db.commit()
                    log.info(f"Seeded {added} checklist items")

                stale_songs = db.query(Song).filter(
                    (Song.status_health_score == None) | (Song.status_health_score == 0.0)
                ).all()
                if not stale_songs:
                    log.info("Health sync: no stale songs")
                    return

                from .utils.health_sync import sync_song_to_checklist
                all_items = db.query(ChecklistItem).all()
                for song in stale_songs:
                    has_statuses = db.query(SongChecklistStatus).filter(
                        SongChecklistStatus.song_id == song.id
                    ).first()
                    if not has_statuses:
                        for item in all_items:
                            db.add(SongChecklistStatus(
                                song_id=song.id,
                                checklist_item_id=item.id,
                                status="NOT_STARTED"
                            ))
                        db.flush()
                    sync_song_to_checklist(db, song)
                db.commit()
                log.info(f"Health sync: {len(stale_songs)} songs updated")
            finally:
                db.close()
        except Exception as e:
            logging.getLogger("cadence").warning(f"Health sync failed: {e}")
    threading.Thread(target=_deferred_health_sync, daemon=True).start()



@app.on_event("shutdown")
def shutdown_event():
    try:
        from .services.email_scheduler import shutdown_scheduler
        shutdown_scheduler()
    except Exception:
        pass

allowed_origins = os.getenv("CORS_ORIGINS", "*").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app_logger = logging.getLogger("cadence")

from starlette.types import ASGIApp, Receive, Scope, Send

class LoggingMiddleware:
    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        from starlette.requests import Request
        request = Request(scope)
        request_id = str(uuid.uuid4())[:8]
        start = time.time()
        status_code = 0

        async def send_wrapper(message):
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message.get("status", 0)
            await send(message)

        await self.app(scope, receive, send_wrapper)

        duration = round((time.time() - start) * 1000, 2)
        if not request.url.path.startswith("/assets"):
            app_logger.info(
                f"{request.method} {request.url.path} -> {status_code} ({duration}ms)",
                extra={"request_id": request_id}
            )

app.add_middleware(LoggingMiddleware)

@app.get("/")
async def serve_root():
    frontend_dist = Path(__file__).parent.parent / "frontend" / "dist"
    index_file = frontend_dist / "index.html"
    if index_file.exists():
        return FileResponse(index_file, headers={"Cache-Control": "no-cache, no-store, must-revalidate"})
    return JSONResponse({"status": "healthy", "service": "Cadence Catalog Intelligence"})

@app.get("/api/health")
def health_check():
    return {"status": "healthy", "service": "Cadence Catalog Intelligence"}

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
