from pydantic import BaseModel, EmailStr
from datetime import datetime


class UserCreate(BaseModel):
    email: EmailStr
    display_name: str
    hashed_password: str


class UserBase(BaseModel):
    id: int
    email: EmailStr
    display_name: str
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True
