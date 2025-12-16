from fastapi import status, APIRouter, Depends, Query, Path, HTTPException, Form
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List
from pydantic import PositiveInt

from app.core.database import get_db
from app import schemas
from app.dependencies import (
    get_text_files,
    get_agent,
)
from app.models import User as UserORM, ProjectStatusEnum
from app.dependencies import get_current_user
from app.cruds import ProjectCRUD, ProjectFileCRUD
from app.services import AgentService
from app.utils import save_file_with_meta

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
        401: {"description": "Unauthorized", "model": schemas.ErrorResponse},
        502: {
            "description": "Agent service HTTP error",
            "model": schemas.ErrorResponse,
        },
    },
)
async def create_project(
    title: str = Form(...),
    description: str = Form(...),
    files: List = Depends(get_text_files),
    current_user: UserORM = Depends(get_current_user),
    agent: AgentService = Depends(get_agent),
    session: AsyncSession = Depends(get_db),
):
    project_data = {
        "title": title,
        "description": description,
        "status": ProjectStatusEnum.ACTIVE,
        "user_id": current_user.id,
    }

    project = await ProjectCRUD.create(session, project_data)
    if not files:
        return project

    saved_meta = []
    for file in files:
        meta = await save_file_with_meta(file)
        saved_meta.append(meta)
        file_data = {
            "project_id": project.id,
            "original_name": meta["name"],
            "file_path": meta["path"],
            "file_size": meta["size"],
            "mime_type": meta["mime_type"],
        }

        await ProjectFileCRUD.create(session, file_data)

    try:
        await agent.health_check()
        await agent.create_project(title, description, saved_meta)
    except HTTPException as e:
        raise HTTPException(
            status_code=e.status_code,
            detail=f"Failed to create project in agent: {e.detail}",
        )

    return project


@router.get(
    "/{project_id}",
    status_code=200,
    response_model=schemas.ProjectBase,
    responses={
        400: {
            "description": "You are not owner of this project",
            "model": schemas.ErrorResponse,
        },
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
    if project.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not owner of this project",
        )
    return project


@router.patch(
    "/{project_id}",
    status_code=200,
    response_model=schemas.ProjectBase,
    responses={
        400: {
            "description": "File field is required | You are not owner of this project| External id for this project not found",
            "model": schemas.ErrorResponse,
        },
        401: {"description": "Unauthorized", "model": schemas.ErrorResponse},
        403: {"description": "Forbidden", "model": schemas.ErrorResponse},
        404: {"description": "Not found", "model": schemas.ErrorResponse},
    },
)
async def add_files_to_project_by_id(
    project_id: PositiveInt = Path(..., description="The identifier of project"),
    files: List = Depends(get_text_files),
    current_user: UserORM = Depends(get_current_user),
    agent: AgentService = Depends(get_agent),
    session: AsyncSession = Depends(get_db),
):
    if not files:
        raise HTTPException(status_code=400, detail="File field is required")

    project = await ProjectCRUD.get_by_id(session, project_id)
    if project.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not owner of this project",
        )
    if project.external_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="External id for this project not found",
        )

    saved_meta = []
    for file in files:
        meta = await save_file_with_meta(file)
        saved_meta.append(meta)
        file_data = {
            "project_id": project.id,
            "original_name": meta["name"],
            "file_path": meta["path"],
            "file_size": meta["size"],
            "mime_type": meta["mime_type"],
        }

        await ProjectFileCRUD.create(session, file_data)

    try:
        await agent.health_check()
        await agent.add_files_to_project(project.external_id, saved_meta)
    except HTTPException as e:
        raise HTTPException(
            status_code=e.status_code,
            detail=f"Failed to create project in agent: {e.detail}",
        )
    return project


@router.delete(
    "/{project_id}",
    status_code=204,
    response_model=None,
    responses={
        401: {"description": "Unauthorized", "model": schemas.ErrorResponse},
        403: {"description": "Forbidden", "model": schemas.ErrorResponse},
        404: {"description": "Not found", "model": schemas.ErrorResponse},
    },
)
async def delete_project_by_id(
    project_id: PositiveInt = Path(..., description="The identifier of project"),
    current_user: UserORM = Depends(get_current_user),
    agent: AgentService = Depends(get_agent),
    session: AsyncSession = Depends(get_db),
):
    project = await ProjectCRUD.get_by_id(session, project_id)
    if project.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not owner of this project",
        )
    if project.external_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="External id for this project not found",
        )

    try:
        await agent.health_check()
        await agent.delete_project(project.external_id)
    except HTTPException as e:
        raise HTTPException(
            status_code=e.status_code,
            detail=f"Failed to delete project on agent: {e.detail}",
        )
    await ProjectCRUD.remove(session, project)
