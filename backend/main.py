from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from .models import Base, engine
from .routes import (
    auth, catalog, settings,
    organizations, creators, songs, credits,
    checklist, exports, valuations, valuation_reports, schedule_a,
    contracts, account_links, admin, notifications, actions, csv_upload
)
import os
from pathlib import Path

if not os.getenv("SESSION_SECRET"):
    raise RuntimeError("SESSION_SECRET environment variable must be set for production use")

app = FastAPI(title="Gotcha Catalog Manager API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
app.include_router(account_links.router)
app.include_router(admin.router)
app.include_router(notifications.router)
app.include_router(actions.router)
app.include_router(csv_upload.router)

@app.get("/api/health")
def health_check():
    return {"status": "healthy", "service": "Gotcha Catalog Manager"}

# Serve static files from frontend build (production)
frontend_dist = Path(__file__).parent.parent / "frontend" / "dist"
if frontend_dist.exists():
    app.mount("/assets", StaticFiles(directory=str(frontend_dist / "assets")), name="assets")
    
    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        """Serve the React SPA for all non-API routes"""
        # Skip API routes
        if full_path.startswith("api/"):
            from fastapi import HTTPException
            raise HTTPException(status_code=404, detail="Not found")
        
        # Sanitize path to prevent directory traversal
        try:
            # Resolve the requested path and ensure it's within frontend_dist
            requested_path = (frontend_dist / full_path).resolve()
            frontend_dist_resolved = frontend_dist.resolve()
            
            # Security check: ensure resolved path is within frontend_dist using is_relative_to
            if not requested_path.is_relative_to(frontend_dist_resolved):
                # Path traversal attempt detected - serve index.html for SPA routing
                return FileResponse(frontend_dist / "index.html")
            
            # Try to serve static file if it exists
            if requested_path.is_file():
                return FileResponse(requested_path)
        except (ValueError, RuntimeError):
            # Invalid path, serve index.html
            pass
        
        # Otherwise serve index.html (SPA routing)
        return FileResponse(frontend_dist / "index.html")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
