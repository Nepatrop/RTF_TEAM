from fastapi import APIRouter, Depends, Query, Path
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from pydantic import PositiveInt

from app.core.database import get_db
from app import schemas
from app.models.user import User as UserORM
from app.dependencies import get_current_user
from app.cruds import ProjectCRUD

router = APIRouter(prefix="/projects", tags=["projects"])


@router.get(
    "",
    status_code=200,
    response_model=schemas.ProjectsGet,
    responses={
        401: {"description": "Unauthorized", "model": schemas.ErrorResponse},
    },
)
async def get_projects_list(
    search: Optional[str] = Query(None, description="Search string"),
    offset: int = Query(0, ge=0, description="Offset"),
    limit: int = Query(10, gt=0, le=50, description="Limit"),
    current_user: UserORM = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    projects, total = await ProjectCRUD.get_list_by_user(
        session, current_user, search, offset, limit
    )
    return schemas.ProjectsGet(items=projects, total=total)


@router.post(
    "",
    status_code=201,
    response_model=schemas.ProjectBase,
    responses={
        400: {"description": "Bad Request", "model": schemas.ErrorResponse},
        401: {"description": "Unauthorized", "model": schemas.ErrorResponse},
        422: {
            "description": "Error: Validation Error",
            "model": schemas.RequestValidationError,
        },
    },
)
async def create_project(
    payload: schemas.ProjectCreate,
    current_user: UserORM = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    project_data = schemas.ProjectCreateInternal(
        name=payload.name,
        description=payload.description,
        user_id=current_user.id,
    )
    project = await ProjectCRUD.create(session, project_data)
    return project


@router.get(
    "/{project_id}",
    status_code=200,
    response_model=schemas.ProjectBase,
    responses={
        401: {"description": "Unauthorized", "model": schemas.ErrorResponse},
        404: {"description": "Not found", "model": schemas.ErrorResponse},
    },
)
async def get_project_by_id(
    project_id: PositiveInt = Path(..., description="The identifier of project"),
    current_user: UserORM = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    project = await ProjectCRUD.get_by_id(session, project_id)
    return project


@router.patch(
    "/{project_id}",
    status_code=200,
    response_model=schemas.ProjectBase,
    responses={
        400: {"description": "Bad Request", "model": schemas.ErrorResponse},
        401: {"description": "Unauthorized", "model": schemas.ErrorResponse},
        404: {"description": "Not found", "model": schemas.ErrorResponse},
    },
)
async def update_project_by_id(
    payload: schemas.ProjectUpdate,
    project_id: PositiveInt = Path(..., description="The identifier of project"),
    current_user: UserORM = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    update_data = payload.model_dump(exclude_unset=True)
    project = await ProjectCRUD.update(session, project_id, update_data)
    return project


@router.delete(
    "/{project_id}",
    status_code=204,
    response_model=None,
    responses={
        401: {"description": "Unauthorized", "model": schemas.ErrorResponse},
        404: {"description": "Not found", "model": schemas.ErrorResponse},
    },
)
async def delete_project_by_id(
    project_id: PositiveInt = Path(..., description="The identifier of project"),
    current_user: UserORM = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    await ProjectCRUD.remove(session, project_id)
