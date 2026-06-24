from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from typing import Dict, Any

from app.db.database import get_db
from app.core.security import (
    authenticate_user, 
    create_access_token, 
    get_current_user,
    get_current_active_user,
    get_password_hash
)
from app.core.config import settings
from app.models.user import User
from app.schemas.user import UserCreate, UserResponse, Token

router = APIRouter()


@router.post("/login", response_model=Token)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """User login - sets cross-subdomain cookie"""
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Create access token
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": str(user.id)},
        expires_delta=access_token_expires
    )
    
    response_data = {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": str(user.id),
            "username": user.username,
            "email": user.email,
            "role": user.role,
            "full_name": user.full_name
        }
    }
    
    # Set cookie for cross-subdomain auth (production, canadasite, www)
    cookie_max_age = settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60  # seconds
    response = JSONResponse(content=response_data)
    response.set_cookie(
        key="filebot_token",
        value=access_token,
        max_age=cookie_max_age,
        domain=".webfilebot.com",
        path="/",
        httponly=True,
        secure=True,
        samesite="lax"
    )
    return response


@router.post("/register", response_model=UserResponse)
def register(
    user_data: UserCreate,
    db: Session = Depends(get_db)
):
    """User registration"""
    # Check if username already exists
    existing_user = db.query(User).filter(
        (User.username == user_data.username) | (User.email == user_data.email)
    ).first()
    
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username or email already exists"
        )
    
    # Create new user
    user = User(
        username=user_data.username,
        email=user_data.email,
        password_hash=get_password_hash(user_data.password),
        full_name=user_data.full_name,
        is_active=True,
        role="user"
    )
    
    db.add(user)
    db.commit()
    db.refresh(user)
    
    return user


@router.get("/me")
def get_current_user_info(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get current user info (including group memberships)"""
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated"
        )
    
    # Build group info from memberships
    groups = []
    for gm in current_user.group_memberships:
        if gm.group:
            groups.append({
                "id": str(gm.group.id),
                "name": gm.group.name
            })
    
    return {
        "id": str(current_user.id),
        "username": current_user.username,
        "email": current_user.email,
        "full_name": current_user.full_name,
        "role": current_user.role,
        "is_active": current_user.is_active,
        "is_superuser": current_user.is_superuser,
        "created_at": current_user.created_at.isoformat() if current_user.created_at else None,
        "updated_at": current_user.updated_at.isoformat() if current_user.updated_at else None,
        "groups": groups
    }


@router.post("/refresh")
def refresh_token(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Refresh access token"""
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated"
        )
    
    # Create new access token
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": str(current_user.id)},
        expires_delta=access_token_expires
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer"
    }


@router.post("/logout")
def logout():
    """User logout - clears cookie"""
    response = JSONResponse(content={"message": "Logout successful"})
    response.delete_cookie(
        key="filebot_token",
        domain=".webfilebot.com",
        path="/"
    )
    return response


@router.get("/check")
def auth_check(request: Request, db: Session = Depends(get_db)):
    """
    Lightweight auth check for nginx auth_request.
    Reads token from cookie (filebot_token) or Authorization header.
    Returns 200 if valid, 401 if not.
    """
    # Try cookie first (for cross-subdomain auth)
    token = request.cookies.get("filebot_token")
    
    # Then try Authorization header (for API clients)
    if not token:
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]
    
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    user = get_current_user(db, token)
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    return {
        "authenticated": True,
        "username": user.username,
        "role": user.role
    }
