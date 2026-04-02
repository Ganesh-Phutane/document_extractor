"""
core/dependencies.py
────────────────────
FastAPI dependencies used across routers.
"""
from typing import Annotated, Generator

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from sqlalchemy.orm import Session

from core.config import settings
from core.database import SessionLocal
from core.security import decode_access_token
from models.user import User
from services import auth_service

# OAuth2 scheme for JWT
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")


def get_db() -> Generator[Session, None, None]:
    """Database session dependency."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_current_user(
    db: Annotated[Session, Depends(get_db)],
    token: Annotated[str, Depends(oauth2_scheme)]
) -> User:
    """
    Validates JWT token and returns the current user.
    Supports BYPASS_AUTH for local development.
    """
    # ── Dev Bypass ─────────────────────────────────────
    if settings.BYPASS_AUTH:
        # Try to find or create a default test user
        test_user = auth_service.get_user_by_email(db, "test@example.com")
        if not test_user:
            from schemas.user import UserCreate
            test_user = auth_service.register_user(
                db, 
                UserCreate(email="test@example.com", password="password123")
            )
        return test_user

    # ── Standard JWT Validation ────────────────────────
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = decode_access_token(token)
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = auth_service.get_user_by_id(db, user_id=user_id)
    if user is None:
        raise credentials_exception
        
    return user
