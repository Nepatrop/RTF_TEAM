from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Enum
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import Base
import enum


class InterviewType(enum.Enum):
    TEXT = "text"
    AUDIO = "audio"


class Interview:
    __tablename__ = "interviews"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    type = Column(Enum(InterviewType), nullable=False)
    content = Column(Text)  # Текст
    file_path = Column(String)  # Аудио
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
