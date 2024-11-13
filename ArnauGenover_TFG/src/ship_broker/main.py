# src/ship_broker/main.py
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
import os

from .config import Settings, get_settings
from .api.routes import vessels, cargoes, email_processing
from .core.database import Base, engine

# Create database tables
Base.metadata.create_all(bind=engine)

settings = get_settings()

# Initialize FastAPI app
app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
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
app.mount("/static", StaticFiles(directory=os.path.join(current_dir, "web/static")), name="static")

# Initialize templates
templates = Jinja2Templates(directory=os.path.join(current_dir, "web/templates"))

# Include API routers
app.include_router(vessels, prefix="/api/v1", tags=["vessels"])
app.include_router(cargoes, prefix="/api/v1", tags=["cargoes"])
app.include_router(email_processing, prefix="/api/v1", tags=["email"])

@app.get("/")
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/vessels")
async def vessels_page(request: Request):
    return templates.TemplateResponse("vessels.html", {"request": request})

@app.get("/cargoes")
async def cargoes_page(request: Request):
    return templates.TemplateResponse("cargoes.html", {"request": request})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)