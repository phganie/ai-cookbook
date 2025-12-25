"""
User service for database operations.
"""
from sqlalchemy.orm import Session

from .. import models
from ..services.auth import get_password_hash, verify_password


def get_user_by_email(db: Session, email: str) -> models.User | None:
    """Get a user by email."""
    return db.query(models.User).filter(models.User.email == email).first()


def create_user(db: Session, email: str, password: str) -> models.User:
    """Create a new user with email/password."""
    hashed_password = get_password_hash(password)
    user = models.User(
        email=email,
        hashed_password=hashed_password,
        auth_provider="email"
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def create_google_user(db: Session, email: str, google_id: str) -> models.User:
    """Create a new user with Google OAuth."""
    user = models.User(
        email=email,
        google_id=google_id,
        auth_provider="google",
        hashed_password=None  # No password for Google users
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def get_user_by_google_id(db: Session, google_id: str) -> models.User | None:
    """Get a user by Google ID."""
    return db.query(models.User).filter(models.User.google_id == google_id).first()


def get_or_create_google_user(db: Session, email: str, google_id: str) -> models.User:
    """Get existing user or create new one for Google OAuth."""
    # Check if user exists by Google ID
    user = get_user_by_google_id(db, google_id)
    if user:
        return user
    
    # Check if user exists by email (link accounts)
    user = get_user_by_email(db, email)
    if user:
        # Link Google account to existing email account
        user.google_id = google_id
        if user.auth_provider == "email":
            # Keep email auth, but add Google as alternative
            user.auth_provider = "email,google"
        db.commit()
        db.refresh(user)
        return user
    
    # Create new user
    return create_google_user(db, email, google_id)


def authenticate_user(db: Session, email: str, password: str) -> models.User | None:
    """Authenticate a user by email and password."""
    user = get_user_by_email(db, email)
    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user

