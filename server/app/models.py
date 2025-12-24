import uuid
from datetime import datetime

from sqlalchemy import JSON, Column, DateTime, Integer, String, Text

from .database import Base


class Recipe(Base):
    __tablename__ = "recipes"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    source_url = Column(Text, nullable=False)
    source_platform = Column(String, nullable=False, default="youtube")
    title = Column(Text, nullable=False)
    servings = Column(Integer, nullable=True)
    ingredients = Column(JSON, nullable=False)
    steps = Column(JSON, nullable=False)
    missing_info = Column(JSON, nullable=False, default=list)
    notes = Column(JSON, nullable=False, default=list)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)


