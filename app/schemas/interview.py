from pydantic import BaseModel, Field
from datetime import datetime
from typing import List, Optional

from app.models import InterviewTypeEnum, InterviewStatusEnum
from app.schemas import ProjectBase


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
    content: Optional[str] = None
    file_path: Optional[str] = None
    project: ProjectBase
    # requirement: Optional[RequirementBase]

    class Config:
        from_attributes = True


class InterviewUpdate(BaseModel):
    name: Optional[str] = None

class InterviewCreate(BaseModel):
    name: str
    type: InterviewTypeEnum
    status: InterviewStatusEnum
    content: Optional[str] = None
    file_path: Optional[str] = None
    project_id: int

class InterviewsGet(BaseModel):
    items: List[InterviewShallow]
    total: int
