from pydantic import BaseModel
from datetime import datetime

class RequirementBase(BaseModel):
    id: int
    content: str
    created_at: datetime

class RequirementUpdate(BaseModel):
    content: str