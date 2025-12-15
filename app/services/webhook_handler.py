from fastapi import Request, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Union

from app.cruds import AgentSessionsCRUD, AgentSessionMessageCRUD, ProjectCRUD
from app.models import (
    SessionStatusEnum,
    SessionMessageRoleEnum,
    SessionMessageTypeEnum,
    QuestionStatusEnum,
    AgentSessions,
    AgentSessionMessage,
    AgentSessionStatusEnum,
)
from app import schemas


def normalize_question_status(status_value) -> Union[QuestionStatusEnum, None]:
    if status_value is None:
        return None

    try:
        if isinstance(status_value, QuestionStatusEnum):
            return status_value.value

        status_str = str(status_value).strip().lower()

        if status_str in ["unanswered", "answered", "skipped"]:
            return status_str
        else:
            return "unanswered"

    except Exception as e:
        return "unanswered"


async def handle_questions_webhook(
    request: Request, data: schemas.IterationWithQuestions, session: AsyncSession
):
    request_id = request.headers.get("X-Request-ID")
    if not request_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="X-Request-ID header is required",
        )

    project = await ProjectCRUD.get_by_external_id(session, data.project_id)
    if not project:
        project_data = {
            "external_id": data.project_id,
            "title": None,
        }
        # хЗ че делать, надо обновить external_id
    agent_session = project.session
    agent_session_data = {"external_session_id": data.session_id}

    upd_session = await AgentSessionsCRUD.update(
        session, agent_session, agent_session_data
    )
    session_id = upd_session.id
    for i, question in enumerate(data.questions):
        message_data = {
            "session_id": session_id,
            "role": SessionMessageRoleEnum.AGENT,
            "content": question.question,
            "message_type": SessionMessageTypeEnum.QUESTION,
            "question_id": question.id,
            "question_number": question.question_number,
            "question_status": normalize_question_status(question.status),
            "explanation": question.explanation,
        }
        await AgentSessionMessageCRUD.create(session, message_data)

    agent_session_data = {"status": SessionStatusEnum.WAITING_FOR_ANSWERS}
    await AgentSessionsCRUD.update(session, agent_session, agent_session_data)

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

    try:
        from sqlalchemy import select
        from sqlalchemy.orm import selectinload

        stmt = (
            select(AgentSessions)
            .options(selectinload(AgentSessions.interview))
            .where(AgentSessions.external_session_id == data.session_id)
        )
        result = await session.execute(stmt)
        agent_session = result.scalar_one_or_none()

        if not agent_session:
            return

        if data.session_status == AgentSessionStatusEnum.DONE:
            session_status = SessionStatusEnum.DONE
        elif data.session_status == AgentSessionStatusEnum.ERROR:
            session_status = SessionStatusEnum.ERROR
        else:
            session_status = SessionStatusEnum.PROCESSING

        agent_session.status = session_status
        agent_session.agent_session_status = data.session_status
        agent_session.current_iteration = data.iteration_number

        if data.final_result:
            message = AgentSessionMessage(
                session_id=agent_session.id,
                role=SessionMessageRoleEnum.AGENT,
                content=data.final_result,
                message_type=SessionMessageTypeEnum.RESULT,
            )
            session.add(message)

        interview_status = (
            InterviewStatusEnum.FINISHED.name
            if data.session_status == AgentSessionStatusEnum.DONE
            else InterviewStatusEnum.ACTIVE
        )

        if agent_session.interview:
            agent_session.interview.status = interview_status

        await session.commit()

    except Exception as e:
        await session.rollback()
        import traceback

        traceback.print_exc()

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

    project = await ProjectCRUD.get_by_title(session, data.title)

    if not project:
        return

    upd_project = {
        "external_id": data.id,
    }
    await ProjectCRUD.update(session, project, upd_project)

    return {"status": "ok"}
