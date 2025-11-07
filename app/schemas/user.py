from pydantic import BaseModel, EmailStr
from datetime import datetime


class UserCreate(BaseModel):
    email: EmailStr
    display_name: str
    hashed_password: str


class UserUpdate(BaseModel):
    display_name: str


class UserBase(BaseModel):
    id: int
    email: EmailStr
    display_name: str
    is_active: bool
    created_at: datetime
    updated_at: datetime | None

    class Config:
        from_attributes = True
