import logging
import os
from pathlib import Path
import sys
from dotenv import load_dotenv

# Load environment variables from .env file FIRST before any other imports
load_dotenv()

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from api.validation import router as validation_router
from api.mcp import router as mcp_router
from api.matching import router as matching_router
from api.ideas import router as ideas_router
from api.agent import router as agent_router
from api.collaboration import router as collaboration_router  # Phase 4
from api.mentor import router as mentor_router  # Phase 4

app = FastAPI(
    title="Elevare Platform API",
    description="AI-powered startup validation and team building with autonomous agent support",
    version="2.0.0"
)

# CORS Configuration for Frontend Integration
# Allows frontend running on different origins (e.g., http://localhost:3000) to access the API
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:3001",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount routers
app.include_router(validation_router)
app.include_router(mcp_router)
app.include_router(matching_router)
app.include_router(ideas_router)
app.include_router(agent_router, prefix="/api/v1", tags=["Autonomous Agent v2.0"])
app.include_router(collaboration_router, prefix="/api/v1", tags=["Real-Time Collaboration"])  # Phase 4
app.include_router(mentor_router, prefix="/api/v1", tags=["AI Mentor"])  # Phase 4

# Initialize database - Import all models to register them with Base, then create tables
from db.database import Base, engine
from models.user_models import User, Skill

# In test runs, ensure a clean database to avoid flaky unique constraint failures
if os.getenv("PYTEST_CURRENT_TEST") or ("pytest" in sys.modules):
    try:
        Base.metadata.drop_all(bind=engine)
    except Exception:
        # Ignore drop errors in case tables don't exist yet
        pass
Base.metadata.create_all(bind=engine)

# Mount static files - Now using integrated templates and assets
static_dir = Path(__file__).parent / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")
    app.mount("/assets", StaticFiles(directory=str(static_dir)), name="assets")  # For Mini project compatibility

# Templates directory - Now using integrated templates from main project
templates_dir = Path(__file__).parent / "templates"
templates = Jinja2Templates(directory=str(templates_dir))

# Simple health & model info endpoint
@app.get("/healthz")
def healthz():
    from services.dimensional_analyzer import DimensionalAnalyzer
    active_model = None
    try:
        analyzer = DimensionalAnalyzer()
        # Do not invoke full analysis; just report candidate list & API key presence
        candidates = analyzer.candidate_models
        active_model = candidates[0] if candidates else None
    except Exception as e:
        return {"status": "error", "error": str(e)}
    return {"status": "ok", "active_model": active_model}

@app.get("/", response_class=HTMLResponse)
def root(request: Request):
    return templates.TemplateResponse(request=request, name="index.html")

@app.get("/login", response_class=HTMLResponse)
def login(request: Request):
    return templates.TemplateResponse(request=request, name="login.html")

@app.get("/intake", response_class=HTMLResponse)
def intake(request: Request):
    return templates.TemplateResponse(request=request, name="intake.html")

@app.get("/roadmap", response_class=HTMLResponse)
def roadmap(request: Request):
    return templates.TemplateResponse(request=request, name="roadmap.html")

@app.get("/dashboard", response_class=HTMLResponse)
def dashboard(request: Request):
    return templates.TemplateResponse(request=request, name="dashboard.html")

@app.get("/user", response_class=HTMLResponse)
def user(request: Request):
    return templates.TemplateResponse(request=request, name="user.html")

@app.get("/cofounder", response_class=HTMLResponse)
def cofounder(request: Request):
    return templates.TemplateResponse(request=request, name="cofounder.html")

@app.get("/cofounder-simple", response_class=HTMLResponse)
def cofounder_simple(request: Request):
    return templates.TemplateResponse(request=request, name="cofounder_simple.html")

@app.get("/profile-setup", response_class=HTMLResponse)
def profile_setup(request: Request):
    return templates.TemplateResponse(request=request, name="profile-setup.html")

@app.get("/features", response_class=HTMLResponse)
def features(request: Request):
    return templates.TemplateResponse(request=request, name="features.html")

@app.get("/events", response_class=HTMLResponse)
def events(request: Request):
    return templates.TemplateResponse(request=request, name="events.html")

@app.get("/mentorship", response_class=HTMLResponse)
def mentorship(request: Request):
    return templates.TemplateResponse(request=request, name="mentorship.html")

@app.get("/idea-wall", response_class=HTMLResponse)
def idea_wall(request: Request):
    return templates.TemplateResponse(request=request, name="idea-wall.html")

@app.get("/systems", response_class=HTMLResponse)
def systems(request: Request):
    return templates.TemplateResponse(request=request, name="systems.html")
