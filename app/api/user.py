from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app import schemas
from app.models.user import User as UserORM
from app.dependencies import get_current_user
from app.cruds import UserCRUD

router = APIRouter(prefix="/user", tags=["users"])


@router.get(
    "/me",
    status_code=200,
    response_model=schemas.UserBase,
    responses={
        401: {"description": "Unauthorized", "model": schemas.ErrorResponse},
    },
)
async def get_current_user_data(
    current_user: UserORM = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    return current_user


@router.patch(
    "/me",
    status_code=200,
    response_model=schemas.UserBase,
    responses={
        401: {"description": "Unauthorized", "model": schemas.ErrorResponse},
        422: {
            "description": "Validation Error",
            "model": schemas.RequestValidationError,
        },
        500: {"description": "Internal Server Error", "model": schemas.ErrorResponse},
    },
)
async def update_current_user(
    payload: schemas.UserUpdate,
    current_user: UserORM = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    update_data = payload.model_dump(exclude_unset=True)
    await UserCRUD.update(session, current_user.id, update_data)
    return current_user
