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
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    external_id = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    project = relationship("Project", back_populates="interviews", lazy="selectin")
    requirement = relationship(
        "Requirement",
        back_populates="interview",
        lazy="selectin",
    )
    files = relationship(
        "InterviewFile",
        back_populates="interview",
        lazy="selectin",
        cascade="all, delete-orphan",
    )
    sessions = relationship(
        "AgentSessions", back_populates="interview", cascade="all, delete-orphan"
    )


class InterviewFile(Base):
    __tablename__ = "interview_files"

    id = Column(Integer, primary_key=True, index=True)
    interview_id = Column(Integer, ForeignKey("interviews.id"), nullable=False)
    original_name = Column(String, nullable=False)
    file_path = Column(String, nullable=False)
    file_size = Column(Integer, nullable=False)
    mime_type = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    interview = relationship("Interview", back_populates="files", lazy="selectin")
