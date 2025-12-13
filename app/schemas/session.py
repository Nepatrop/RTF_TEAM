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
    iteration_number: int
    title: Optional[str] = None
    questions: List[QuestionData]


class CallbackProjectUpdatedData(BaseModel):
    id: str
    title: str
    description: Optional[str] = None
    size: int
    files: List[Dict[str, Any]]


class SessionDTO(BaseModel):
    session_id: str
    project_id: str
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
    data: Union[IterationWithQuestions, SessionDTO, CallbackProjectUpdatedData, CallbackErrorData]

# Модели для создания сессии

class ContextQuestions(BaseModel):
    task: str
    goal: str
    value: str


class SessionStartRequest(BaseModel):
    interview_id: Optional[int] = None
    project_id: Optional[int] = None
    context_questions: Optional[ContextQuestions] = None
    callback_url: str = Field(..., description="URL для отправки callback'ов")

# Модели ответов

class AnswerQuestion(BaseModel):
    question_id: str
    answer: str


class SkipQuestion(BaseModel):
    question_id: str
    reason: Optional[str] = None


class SessionAnswerRequest(BaseModel):
    message: Optional[str] = None
    answers: Optional[Union[str, List[AnswerQuestion], Dict[str, Any]]] = None
    
    # Валидатор для обработки разных форматов
    @field_validator('answers', mode='before')
    @classmethod
    def validate_answers(cls, v, info):
        # Если передано message, но не передано answers
        if info.data.get('message') and v is None:
            return info.data.get('message')
        return v

# Модели сообщений

class AgentSessionMessageShallow(BaseModel):
    role: SessionMessageRoleEnum
    message_type: SessionMessageTypeEnum
    content: str
    question_id: Optional[str] = None
    question_number: Optional[int] = None
    question_status: Optional[QuestionStatusEnum] = None
    explanation: Optional[str] = None
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
    agent_session_status: Optional[AgentSessionStatusEnum] = None
    current_iteration: int
    messages: Optional[List[AgentSessionMessageShallow]] = []

    class Config:
        from_attributes = True


class AgentSessionBase(BaseModel):
    id: int
    external_session_id: str
    status: SessionStatusEnum
    agent_session_status: Optional[AgentSessionStatusEnum] = None
    current_iteration: int
    callback_url: str

    class Config:
        from_attributes = True
