from pydantic import BaseModel, Field
from datetime import datetime
from typing import List, Optional

from app.models import ProjectStatusEnum
from app.schemas.session import AgentSessionWithRequirement


class ProjectFileBase(BaseModel):
    id: int
    file_path: str
    original_name: str
    file_size: int
    mime_type: str
    created_at: datetime

    class Config:
        from_attributes = True


class ProjectFileCreate(BaseModel):
    interview_id: int
    original_name: str
    file_path: str
    file_size: int
    mime_type: str


class ProjectBase(BaseModel):
    id: int
    external_id: Optional[str] = None
    status: ProjectStatusEnum
    title: str
    description: str
    created_at: datetime
    updated_at: Optional[datetime]

    files: List[ProjectFileBase] = []
    session: Optional[AgentSessionWithRequirement] = None

    class Config:
        from_attributes = True


class ProjectShallow(BaseModel):
    id: int
    status: ProjectStatusEnum
    title: str
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True


class ProjectsGet(BaseModel):
    items: List[ProjectShallow]
    total: int
