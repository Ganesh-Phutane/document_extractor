"""
routes/auth.py
──────────────
Endpoints for user registration, login (JWT), and profile retrieval.
"""
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from core.dependencies import get_db, get_current_user
from core.security import create_access_token
from models.user import User
from schemas.user import UserCreate, UserLogin, UserResponse, TokenResponse
from services import auth_service

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(user_in: UserCreate, db: Annotated[Session, Depends(get_db)]):
    """Registers a new user."""
    # Check if user already exists
    existing_user = auth_service.get_user_by_email(db, email=user_in.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A user with this email already exists."
        )
    
    return auth_service.register_user(db, user_in=user_in)


@router.post("/login", response_model=TokenResponse)
def login(login_data: UserLogin, db: Annotated[Session, Depends(get_db)]):
    """Authenticates a user and returns a JWT token."""
    user = auth_service.authenticate_user(
        db, 
        email=login_data.email, 
        password=login_data.password
    )
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Create token
    access_token = create_access_token(data={"sub": user.id})
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": user
    }


@router.get("/me", response_model=UserResponse)
def get_me(current_user: Annotated[User, Depends(get_current_user)]):
    """Returns the profile of the currently authenticated user."""
    return current_user
