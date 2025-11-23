from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Enum
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from app.models.base import Base
from app.models import InterviewTypeEnum, InterviewStatusEnum


class Interview(Base):
    __tablename__ = "interviews"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    type = Column(Enum(InterviewTypeEnum), nullable=False)
    status = Column(Enum(InterviewStatusEnum), nullable=False)
    content = Column(Text)
    file_path = Column(String)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    project = relationship(
        "Project",
        back_populates="interviews",
        lazy="selectin"
    )
    requirement = relationship(
        "Requirement",
        back_populates="interview",
        lazy="selectin",
    )
