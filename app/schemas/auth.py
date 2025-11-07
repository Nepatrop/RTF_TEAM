from pydantic import BaseModel, EmailStr, Field
from datetime import datetime


class Token(BaseModel):
    access_token: str
    refresh_token: str


class RefreshTokenCreate(BaseModel):
    token: str
    user_id: int
    expires_at: datetime


class RefreshToken(BaseModel):
    refresh_token: str


class Login(BaseModel):
    email: EmailStr
    password: str


class Register(Login):
    email: EmailStr
    display_name: str = Field(
        ..., min_length=4, description="Display name must be at least 4 characters"
    )
    password: str = Field(
        ..., min_length=8, description="Password must be at least 8 characters"
    )
