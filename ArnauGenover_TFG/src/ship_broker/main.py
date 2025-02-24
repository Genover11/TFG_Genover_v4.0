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

from fastapi import Form, status
from fastapi.responses import RedirectResponse
import jwt
from datetime import datetime, timedelta
from .core.database import User
from .api.dependencies import get_db  # Added missing import
from sqlalchemy.orm import Session  # Added missing import

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

@app.get("/login")
async def login_page(request: Request):
    """Render login page"""
    try:
        return templates.TemplateResponse("login.html", {
            "request": request,
            "current_user": None
        })
    except Exception as e:
        logger.error(f"Error rendering login page: {str(e)}")
        return {"error": "Error rendering page"}

@app.get("/register")
async def register_page(request: Request):
    """Render registration page"""
    try:
        return templates.TemplateResponse("register.html", {
            "request": request,
            "current_user": None
        })
    except Exception as e:
        logger.error(f"Error rendering register page: {str(e)}")
        return {"error": "Error rendering page"}

@app.post("/login")
async def login_form(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    """Process login form submission"""
    try:
        user = db.query(User).filter(User.email == username).first()
        if not user or not user.verify_password(password):
            return templates.TemplateResponse(
                "login.html",
                {"request": request, "error": "Invalid email or password", "current_user": None}
            )
        
        # Create JWT token
        token = jwt.encode(
            {"sub": str(user.id), "exp": datetime.utcnow() + timedelta(hours=24)},
            settings.SECRET_KEY,
            algorithm="HS256"
        )
        
        response = RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)
        response.set_cookie(
            key="session",
            value=token,
            httponly=True,
            max_age=86400,  # 24 hours
            expires=86400,
        )
        return response
    except Exception as e:
        logger.error(f"Error processing login: {str(e)}")
        return templates.TemplateResponse(
            "login.html",
            {"request": request, "error": "Login failed. Please try again.", "current_user": None}
        )

@app.post("/register")
async def register_form(
    request: Request,
    username: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    """Process registration form submission"""
    try:
        # Check for existing email
        existing_email = db.query(User).filter(User.email == email).first()
        # Check for existing username
        existing_username = db.query(User).filter(User.username == username).first()

        errors = []
        if existing_email:
            errors.append("Email is already registered")
        if existing_username:
            errors.append("Username is already taken")

        if errors:
            return templates.TemplateResponse(
                "register.html",
                {"request": request, "error": " and ".join(errors), "current_user": None}
            )
        
        user = User(
            email=email,
            username=username,
            hashed_password=User.get_password_hash(password)
        )
        db.add(user)
        db.commit()
        return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)
    except Exception as e:
        logger.error(f"Error processing registration: {str(e)}")
        db.rollback()
        return templates.TemplateResponse(
            "register.html",
            {"request": request, "error": "Registration failed. Please try again.", "current_user": None}
        )