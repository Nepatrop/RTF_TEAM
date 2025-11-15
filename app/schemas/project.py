from pydantic import BaseModel, Field
from datetime import datetime
from typing import List, Optional


class ProjectBase(BaseModel):
    id: int
    name: str
    description: Optional[str]
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True


class ProjectCreate(BaseModel):
    name: str = Field(..., min_length=4, max_length=50)
    description: Optional[str] = None


class ProjectCreateInternal(ProjectCreate):
    user_id: int


class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None


class ProjectsGet(BaseModel):
    items: List[ProjectBase]
    total: int
