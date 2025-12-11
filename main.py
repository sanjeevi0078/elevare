"""
Elevare Platform - Main Application Entry Point
Enterprise-grade FastAPI application with comprehensive middleware, logging, and error handling.
"""

import os
import sys
from pathlib import Path
from contextlib import asynccontextmanager

# Load environment variables FIRST
from dotenv import load_dotenv
load_dotenv()

# Import enterprise infrastructure
from config import settings, get_settings
from logger import logger, setup_logging
from middleware import setup_middleware
from exceptions import ElevareException

# FastAPI imports
from fastapi import FastAPI, Request, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates

# API routers
from api.validation import router as validation_router
from api.mcp import router as mcp_router
from api.matching import router as matching_router
from api.ideas import router as ideas_router
from api.agent import router as agent_router
from api.collaboration import router as collaboration_router
from api.mentor import router as mentor_router
from api.roadmap import router as roadmap_router
from api.auth import router as auth_router
from api.events import router as events_router
from api.admin import router as admin_router


# ==========================================
# APPLICATION LIFECYCLE MANAGEMENT
# ==========================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifecycle manager.
    Handles startup and shutdown events.
    """
    # STARTUP
    logger.info(f"🚀 Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    logger.info(f"📊 Environment: {settings.ENVIRONMENT.value}")
    logger.info(f"🔧 Debug Mode: {settings.DEBUG}")
    
    # Initialize database
    from db.database import Base, engine
    from models.user_models import User, Skill
    
    try:
        # In test mode, drop all tables first for clean state
        if settings.is_testing or os.getenv("PYTEST_CURRENT_TEST"):
            logger.info("Test mode detected - dropping all tables")
            try:
                Base.metadata.drop_all(bind=engine)
            except Exception as e:
                logger.warning(f"Could not drop tables: {e}")
        
        # Create all tables
        logger.info("Creating database tables...")
        Base.metadata.create_all(bind=engine)
        logger.info("✅ Database initialized successfully")
        
    except Exception as e:
        logger.error(f"❌ Database initialization failed: {e}", exc_info=True)
        if settings.is_production:
            raise
    
    # Initialize Redis connection
    try:
        from services.mcp_service import get_redis_client
        redis_client = get_redis_client()
        redis_client.ping()
        logger.info("✅ Redis connection established")
    except Exception as e:
        logger.warning(f"⚠️ Redis connection failed: {e}")
        if settings.is_production:
            raise
    
    # Log feature flags
    logger.info(f"Feature Flags:")
    logger.info(f"  - Cofounder Matching: {settings.FEATURE_COFOUNDER_MATCHING}")
    logger.info(f"  - AI Mentor: {settings.FEATURE_AI_MENTOR}")
    logger.info(f"  - Collaboration: {settings.FEATURE_COLLABORATION}")
    logger.info(f"  - Dimensional Analysis: {settings.FEATURE_DIMENSIONAL_ANALYSIS}")
    logger.info(f"  - Real GitHub API: {settings.FEATURE_REAL_GITHUB_API}")
    
    logger.info(f"✅ {settings.APP_NAME} started successfully on {settings.HOST}:{settings.PORT}")
    
    yield
    
    # SHUTDOWN
    logger.info(f"🛑 Shutting down {settings.APP_NAME}")
    
    # Cleanup Redis
    try:
        redis_client = get_redis_client()
        redis_client.close()
        logger.info("✅ Redis connection closed")
    except Exception as e:
        logger.warning(f"Error closing Redis connection: {e}")
    
    logger.info(f"✅ {settings.APP_NAME} shut down successfully")


# ==========================================
# APPLICATION FACTORY
# ==========================================

def create_application() -> FastAPI:
    """
    Application factory pattern.
    Creates and configures the FastAPI application.
    """
    
    # Create FastAPI app
    app = FastAPI(
        title=settings.APP_NAME,
        description="AI-powered startup validation and team building platform with autonomous agent support",
        version=settings.APP_VERSION,
        debug=settings.DEBUG,
        lifespan=lifespan,
        # Disable docs in production for security
        docs_url="/docs" if not settings.is_production else None,
        redoc_url="/redoc" if not settings.is_production else None,
        openapi_url="/openapi.json" if not settings.is_production else None,
    )
    
    # Setup middleware (CORS, logging, error handling, security, rate limiting)
    setup_middleware(app)
    
    # Mount API routers
    app.include_router(auth_router, prefix="/api/v1", tags=["Authentication"])
    app.include_router(validation_router, tags=["Validation"])
    app.include_router(mcp_router, tags=["MCP Service"])
    app.include_router(matching_router, prefix="/matching", tags=["Cofounder Matching"])
    app.include_router(ideas_router, prefix="/ideas", tags=["Ideas"])
    app.include_router(roadmap_router, prefix="/roadmap", tags=["Roadmap"])
    app.include_router(events_router, prefix="/events", tags=["Events"])
    
    # Connection management
    from api.connect import router as connect_router
    app.include_router(connect_router, prefix="/api", tags=["Connections"])
    
    app.include_router(agent_router, prefix="/api/v1", tags=["AI Agent"])
    app.include_router(collaboration_router, prefix="/api/v1", tags=["Collaboration"])
    app.include_router(mentor_router, prefix="/api/v1", tags=["AI Mentor"])
    app.include_router(admin_router, prefix="/api/v1", tags=["Admin - Knowledge Base"])
    
    # Mount static files
    static_dir = Path(__file__).parent / "static"
    if static_dir.exists():
        app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")
        app.mount("/assets", StaticFiles(directory=str(static_dir)), name="assets")
    
    # Setup templates
    templates_dir = Path(__file__).parent / "templates"
    templates = Jinja2Templates(directory=str(templates_dir))
    
    # ==========================================
    # HEALTH & STATUS ENDPOINTS
    # ==========================================
    
    @app.get("/healthz", tags=["Health"])
    @app.get("/health", tags=["Health"])
    async def health_check():
        """
        Health check endpoint for load balancers and monitoring.
        Returns system status and configuration info.
        """
        from services.dimensional_analyzer import DimensionalAnalyzer
        
        try:
            analyzer = DimensionalAnalyzer()
            active_model = analyzer.client.model if hasattr(analyzer, 'client') else settings.GROQ_MODEL
        except Exception:
            active_model = settings.GROQ_MODEL
        
        health_data = {
            "status": "ok",
            "app": settings.APP_NAME,
            "version": settings.APP_VERSION,
            "environment": settings.ENVIRONMENT.value,
            "active_model": active_model,
        }
        
        # Add detailed info in development
        if not settings.is_production:
            health_data["features"] = {
                "cofounder_matching": settings.FEATURE_COFOUNDER_MATCHING,
                "ai_mentor": settings.FEATURE_AI_MENTOR,
                "collaboration": settings.FEATURE_COLLABORATION,
                "dimensional_analysis": settings.FEATURE_DIMENSIONAL_ANALYSIS,
            }
        
        return health_data
    
    @app.get("/", response_class=HTMLResponse, tags=["Frontend"])
    async def root(request: Request):
        """Landing page"""
        return templates.TemplateResponse(request=request, name="index.html")
    
    # ==========================================
    # FRONTEND ROUTES
    # ==========================================
    
    @app.get("/login", response_class=HTMLResponse, tags=["Frontend"])
    async def login(request: Request):
        return templates.TemplateResponse(request=request, name="login.html")
    
    @app.get("/intake", response_class=HTMLResponse, tags=["Frontend"])
    async def intake(request: Request):
        return templates.TemplateResponse(request=request, name="intake.html")
    
    @app.get("/roadmap", response_class=HTMLResponse, tags=["Frontend"])
    async def roadmap(request: Request):
        return templates.TemplateResponse(request=request, name="roadmap-dynamic.html")
    
    @app.get("/dashboard", response_class=HTMLResponse, tags=["Frontend"])
    @app.get("/user", response_class=HTMLResponse, tags=["Frontend"])
    async def dashboard(request: Request):
        return templates.TemplateResponse(request=request, name="user.html")
    
    @app.get("/cofounder", response_class=HTMLResponse, tags=["Frontend"])
    async def cofounder(request: Request):
        return templates.TemplateResponse(request=request, name="cofounder.html")
    
    @app.get("/cofounder-simple", response_class=HTMLResponse, tags=["Frontend"])
    async def cofounder_simple(request: Request):
        """Simplified cofounder matching page for testing"""
        if settings.is_production:
            return JSONResponse(
                status_code=404,
                content={"error": "Page not available in production"}
            )
        return templates.TemplateResponse(request=request, name="cofounder_simple.html")
    
    @app.get("/profile-setup", response_class=HTMLResponse, tags=["Frontend"])
    async def profile_setup(request: Request):
        return templates.TemplateResponse(request=request, name="profile-setup.html")
    
    @app.get("/profile", response_class=HTMLResponse, tags=["Frontend"])
    async def profile(request: Request):
        return templates.TemplateResponse(request=request, name="profile.html")
    
    @app.get("/features", response_class=HTMLResponse, tags=["Frontend"])
    async def features(request: Request):
        return templates.TemplateResponse(request=request, name="features.html")
    
    @app.get("/events", response_class=HTMLResponse, tags=["Frontend"])
    async def events(request: Request):
        return templates.TemplateResponse(request=request, name="events.html")
    
    @app.get("/mentorship", response_class=HTMLResponse, tags=["Frontend"])
    async def mentorship(request: Request):
        return templates.TemplateResponse(request=request, name="mentorship.html")
    
    @app.get("/idea-wall", response_class=HTMLResponse, tags=["Frontend"])
    async def idea_wall(request: Request):
        return templates.TemplateResponse(request=request, name="idea-wall.html")
    
    @app.get("/systems", response_class=HTMLResponse, tags=["Frontend"])
    async def systems(request: Request):
        return templates.TemplateResponse(request=request, name="systems.html")
    
    return app


# ==========================================
# CREATE APPLICATION INSTANCE
# ==========================================

app = create_application()


# ==========================================
# ENTRY POINT FOR DEVELOPMENT SERVER
# ==========================================

if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.RELOAD,
        log_level=settings.LOG_LEVEL.lower(),
        access_log=True,
    )
