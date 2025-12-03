from pydantic import BaseModel
from typing import List, Optional, Literal, Union
from datetime import datetime

from app.models import (
    SessionCallbackEnum,
    SessionStatusEnum,
    SessionMessageRoleEnum,
    SessionMessageTypeEnum,
)


class QuestionsData(BaseModel):
    session_id: str
    session_status: str
    project_id: str
    iteration_number: int
    questions: List[str]


class FinalResultData(BaseModel):
    session_id: str
    project_id: str
    result: str
    error: str


class ProjectUpdatedData(BaseModel):
    id: str
    title: str
    size: int
    files: List[dict]


class AgentCallback(BaseModel):
    event: SessionCallbackEnum
    timestamp: datetime
    data: Union[QuestionsData, FinalResultData, ProjectUpdatedData]


class AgentSessionCreate(BaseModel):
    interview_id: int
    external_session_id: str
    status: SessionStatusEnum
    current_iteration: int


class AgentSessionUpdate(BaseModel):
    status: Optional[SessionStatusEnum] = None
    current_iteration: Optional[int] = None


class AgentSessionMessageCreate(BaseModel):
    session_id: int
    role: SessionMessageRoleEnum
    content: str
    message_type: SessionMessageTypeEnum


class AgentSessionMessageShallow(BaseModel):
    role: SessionMessageRoleEnum
    message_type: SessionMessageTypeEnum
    content: str
    created_at: datetime


class ContextQuestions(BaseModel):
    task: str
    goal: str
    value: str


class SessionStartRequest(BaseModel):
    project_id: int
    context_questions: ContextQuestions


class SessionAnswerRequest(BaseModel):
    answers: str


class SessionStatusResponse(BaseModel):
    id: int
    external_session_id: str
    status: SessionStatusEnum
    current_iteration: int
    messages: Optional[List[AgentSessionMessageShallow]] = []

    class Config:
        from_attributes = True


class AgentSessionBase(BaseModel):
    id: int
    external_session_id: str
    status: SessionStatusEnum
    current_iteration: int

    class Config:
        from_attributes = True
