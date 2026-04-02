"""
services/auth_service.py
────────────────────────
Business logic for User Registration, Authentication, and Session Management.
"""
from datetime import datetime, timezone
import uuid
from sqlalchemy.orm import Session
from sqlalchemy import select

from models.user import User
from models.audit import AuditLog
from schemas.user import UserCreate
from core.security import hash_password, verify_password


def register_user(db: Session, user_in: UserCreate) -> User:
    """Creates a new user in the database with a hashed password."""
    db_user = User(
        email=user_in.email,
        hashed_password=hash_password(user_in.password),
        is_active=True
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


def authenticate_user(db: Session, email: str, password: str) -> User | None:
    """Verifies credentials and updates last_login if successful."""
    # Find user
    result = db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()

    if not user:
        return None
    
    if not verify_password(password, user.hashed_password):
        return None
    
    # Update last login
    user.last_login = datetime.now(timezone.utc)
    
    # Log Audit Event
    audit = AuditLog(
        user_id=user.id,
        action="login",
        details={"ip": "local", "status": "success"} # Placeholder for more metadata later
    )
    db.add(audit)
    
    db.commit()
    db.refresh(user)
    return user


def get_user_by_email(db: Session, email: str) -> User | None:
    """Finds a user by their unique email address."""
    result = db.execute(select(User).where(User.email == email))
    return result.scalar_one_or_none()


def get_user_by_id(db: Session, user_id: str) -> User | None:
    """Finds a user by their primary key (String UUID)."""
    result = db.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()
