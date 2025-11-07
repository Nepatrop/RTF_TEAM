from app.core.database import Base
import enum


class SessionStatus(enum.Enum):
    PROCESSING = "processing"
    QUESTION = "question"
    FINISHED = "finished"
    ERROR = "error"
    CANCELLED = "cancelled"


class AgentSession:
    __tablename__ = "agent_sessions"


class Requirement:
    __tablename__ = "requirements"
