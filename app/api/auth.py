from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import (
    get_db,
    create_access_token,
    get_password_hash,
    create_refresh_token,
    verify_password,
)
from app.models.user import User as UserORM
import app.schemas as schemas
from app.cruds import UserCRUD, RefreshTokenCRUD
from app.dependencies import get_current_user

router = APIRouter(prefix="/auth", tags=["auth"])


async def _create_tokens(session: AsyncSession, user: UserORM):
    refresh, expires_at = create_refresh_token(user.id)
    await RefreshTokenCRUD.create(
        session,
        schemas.RefreshTokenCreate(
            token=refresh, user_id=user.id, expires_at=expires_at
        ),
    )
    access = create_access_token(user.id)
    return schemas.Token(access_token=access, refresh_token=refresh)


@router.post(
    "/register",
    status_code=201,
    response_model=schemas.Token,
    responses={
        409: {
            "description": "Conflict: User Already Exists",
            "model": schemas.ErrorResponse,
        },
        422: {
            "description": "Error: Validation Error",
            "model": schemas.RequestValidationError,
        },
        500: {"description": "Internal Server Error", "model": schemas.ErrorResponse},
    },
)
async def register(payload: schemas.Register, session: AsyncSession = Depends(get_db)):
    user = await UserCRUD.get_by_email(session, payload.email)
    if user:
        raise HTTPException(status.HTTP_409_CONFLICT, detail="User Already Exists")

    hash_password = get_password_hash(payload.password)
    user_data = schemas.UserCreate(
        email=payload.email,
        hashed_password=hash_password,
        display_name=payload.display_name,
    )
    new_user = await UserCRUD.create(session, user_data)

    return await _create_tokens(session, new_user)


@router.post(
    "/login",
    status_code=200,
    response_model=schemas.Token,
    responses={
        400: {"description": "Bad request", "model": schemas.ErrorResponse},
        422: {
            "description": "Validation Error",
            "model": schemas.RequestValidationError,
        },
        500: {"description": "Internal Server Error", "model": schemas.ErrorResponse},
    },
)
async def login(payload: schemas.Login, session: AsyncSession = Depends(get_db)):
    user = await UserCRUD.get_by_email(session, payload.email)
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Incorrect email or password")

    return await _create_tokens(session, user)


@router.post(
    "/logout",
    status_code=204,
    response_model=None,
    responses={
        500: {"description": "Internal Server Error", "model": schemas.ErrorResponse},
    },
)
async def logout(
    current_user: UserORM = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    await RefreshTokenCRUD.remove_by_user(session, current_user.id)


@router.post(
    "/refresh",
    response_model=schemas.Token,
    status_code=200,
    responses={
        400: {"description": "Bad Request", "model": schemas.ErrorResponse},
        422: {
            "description": "Validation Error",
            "model": schemas.RequestValidationError,
        },
        500: {"description": "Internal Server Error", "model": schemas.ErrorResponse},
    },
)
async def refresh_token(
    payload: schemas.RefreshToken,
    session: AsyncSession = Depends(get_db),
):
    token = await RefreshTokenCRUD.get_by_token(session, payload.refresh_token)
    if not token:
        raise HTTPException(status_code=400, detail="Invalid refresh token")

    user = await UserCRUD.get_by_id(session, token.user_id)

    return await _create_tokens(session, user)
