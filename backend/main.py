from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from .models import Base, engine
from .routes import auth, catalog, settings
import os

if not os.getenv("SESSION_SECRET"):
    raise RuntimeError("SESSION_SECRET environment variable must be set for production use")

app = FastAPI(title="MIME Catalog Intelligence API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

Base.metadata.create_all(bind=engine)

app.include_router(auth.router)
app.include_router(catalog.router)
app.include_router(settings.router)

@app.get("/api/health")
def health_check():
    return {"status": "healthy", "service": "MIME Catalog Intelligence"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
