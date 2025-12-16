from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Enum
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from app.models import Base

from app.models.enum import ProjectStatusEnum


class Project(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True)
    external_id = Column(String, nullable=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    status = Column(Enum(ProjectStatusEnum), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    files = relationship(
        "ProjectFile",
        back_populates="project",
        lazy="selectin",
        cascade="all, delete-orphan",
    )
    user = relationship("User", back_populates="projects", lazy="selectin")
    session = relationship(
        "AgentSessions",
        back_populates="project",
        cascade="all, delete-orphan",
        lazy="selectin",
        uselist=False,
    )


class ProjectFile(Base):
    __tablename__ = "project_files"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    original_name = Column(String, nullable=False)
    file_path = Column(String, nullable=False)
    file_size = Column(Integer, nullable=False)
    mime_type = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    project = relationship("Project", back_populates="files", lazy="selectin")
