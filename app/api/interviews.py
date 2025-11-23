from fastapi import status, APIRouter, Depends, Query, Path, UploadFile, HTTPException, Form
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from pydantic import PositiveInt

from app.core.database import get_db
from app import schemas
from app.cruds import ProjectCRUD, InterviewCRUD
from app.models import User as UserORM, InterviewTypeEnum, InterviewStatusEnum
from app.dependencies import get_current_user, get_file
from app.utils.files import get_type_by_file, save_file

router = APIRouter(prefix="/interviews", tags=["interviews"])


@router.get(
    "/projects/{project_id}",
    status_code=200,
    response_model=schemas.InterviewsGet,
    responses={
        401: {"description": "Unauthorized", "model": schemas.ErrorResponse},
        403: {"description": "Forbidden", "model": schemas.ErrorResponse},
        404: {"description": "Not found", "model": schemas.ErrorResponse}
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
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You are not owner of this project")
    interviews, total = await InterviewCRUD.get_list_by_project(
        session, project, search, offset, limit
    )
    return schemas.InterviewsGet(items=interviews, total=total)


@router.post(
    "/projects/{project_id}/upload",
    response_model=schemas.InterviewBase,
    responses={
        400: {"description": "Bad Request", "model": schemas.ErrorResponse},
        401: {"description": "Unauthorized", "model": schemas.ErrorResponse},
        403: {"description": "Forbidden", "model": schemas.ErrorResponse},
        404: {"description": "Not found", "model": schemas.ErrorResponse},
    },
)
async def upload_file_interview(
        project_id: int = Path(..., description="The identifier of project"),
        file: Optional[UploadFile] = Depends(get_file),
        content: Optional[str] = Form(None),
        current_user: UserORM = Depends(get_current_user),
        session: AsyncSession = Depends(get_db),
):
    project = await ProjectCRUD.get_by_id(session, project_id)
    if project.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You are not owner of this project")
    if file:
        interview_type = get_type_by_file(file)
        file_path = await save_file(file)
        content = None
    elif content:
        interview_type = InterviewTypeEnum.TEXT
        file_path = None
    else:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="File or content must be provided")

    existing_count = await InterviewCRUD.count_by_project(session, project)
    interview_data = schemas.InterviewCreate(
        name=f'Interview №{existing_count + 1}',
        type=interview_type,
        status=InterviewStatusEnum.UPLOADED,
        content=content,
        file_path=file_path,
        project_id=project_id,
    )
    interview = await InterviewCRUD.create(session, interview_data)

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
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You are not owner of project this interview")
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
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You are not owner of project this interview")
    upd_interview = await InterviewCRUD.update(session, interview, update_data)
    return upd_interview


@router.delete(
    "/{interview_id}",
    status_code=204,
    response_model=None,
    responses={
        401: {"description": "Unauthorized", "model": schemas.ErrorResponse},
        404: {"description": "Not found", "model": schemas.ErrorResponse},
    },
)
async def delete_interview_by_id(
        interview_id: PositiveInt = Path(..., description="The identifier of interview"),
        current_user: UserORM = Depends(get_current_user),
        session: AsyncSession = Depends(get_db),
):
    interview = await InterviewCRUD.get_by_id(session, interview_id)
    if interview.project.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You are not owner of this project")
    await InterviewCRUD.remove(session, interview)
