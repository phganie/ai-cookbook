import uuid
from datetime import datetime

from sqlalchemy import JSON, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from .database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String, unique=True, nullable=False, index=True)
    hashed_password = Column(String, nullable=True)  # Nullable for Google OAuth users
    google_id = Column(String, unique=True, nullable=True, index=True)  # Google user ID
    auth_provider = Column(String, nullable=False, default="email")  # "email" or "google"
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    
    # Relationship to recipes
    recipes = relationship("Recipe", back_populates="owner", cascade="all, delete-orphan")


class Recipe(Base):
    __tablename__ = "recipes"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    source_url = Column(Text, nullable=False)
    source_platform = Column(String, nullable=False, default="youtube")
    title = Column(Text, nullable=False)
    servings = Column(Integer, nullable=True)
    ingredients = Column(JSON, nullable=False)
    steps = Column(JSON, nullable=False)
    missing_info = Column(JSON, nullable=False, default=list)
    notes = Column(JSON, nullable=False, default=list)
    transcript = Column(Text, nullable=True)  # Store transcript for Ask AI feature
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    
    # Relationship to user
    owner = relationship("User", back_populates="recipes")


