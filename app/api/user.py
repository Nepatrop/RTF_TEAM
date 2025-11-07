from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app import schemas
from app.models.user import User as UserORM
from app.dependencies import get_current_user

router = APIRouter(prefix="/user", tags=["users"])


@router.get(
    "/me",
    status_code=200,
    response_model=schemas.UserBase,
    responses={
        401: {"description": "Unauthorized", "model": schemas.ErrorResponse},
    },
)
async def get_current_user(
    current_user: UserORM = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    return schemas.UserBase.model_validate(current_user)
