from fastapi import (
    status,
    APIRouter,
    Depends,
    Query,
    Path,
    UploadFile,
    HTTPException,
)
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List
from pydantic import PositiveInt

from app.core.database import get_db
from app import schemas
from app.cruds import ProjectCRUD, InterviewCRUD, InterviewFileCRUD
from app.models import User as UserORM, InterviewTypeEnum, InterviewStatusEnum
from app.dependencies import (
    get_current_user,
    get_audio_files,
    get_text_files,
    get_agent,
)
from app.services import AgentService
from app.utils.files import save_file_with_meta

router = APIRouter(prefix="/interviews", tags=["interviews"])


@router.get(
    "/projects/{project_id}",
    status_code=200,
    response_model=schemas.InterviewsGet,
    responses={
        401: {"description": "Unauthorized", "model": schemas.ErrorResponse},
        403: {"description": "Forbidden", "model": schemas.ErrorResponse},
        404: {"description": "Not found", "model": schemas.ErrorResponse},
    },
)
async def get_interviews_list(
    project_id: PositiveInt = Path(..., description="The identifier of project"),
    search: Optional[str] = Query(None, description="Search string"),
    offset: int = Query(0, ge=0, description="Offset"),
    limit: int = Query(10, gt=0, le=50, description="Limit"),
    current_user: UserORM = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    project = await ProjectCRUD.get_by_id(session, project_id)
    if project.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not owner of this project",
        )
    interviews, total = await InterviewCRUD.get_list_by_project(
        session, project, search, offset, limit
    )
    return schemas.InterviewsGet(items=interviews, total=total)


@router.post(
    "/projects/{project_id}/upload-text",
    response_model=schemas.InterviewBase,
    responses={
        400: {"description": "Invalid file format", "model": schemas.ErrorResponse},
        401: {"description": "Unauthorized", "model": schemas.ErrorResponse},
        403: {
            "description": "You are not owner of this project",
            "model": schemas.ErrorResponse,
        },
        404: {"description": "Not found", "model": schemas.ErrorResponse},
    },
)
async def upload_text_interview(
    project_id: int = Path(..., description="The identifier of project"),
    files: List[UploadFile] = Depends(get_text_files),
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

    existing_count = await InterviewCRUD.count_by_project(session, project)
    interview_data = schemas.InterviewCreate(
        name=f"Interview №{existing_count + 1}",
        type=InterviewTypeEnum.TEXT,
        status=InterviewStatusEnum.ACTIVE,
        project_id=project_id,
    )
    interview = await InterviewCRUD.create(session, interview_data)

    saved_meta = []
    for file in files:
        meta = await save_file_with_meta(file)
        saved_meta.append(meta)
        file_data = schemas.InterviewFileCreate(
            interview_id=interview.id,
            original_name=meta["name"],
            file_path=meta["path"],
            file_size=meta["size"],
            mime_type=meta["mime_type"],
        )
        await InterviewFileCRUD.create(session, file_data)

    # Взаимодействуем с агентом
    agent_project_name = f"{project.name}: {interview.name}"
    try:
        await agent.health_check()
        agent_project = await agent.create_project(agent_project_name, saved_meta)
    except HTTPException as e:
        raise HTTPException(
            status_code=e.status_code,
            detail=f"Failed to create project in agent: {e.detail}",
        )

    external_id = agent_project.get("id")
    if not external_id:
        raise HTTPException(500, "Agent did not return external id")

    upd_data = {
        "external_id": external_id,
    }
    await InterviewCRUD.update(session, upd_data, interview)

    return interview


@router.get(
    "/{interview_id}",
    status_code=200,
    response_model=schemas.InterviewBase,
    responses={
        401: {"description": "Unauthorized", "model": schemas.ErrorResponse},
        403: {"description": "Forbidden", "model": schemas.ErrorResponse},
        404: {"description": "Not found", "model": schemas.ErrorResponse},
    },
)
async def get_interview_by_id(
    interview_id: PositiveInt = Path(..., description="The identifier of interview"),
    current_user: UserORM = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    interview = await InterviewCRUD.get_by_id(session, interview_id)
    if interview.project.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not owner of project this interview",
        )
    return interview


@router.patch(
    "/{interview_id}",
    status_code=200,
    response_model=schemas.InterviewBase,
    responses={
        400: {"description": "Bad Request", "model": schemas.ErrorResponse},
        401: {"description": "Unauthorized", "model": schemas.ErrorResponse},
        404: {"description": "Not found", "model": schemas.ErrorResponse},
    },
)
async def update_interview_by_id(
    payload: schemas.InterviewUpdate,
    interview_id: PositiveInt = Path(..., description="The identifier of interview"),
    current_user: UserORM = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    update_data = payload.model_dump(exclude_unset=True)
    interview = await InterviewCRUD.get_by_id(session, interview_id)
    if interview.project.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not owner of project this interview",
        )
    upd_interview = await InterviewCRUD.update(session, interview, update_data)
    return upd_interview


@router.delete(
    "/{interview_id}",
    status_code=204,
    response_model=None,
    responses={
        400: {"description": "Unauthorized", "model": schemas.ErrorResponse},
        401: {"description": "Unauthorized", "model": schemas.ErrorResponse},
        404: {"description": "Not found", "model": schemas.ErrorResponse},
    },
)
async def delete_interview_by_id(
    interview_id: PositiveInt = Path(..., description="The identifier of interview"),
    current_user: UserORM = Depends(get_current_user),
    agent: AgentService = Depends(get_agent),
    session: AsyncSession = Depends(get_db),
):
    interview = await InterviewCRUD.get_by_id(session, interview_id)
    if interview.project.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not owner of this project",
        )
    if interview.external_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="External id for this interview not found",
        )

    try:
        await agent.health_check()
        await agent.delete_project(interview.external_id)
    except HTTPException as e:
        raise HTTPException(
            status_code=e.status_code,
            detail=f"Failed to delete project on agent: {e.detail}",
        )
    await InterviewCRUD.remove(session, interview)


@router.get(
    "/{interview_id}/session",
    status_code=200,
    response_model=schemas.AgentSessionBase,
    responses={
        401: {"description": "Unauthorized", "model": schemas.ErrorResponse},
        403: {"description": "Forbidden", "model": schemas.ErrorResponse},
        404: {"description": "Not found", "model": schemas.ErrorResponse},
    },
)
async def get_session_data_by_interview_id(
    interview_id: PositiveInt = Path(..., description="The identifier of interview"),
    current_user: UserORM = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    interview = await InterviewCRUD.get_by_id(session, interview_id)
    if interview.project.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not owner of project this interview",
        )
    interview_session = interview.session
    if not interview_session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found",
        )
    return interview_session
