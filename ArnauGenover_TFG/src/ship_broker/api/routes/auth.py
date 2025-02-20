# src/ship_broker/api/routes/auth.py

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status, Form
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
import jwt
from datetime import datetime, timedelta
from ...core.database import User
from ...core.schemas import UserCreate
from ..dependencies import get_db
from ...config import get_settings

settings = get_settings()
router = APIRouter()
templates = Jinja2Templates(directory="src/ship_broker/web/templates")

SECRET_KEY = settings.SECRET_KEY
ALGORITHM = "HS256"

# Dependency to get current user
async def get_current_user(request: Request, db: Session = Depends(get_db)):
    token = request.cookies.get("session")
    if not token:
        return None
    
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        if user_id is None:
            return None
        return db.query(User).filter(User.id == user_id).first()
    except:
        return None

@router.get("/login")
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request, "current_user": None})

@router.post("/login")
async def login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.email == username).first()
    if not user or not user.verify_password(password):
        return templates.TemplateResponse(
            "login.html",
            {"request": request, "error": "Invalid email or password", "current_user": None}
        )
    
    # Create JWT token
    token = jwt.encode(
        {"sub": str(user.id), "exp": datetime.utcnow() + timedelta(hours=24)},
        SECRET_KEY,
        algorithm=ALGORITHM
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

@router.get("/register")
async def register_page(request: Request):
    return templates.TemplateResponse("register.html", {"request": request, "current_user": None})

@router.post("/register")
async def register(
    request: Request,
    username: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
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
    
    try:
        user = User(
            email=email,
            username=username,
            hashed_password=User.get_password_hash(password)
        )
        db.add(user)
        db.commit()
        return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)
    except Exception as e:
        db.rollback()
        return templates.TemplateResponse(
            "register.html",
            {"request": request, "error": "Registration failed. Please try again.", "current_user": None}
        )

@router.get("/logout")
async def logout():
    response = RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)
    response.delete_cookie("session")
    return response