from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field, field_validator


def validate_password_strength(password: str) -> str:
    """Validate password strength and raise ValueError if weak."""
    errors = []
    
    if len(password) < 8:
        errors.append("Password must be at least 8 characters long")
    # Limit to 72 characters to avoid bcrypt's 72-byte limit
    # (1 character = 1 byte for ASCII, but Unicode can be more)
    if len(password) > 72:
        errors.append("Password must be less than 72 characters")
    if not any(c.isupper() for c in password):
        errors.append("Password must contain at least one uppercase letter")
    if not any(c.islower() for c in password):
        errors.append("Password must contain at least one lowercase letter")
    if not any(c.isdigit() for c in password):
        errors.append("Password must contain at least one number")
    if not any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password):
        errors.append("Password must contain at least one special character")
    
    if errors:
        raise ValueError("; ".join(errors))
    
    return password


class UserBase(BaseModel):
    email: EmailStr


class UserCreate(UserBase):
    password: str = Field(min_length=8, max_length=72)
    
    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        return validate_password_strength(v)


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class GoogleAuthRequest(BaseModel):
    """Request for Google OAuth authentication."""
    code: str  # Authorization code from Google


class UserResponse(UserBase):
    id: str
    auth_provider: str
    created_at: datetime

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse

