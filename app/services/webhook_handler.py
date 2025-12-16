from fastapi import Request, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Union

from app.cruds import AgentSessionsCRUD, AgentSessionMessageCRUD, ProjectCRUD, AgentSessionRequirementCRUD
from app.models import (
    SessionStatusEnum,
    SessionMessageRoleEnum,
    SessionMessageTypeEnum,
    QuestionStatusEnum,
    AgentSessions,
    AgentSessionMessage,
    AgentSessionStatusEnum,
    ProjectStatusEnum,
)
from app import schemas


def normalize_question_status(status_value) -> Union[QuestionStatusEnum, None]:
    if status_value is None:
        return None

    try:
        if isinstance(status_value, QuestionStatusEnum):
            return status_value.value

        status_str = str(status_value).strip().lower()

        if status_str == "skiped":
            status_str = "skipped"

        if status_str in ["unanswered", "answered", "skipped"]:
            return status_str
        else:
            return "unanswered"

    except Exception as e:
        return "unanswered"


async def handle_questions_webhook(
    request: Request,
    data: schemas.IterationWithQuestions,
    session: AsyncSession,
):
    request_id = request.headers.get("X-Request-ID")
    if not request_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="X-Request-ID header is required",
        )

    project = await ProjectCRUD.get_last(session)
    project_id = project.id
    agent_session = await AgentSessionsCRUD.get_by_project_id(session, project_id)
    agent_session_id = agent_session.id

    await AgentSessionsCRUD.update(
        session,
        agent_session,
        {
            "external_session_id": data.session_id,
            "current_iteration": data.iteration_number,
        },
    )

    for question in data.questions:
        existing = await AgentSessionMessageCRUD.get_by_external_question_id(
            session, question.id
        )

        normalized_status = normalize_question_status(question.status)

        if existing:
            await AgentSessionMessageCRUD.update(
                session,
                existing,
                {
                    "question_status": normalized_status,
                },
            )
        else:
            await AgentSessionMessageCRUD.create(
                session,
                {
                    "session_id": agent_session_id,
                    "role": SessionMessageRoleEnum.AGENT,
                    "content": question.question,
                    "message_type": SessionMessageTypeEnum.QUESTION,
                    "question_external_id": question.id,
                    "question_number": question.question_number,
                    "question_status": normalized_status,
                    "explanation": question.explanation,
                },
            )

    await AgentSessionsCRUD.update(
        session,
        agent_session,
        {"status": SessionStatusEnum.WAITING_FOR_ANSWERS},
    )

    return {"status": "ok"}


async def handle_final_result_webhook(
    request: Request, data: schemas.SessionDTO, session: AsyncSession
):
    request_id = request.headers.get("X-Request-ID")
    if not request_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="X-Request-ID header is required",
        )

    agent_session = await AgentSessionsCRUD.get_by_external_id(session, data.session_id)
    agent_session_upd = {
        "status": data.session_status.value,
        "current_iteration": data.iteration_number,
    }
    await AgentSessionsCRUD.update(session, agent_session, agent_session_upd)

    if data.final_result:
        message_upd = {
            "session_id": agent_session.id,
            "role": SessionMessageRoleEnum.AGENT,
            "content": data.final_result,
            "message_type": SessionMessageTypeEnum.RESULT,
        }
        await AgentSessionMessageCRUD.create(session, message_upd)
        existing_req = await AgentSessionRequirementCRUD.get_by_session_id(session, agent_session.id)
        if existing_req:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Requirements already exists",
            )
        requirements = {
            "session_id": agent_session.id,
            "content": data.final_result,
        }
        await AgentSessionRequirementCRUD.create(session, requirements)

    project = await ProjectCRUD.get_by_external_id(session, data.project_id)
    if project:
        project_upd = {"status": ProjectStatusEnum.FINISHED}
        await ProjectCRUD.update(session, project, project_upd)
    return {"status": "ok"}


async def handle_error_webhook(
    request: Request, data: schemas.CallbackErrorData, session: AsyncSession
):
    request_id = request.headers.get("X-Request-ID")
    if not request_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="X-Request-ID header is required",
        )

    error_details = data.error.get("details", {})
    session_id = error_details.get("session_id")

    if session_id:
        agent_session = await AgentSessionsCRUD.get_by_external_id(session, session_id)
        if agent_session:
            await AgentSessionsCRUD.update(
                session,
                agent_session,
                {
                    "status": SessionStatusEnum.ERROR,
                    "agent_session_status": AgentSessionStatusEnum.ERROR,
                },
            )


async def handle_project_update_webhook(
    request: Request, data: schemas.CallbackProjectUpdatedData, session: AsyncSession
):
    request_id = request.headers.get("X-Request-ID")
    if not request_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="X-Request-ID header is required",
        )

    project = await ProjectCRUD.get_last(session)

    if not project:
        return

    upd_project = {
        "external_id": data.id,
    }
    await ProjectCRUD.update(session, project, upd_project)

    return {"status": "ok"}
