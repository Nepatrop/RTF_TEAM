from pydantic import BaseModel, Field, field_validator
from typing import List, Optional, Dict, Union, Any
from datetime import datetime

from app.models import (
    SessionCallbackEnum,
    SessionStatusEnum,
    SessionMessageRoleEnum,
    SessionMessageTypeEnum,
    QuestionStatusEnum,
    AgentSessionStatusEnum,
)


class QuestionData(BaseModel):
    id: str = Field(..., description="UUID вопроса от агента")
    question_number: int
    status: str
    question: str
    explanation: Optional[str] = None


class IterationWithQuestions(BaseModel):
    session_id: str
    iteration_id: str
    project_id: Optional[str] = None
    iteration_number: int
    title: Optional[str] = None
    questions: List[QuestionData]


class CallbackProjectUpdatedData(BaseModel):
    id: str
    title: str
    description: str
    size: int
    files: List[Dict[str, Any]]


class SessionDTO(BaseModel):
    session_id: str
    project_id: Optional[str] = None
    session_status: AgentSessionStatusEnum
    iteration_number: int
    final_result: Optional[str] = None
    error: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class CallbackErrorData(BaseModel):
    error: Dict[str, Any]


class AgentCallback(BaseModel):
    event: SessionCallbackEnum
    timestamp: datetime
    data: Union[
        IterationWithQuestions,
        SessionDTO,
        CallbackProjectUpdatedData,
        CallbackErrorData,
    ]


# Модели для создания сессии


class ContextQuestion(BaseModel):
    question: str
    answer: str


class SessionStartProjectContextRequest(BaseModel):
    user_goal: str


class SessionStartManualContextRequest(BaseModel):
    user_goal: str
    context_questions: List[ContextQuestion]


# Модели ответов


class SessionAnswerRequest(BaseModel):
    answer: str
    is_skipped: bool = False


# Модели сообщений


class AgentSessionMessageShallow(BaseModel):
    id: int
    role: SessionMessageRoleEnum
    message_type: SessionMessageTypeEnum
    content: str
    question_external_id: str
    question_number: Optional[int] = None
    question_status: Optional[QuestionStatusEnum] = None
    explanation: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class UserSessionAnswerShallow(BaseModel):
    role: SessionMessageRoleEnum
    message_type: SessionMessageTypeEnum
    content: str
    is_skipped: bool
    created_at: datetime

    class Config:
        from_attributes = True


class AgentSessionMessageCreate(BaseModel):
    session_id: int
    role: SessionMessageRoleEnum
    content: str
    message_type: SessionMessageTypeEnum
    question_id: Optional[str] = None
    question_number: Optional[int] = None
    question_status: Optional[QuestionStatusEnum] = None
    explanation: Optional[str] = None


class AgentSessionCreate(BaseModel):
    interview_id: int
    external_session_id: str
    status: SessionStatusEnum
    agent_session_status: Optional[AgentSessionStatusEnum] = None
    current_iteration: int
    user_goal: str
    context_questions: Optional[Dict[str, str]] = None
    callback_url: str


class AgentSessionUpdate(BaseModel):
    status: Optional[SessionStatusEnum] = None
    agent_session_status: Optional[AgentSessionStatusEnum] = None
    current_iteration: Optional[int] = None


class SessionStatusResponse(BaseModel):
    id: int
    external_session_id: str
    status: SessionStatusEnum
    user_goal: str
    current_iteration: int
    messages: Optional[List[AgentSessionMessageShallow]] = []

    class Config:
        from_attributes = True


class AgentSessionBase(BaseModel):
    id: int
    external_session_id: Optional[str] = None
    user_goal: str
    status: SessionStatusEnum
    current_iteration: int

    class Config:
        from_attributes = True
