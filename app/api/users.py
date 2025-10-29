from fastapi import APIRouter, Depends

from app.core.database import get_db
from app.schemas.user import UserResponse

router = APIRouter()

@router.get("/me", response_model=UserResponse)
async def get_current_user():
    return {"message": "Get current user endpoint"}
