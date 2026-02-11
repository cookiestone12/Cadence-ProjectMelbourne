from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from .models import Base, engine
from .routes import (
    auth, catalog, settings,
    organizations, creators, songs, credits,
    checklist, exports, valuations, valuation_reports, schedule_a,
    contracts, contracts_mgmt, account_links, admin, notifications, actions, csv_upload,
    works, releases, bulk, spotify_import, royalties, placements, analytics,
    tenant_admin
)
from .utils.logging_config import logger
from .models.database import SessionLocal
from .models.models import User
import os
import time
import uuid
import logging
from pathlib import Path

if not os.getenv("SESSION_SECRET"):
    raise RuntimeError("SESSION_SECRET environment variable must be set for production use")

Base.metadata.create_all(bind=engine)

def ensure_schema_updates():
    from sqlalchemy import text, inspect
    with engine.connect() as conn:
        inspector = inspect(engine)
        cols = [c['name'] for c in inspector.get_columns('creators')]
        if 'hero_image_data' not in cols:
            conn.execute(text("ALTER TABLE creators ADD COLUMN hero_image_data BYTEA"))
            conn.commit()
            logger.info("Added hero_image_data column to creators")
        if 'hero_image_mime' not in cols:
            conn.execute(text("ALTER TABLE creators ADD COLUMN hero_image_mime VARCHAR"))
            conn.commit()
            logger.info("Added hero_image_mime column to creators")

        song_cols = {c['name']: c for c in inspector.get_columns('songs')}
        bool_to_string_fields = ['is_paid', 'is_invoiced', 'is_registered_with_dsp']
        for field in bool_to_string_fields:
            if field in song_cols:
                col_type = str(song_cols[field]['type'])
                if 'BOOLEAN' in col_type.upper() or 'BOOL' in col_type.upper():
                    conn.execute(text(f"""
                        ALTER TABLE songs ALTER COLUMN {field} TYPE VARCHAR
                        USING CASE
                            WHEN {field} = true THEN 'Yes'
                            WHEN {field} = false THEN 'No'
                            ELSE 'No'
                        END
                    """))
                    conn.execute(text(f"ALTER TABLE songs ALTER COLUMN {field} SET DEFAULT 'No'"))
                    conn.commit()
                    logger.info(f"Converted songs.{field} from BOOLEAN to VARCHAR")

try:
    ensure_schema_updates()
except Exception as e:
    logger.warning(f"Schema update check: {e}")

def seed_super_admin():
    from .utils.auth import get_password_hash
    from .models.models import Organization, OrganizationMember
    db = SessionLocal()
    try:
        from sqlalchemy import func
        existing = db.query(User).filter(func.lower(User.username) == 'masterpadmin').first()
        if not existing:
            admin = User(
                username='MasterPAdmin',
                email='admin@rythm.app',
                hashed_password=get_password_hash('Male50Cent!'),
                is_admin=True,
                is_super_admin=True,
            )
            db.add(admin)
            db.commit()
            db.refresh(admin)
            logger.info("MasterPAdmin super admin account created")
            existing = admin

        if existing:
            has_membership = db.query(OrganizationMember).filter(
                OrganizationMember.user_id == existing.id
            ).first()
            if not has_membership:
                first_org = db.query(Organization).order_by(Organization.id).first()
                if not first_org:
                    first_org = Organization(
                        name="Rythm",
                        display_name="Rythm",
                        type="LABEL",
                        account_type="ENTERPRISE",
                    )
                    db.add(first_org)
                    db.commit()
                    db.refresh(first_org)
                    logger.info(f"Created default organization '{first_org.name}'")
                membership = OrganizationMember(
                    organization_id=first_org.id,
                    user_id=existing.id,
                    role="OWNER"
                )
                db.add(membership)
                db.commit()
                logger.info(f"Added MasterPAdmin to organization '{first_org.name}' as OWNER")
    except Exception as e:
        db.rollback()
        logger.error(f"Error seeding super admin: {e}")
    finally:
        db.close()

seed_super_admin()

app = FastAPI(title="Rythm Catalog Intelligence API")

allowed_origins = os.getenv("CORS_ORIGINS", "*").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app_logger = logging.getLogger("rythm")

@app.middleware("http")
async def logging_middleware(request, call_next):
    request_id = str(uuid.uuid4())[:8]
    start = time.time()
    response = await call_next(request)
    duration = round((time.time() - start) * 1000, 2)
    if not request.url.path.startswith("/assets"):
        app_logger.info(
            f"{request.method} {request.url.path} -> {response.status_code} ({duration}ms)",
            extra={"request_id": request_id}
        )
    return response

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

@app.get("/api/health")
def health_check():
    return {"status": "healthy", "service": "Rythm Catalog Intelligence"}

uploads_dir = Path(__file__).parent / "uploads"
uploads_dir.mkdir(parents=True, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=str(uploads_dir)), name="uploads")

# Serve static files from frontend build (production)
frontend_dist = Path(__file__).parent.parent / "frontend" / "dist"
if frontend_dist.exists():
    app.mount("/assets", StaticFiles(directory=str(frontend_dist / "assets")), name="assets")
    
    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        """Serve the React SPA for all non-API routes"""
        from fastapi.responses import Response
        
        if full_path.startswith("api/"):
            from fastapi import HTTPException
            raise HTTPException(status_code=404, detail="Not found")
        
        try:
            requested_path = (frontend_dist / full_path).resolve()
            frontend_dist_resolved = frontend_dist.resolve()
            
            if not requested_path.is_relative_to(frontend_dist_resolved):
                return FileResponse(frontend_dist / "index.html", headers={"Cache-Control": "no-cache, no-store, must-revalidate"})
            
            if requested_path.is_file():
                if full_path.startswith("assets/"):
                    return FileResponse(requested_path, headers={"Cache-Control": "public, max-age=31536000, immutable"})
                return FileResponse(requested_path, headers={"Cache-Control": "no-cache, no-store, must-revalidate"})
        except (ValueError, RuntimeError):
            pass
        
        return FileResponse(frontend_dist / "index.html", headers={"Cache-Control": "no-cache, no-store, must-revalidate"})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
