"""
schemas/user.py
────────────────
Pydantic v2 schemas for User — request/response contracts for auth endpoints.
"""
import uuid
from datetime import datetime
from pydantic import BaseModel, EmailStr, field_validator


class UserCreate(BaseModel):
    """POST /auth/register body"""
    email: EmailStr
    password: str

    @field_validator("password")
    @classmethod
    def password_min_length(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v


class UserLogin(BaseModel):
    """POST /auth/login body"""
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    """Returned in API responses — never includes password"""
    model_config = {"from_attributes": True}

    id: uuid.UUID
    email: str
    created_at: datetime
    last_login: datetime | None = None


class TokenResponse(BaseModel):
    """Returned after successful login"""
    access_token: str
    token_type: str = "bearer"
    user: UserResponse
