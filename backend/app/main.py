import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.database import engine, Base, SessionLocal
from app.auth import seed_default_moderator
from app.middleware import AnonymityAndSecurityMiddleware
from app.api import reports, auth, admin

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: ensure tables exist and default moderator is created
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        seed_default_moderator(db)
    finally:
        db.close()
    yield

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="""
# WhistleDrop Backend API
**Speak Without Being Seen** — A state-of-the-art anonymous whistleblower reporting platform.

## Key Capabilities:
* **True Anonymity & Zero-Knowledge Architecture**: No user registration, no sessions, no IP logging.
* **Cryptographic Case Tracking**: Unguessable high-entropy Case Codes (`WD-XXXX-XXXX-XXXX`).
* **AI Guardian**: Automated PII detection and redaction (names, emails, IDs, phone numbers).
* **Applied Machine Learning**:
  * TF-IDF + Naive Bayes categorization across GDG categories.
  * Three-tier confidence gating system.
  * Keyword + NLP triage urgency & severity scoring (`LOW`, `MEDIUM`, `HIGH`, `CRITICAL`).
  * Cosine similarity duplicate/related incident detection.
* **Strict State Transition Workflow**: `SUBMITTED` ➔ `UNDER_REVIEW` ➔ `RESOLVED` / `DISMISSED`.
    """,
    version=settings.VERSION,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)

# 1. CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 2. Anonymity, Privacy Headers & Ephemeral Rate Limiting Middleware
app.add_middleware(AnonymityAndSecurityMiddleware)

# 3. Mount Static Files
static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

# 4. Mount API Routers
app.include_router(reports.router, prefix=settings.API_PREFIX)
app.include_router(auth.router, prefix=settings.API_PREFIX)
app.include_router(admin.router, prefix=settings.API_PREFIX)

@app.get("/", tags=["Portal UI"], include_in_schema=False)
def serve_portal():
    index_path = os.path.join(static_dir, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"message": "WhistleDrop API is operational. Visit /docs for OpenAPI explorer."}

@app.get("/api/health", tags=["Health & Info"])
def health_check():
    return {
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "status": "healthy",
        "anonymity_mode": "STRICT_ZERO_KNOWLEDGE",
        "documentation": "/docs"
    }
