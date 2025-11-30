from pydantic import BaseModel, Field
from datetime import datetime
from typing import List, Optional

from app.models import InterviewTypeEnum, InterviewStatusEnum
from app.schemas import ProjectBase


class InterviewFileBase(BaseModel):
    id: int
    file_path: str
    original_name: str
    file_size: int
    mime_type: str
    created_at: datetime

    class Config:
        from_attributes = True


class InterviewFileCreate(BaseModel):
    interview_id: int
    original_name: str
    file_path: str
    file_size: int
    mime_type: str


class InterviewShallow(BaseModel):
    id: int
    name: str
    type: InterviewTypeEnum
    status: InterviewStatusEnum
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True


class InterviewBase(InterviewShallow):
    external_id: Optional[str] = None
    project: ProjectBase
    # requirement: Optional[RequirementBase]
    files: List[InterviewFileBase] = []

    class Config:
        from_attributes = True


class InterviewUpdate(BaseModel):
    name: Optional[str] = None
    external_id: Optional[str] = None


class InterviewCreate(BaseModel):
    name: str
    type: InterviewTypeEnum
    status: InterviewStatusEnum
    project_id: int


class InterviewsGet(BaseModel):
    items: List[InterviewShallow]
    total: int
