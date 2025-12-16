from fastapi import APIRouter, Depends, Path, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi.responses import StreamingResponse

from app.core.database import get_db
from app import schemas
from app.models.user import User as UserORM
from app.dependencies import get_current_user
from app.cruds import AgentSessionRequirementCRUD
from app.services import markdown_to_pdf, markdown_to_word

router = APIRouter(prefix="/requirements", tags=["requirements"])


@router.get(
    "/{requirements_id}",
    status_code=200,
    response_model=schemas.RequirementBase,
    responses={
        401: {"description": "Unauthorized"},
        403: {"description": "Forbidden"},
        404: {"description": "Not found"},
        500: {"description": "Internal Server Error"},
    },
)
async def get_requirements(
    requirements_id: int = Path(..., description="The identifier of requirements"),
    current_user: UserORM = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    requirements = await AgentSessionRequirementCRUD.get_by_id(session, requirements_id)

    return requirements

@router.patch(
    "/{requirements_id}",
    status_code=200,
    response_model=schemas.RequirementBase,
    responses={
        401: {"description": "Unauthorized", "model": schemas.ErrorResponse},
        403: {"description": "Not found", "model": schemas.ErrorResponse},
        404: {"description": "Not found", "model": schemas.ErrorResponse},
        500: {"description": "Internal Server Error", "model": schemas.ErrorResponse},
    },
)
async def update_requirements(
    payload: schemas.RequirementUpdate,
    requirements_id: int = Path(..., description="The identifier of requirements"),
    current_user: UserORM = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    existing_requirements = await AgentSessionRequirementCRUD.get_by_id(session, requirements_id)
    update_data = payload.model_dump(exclude_unset=True)

    requirements = await AgentSessionRequirementCRUD.update(session, existing_requirements, update_data)
    return requirements

@router.get(
    "/{requirements_id}/export"
)
async def export_requirements(
    requirements_id: int = Path(..., description="The identifier of session"),
    file: str = Query("docx", description="Export format: 'docx' or 'pdf'"),
    current_user: UserORM = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):

    requirements = await AgentSessionRequirementCRUD.get_by_id(session, requirements_id)

    if file == "pdf":
        file_stream = markdown_to_pdf(requirements.content)
        media_type = "application/pdf"
        filename = f"requirements_{requirements_id}.pdf"
    else:
        file_stream = markdown_to_word(requirements.content)
        media_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        filename = f"requirements_{requirements_id}.docx"

    return StreamingResponse(
        file_stream,
        media_type=media_type,
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )