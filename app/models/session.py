from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Enum, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from app.models.base import Base
from app.models import SessionStatusEnum, SessionMessageRoleEnum, SessionMessageTypeEnum


class AgentSessions(Base):
    __tablename__ = "agent_sessions"

    id = Column(Integer, primary_key=True, index=True)
    interview_id = Column(Integer, ForeignKey("interviews.id"), nullable=False)
    external_session_id = Column(String, unique=True, nullable=False)
    status = Column(Enum(SessionStatusEnum), nullable=False)
    current_iteration = Column(Integer, nullable=False, default=1)
    context_questions = Column(JSON, nullable=True)

    interview = relationship("Interview", back_populates="sessions")
    messages = relationship(
        "AgentSessionMessage", back_populates="session", cascade="all, delete-orphan"
    )


class AgentSessionMessage(Base):
    __tablename__ = "agent_session_messages"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("agent_sessions.id"), nullable=False)
    role = Column(Enum(SessionMessageRoleEnum), nullable=False)
    content = Column(String, nullable=False)
    message_type = Column(Enum(SessionMessageTypeEnum), nullable=False)
    iteration_number = Column(Integer, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    session = relationship("AgentSessions", back_populates="messages")
