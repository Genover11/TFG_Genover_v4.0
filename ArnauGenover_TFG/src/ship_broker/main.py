# src/ship_broker/main.py

from fastapi import FastAPI, Request, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
import asyncio
import os
import logging

from .config import Settings, get_settings
from .api.routes import vessels, cargoes, email_processing, test, matching, auctions, auth
from .core.database import Base, engine
from .core.scheduler import start_scheduler
from .api.routes.auth import get_current_user
from .core.vessel_tracker import tracker

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

# Create database tables
Base.metadata.create_all(bind=engine)

# Get settings
settings = get_settings()

# Initialize FastAPI app first
app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Ship broker application for managing vessels and cargoes",
    docs_url="/api/docs",
    redoc_url="/api/redoc"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Get the current file's directory
current_dir = os.path.dirname(os.path.abspath(__file__))

# Mount static files
static_dir = os.path.join(current_dir, "web", "static")
if not os.path.exists(static_dir):
    os.makedirs(static_dir, exist_ok=True)
    logger.info(f"Created static directory: {static_dir}")

# Create necessary subdirectories
for subdir in ['css', 'js', 'img']:
    subdir_path = os.path.join(static_dir, subdir)
    if not os.path.exists(subdir_path):
        os.makedirs(subdir_path, exist_ok=True)
        logger.info(f"Created static subdirectory: {subdir_path}")

app.mount("/static", StaticFiles(directory=static_dir), name="static")
logger.info(f"Static files mounted from: {static_dir}")

# Initialize templates
templates_dir = os.path.join(current_dir, "web", "templates")
if not os.path.exists(templates_dir):
    os.makedirs(templates_dir, exist_ok=True)
    logger.info(f"Created templates directory: {templates_dir}")

templates = Jinja2Templates(directory=templates_dir)

# Include API routers with consistent prefixes
app.include_router(
    vessels.router,
    prefix="/api/v1",
    tags=["vessels"]
)

app.include_router(
    cargoes.router,
    prefix="/api/v1",
    tags=["cargoes"]
)

app.include_router(
    email_processing.router,
    prefix="/api/v1",
    tags=["email"]
)

app.include_router(
    matching.router,
    prefix="/api/v1",
    tags=["matching"]
)

app.include_router(
    test.router,
    prefix="/api/v1",
    tags=["test"]
)

app.include_router(
    auctions.router,
    prefix="/api/v1",
    tags=["auctions"]
)

app.include_router(
    auth.router,
    prefix="/api/v1",
    tags=["auth"]
)

@app.on_event("startup")
async def startup_event():
    """Start background tasks when the application starts"""
    try:
        logger.info("Starting background tasks...")
        
        # Start the scheduler
        asyncio.create_task(start_scheduler())
        
        # Start AIS stream
        asyncio.create_task(tracker.start_tracking())
        
        logger.info("Background tasks started successfully")
    except Exception as e:
        logger.error(f"Error starting background tasks: {str(e)}")

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup when the application shuts down"""
    try:
        # Stop AIS stream
        await tracker.stop_tracking()
    except Exception as e:
        logger.error(f"Error during shutdown: {str(e)}")

@app.get("/")
async def home(request: Request, current_user=Depends(get_current_user)):
    """Render home page"""
    try:
        return templates.TemplateResponse("index.html", {
            "request": request,
            "current_user": current_user
        })
    except Exception as e:
        logger.error(f"Error rendering home page: {str(e)}")
        return {"error": "Error rendering page"}

@app.get("/vessels")
async def vessels_page(request: Request, current_user=Depends(get_current_user)):
    """Render vessels page"""
    try:
        return templates.TemplateResponse("vessels.html", {
            "request": request,
            "current_user": current_user
        })
    except Exception as e:
        logger.error(f"Error rendering vessels page: {str(e)}")
        return {"error": "Error rendering page"}

@app.get("/cargoes")
async def cargoes_page(request: Request, current_user=Depends(get_current_user)):
    """Render cargoes page"""
    try:
        return templates.TemplateResponse("cargoes.html", {
            "request": request,
            "current_user": current_user
        })
    except Exception as e:
        logger.error(f"Error rendering cargoes page: {str(e)}")
        return {"error": "Error rendering page"}

@app.get("/auctions")
async def auctions_page(request: Request, current_user=Depends(get_current_user)):
    """Render auctions page"""
    try:
        return templates.TemplateResponse("auctions.html", {
            "request": request,
            "current_user": current_user
        })
    except Exception as e:
        logger.error(f"Error rendering auctions page: {str(e)}")
        return {"error": "Error rendering page"}

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        return {
            "status": "healthy",
            "version": settings.VERSION,
            "database": "connected" if engine else "disconnected",
            "ais_stream": "connected" if tracker.api_key else "disconnected"
        }
    except Exception as e:
        logger.error(f"Error in health check: {str(e)}")
        return {
            "status": "unhealthy",
            "error": str(e)
        }