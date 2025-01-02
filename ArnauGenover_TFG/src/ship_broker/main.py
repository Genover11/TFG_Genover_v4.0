# src/ship_broker/main.py

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
import asyncio
import os
import logging

from .config import Settings, get_settings
from .api.routes import vessels, cargoes, email_processing, test, matching, auctions
from .core.database import Base, engine
from .core.scheduler import start_scheduler

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create database tables
Base.metadata.create_all(bind=engine)

# Get settings
settings = get_settings()

# Initialize FastAPI app
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
static_dir = os.path.join(current_dir, "web/static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")
else:
    logger.warning(f"Static directory not found: {static_dir}")

# Initialize templates
templates_dir = os.path.join(current_dir, "web/templates")
if os.path.exists(templates_dir):
    templates = Jinja2Templates(directory=templates_dir)
else:
    logger.warning(f"Templates directory not found: {templates_dir}")

# Include API routers
app.include_router(vessels, prefix="/api/v1", tags=["vessels"])
app.include_router(cargoes, prefix="/api/v1", tags=["cargoes"])
app.include_router(email_processing, prefix="/api/v1", tags=["email"])
app.include_router(matching, prefix="/api/v1", tags=["matching"])
app.include_router(test, prefix="/api/v1", tags=["test"])
app.include_router(auctions, prefix="/api/v1", tags=["auctions"])  # Changed this line

@app.on_event("startup")
async def startup_event():
    """Start background tasks when the application starts"""
    try:
        logger.info("Starting background tasks...")
        asyncio.create_task(start_scheduler())
        logger.info("Background tasks started successfully")
    except Exception as e:
        logger.error(f"Error starting background tasks: {str(e)}")

@app.get("/")
async def home(request: Request):
    """Render home page"""
    try:
        return templates.TemplateResponse("index.html", {"request": request})
    except Exception as e:
        logger.error(f"Error rendering home page: {str(e)}")
        return {"error": "Error rendering page"}

@app.get("/vessels")
async def vessels_page(request: Request):
    """Render vessels page"""
    try:
        return templates.TemplateResponse("vessels.html", {"request": request})
    except Exception as e:
        logger.error(f"Error rendering vessels page: {str(e)}")
        return {"error": "Error rendering page"}

@app.get("/cargoes")
async def cargoes_page(request: Request):
    """Render cargoes page"""
    try:
        return templates.TemplateResponse("cargoes.html", {"request": request})
    except Exception as e:
        logger.error(f"Error rendering cargoes page: {str(e)}")
        return {"error": "Error rendering page"}

@app.get("/matches")
async def matches_page(request: Request):
    """Render matches page"""
    try:
        return templates.TemplateResponse("matches.html", {"request": request})
    except Exception as e:
        logger.error(f"Error rendering matches page: {str(e)}")
        return {"error": "Error rendering page"}

@app.get("/auctions")
async def auctions_page(request: Request):
    """Render auctions page"""
    try:
        return templates.TemplateResponse("auctions.html", {"request": request})
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
            "database": "connected" if engine else "disconnected"
        }
    except Exception as e:
        logger.error(f"Error in health check: {str(e)}")
        return {
            "status": "unhealthy",
            "error": str(e)
        }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app, 
        host="0.0.0.0", 
        port=8000, 
        reload=True,
        log_level="info"
    )