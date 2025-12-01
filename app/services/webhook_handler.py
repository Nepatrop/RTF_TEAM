from sqlalchemy.ext.asyncio import AsyncSession

from app.cruds import InterviewCRUD, AgentSessionsCRUD, AgentSessionMessageCRUD
from app.models import (
    SessionStatusEnum,
    SessionMessageRoleEnum,
    SessionMessageTypeEnum,
    InterviewStatusEnum,
)
from app import schemas


async def handle_questions_webhook(data: schemas.QuestionsData, session: AsyncSession):
    interview = await InterviewCRUD.get_by_external_id(session, data.project_id)
    if not interview:
        return

    agent_session = await AgentSessionsCRUD.get_by_external_id(session, data.session_id)

    if not agent_session:
        session_agent_data = schemas.AgentSessionCreate(
            interview_id=interview.id,
            external_session_id=data.session_id,
            status=SessionStatusEnum.PROCESSING,
            current_iteration=data.iteration_number,
        )
        agent_session = await AgentSessionsCRUD.create(session, session_agent_data)
    agent_session_id = agent_session.id

    upd_agent_session_data = {
        "status": SessionStatusEnum.PROCESSING,
        "current_iteration": data.iteration_number,
    }
    await AgentSessionsCRUD.update(session, agent_session, upd_agent_session_data)

    for question_text in data.questions:
        agent_message_data = schemas.AgentSessionMessageCreate(
            session_id=agent_session_id,
            role=SessionMessageRoleEnum.AGENT,
            content=question_text,
            message_type=SessionMessageTypeEnum.QUESTION,
            iteration_number=data.iteration_number,
        )
        await AgentSessionMessageCRUD.create(session, agent_message_data)

    session_data = {
        "status": SessionStatusEnum.WAITING_FOR_ANSWERS,
    }
    await AgentSessionsCRUD.update(session, agent_session, session_data)
    interview_data = {
        "status": InterviewStatusEnum.QUESTION,
    }
    await InterviewCRUD.update(session, interview, interview_data)


async def handle_final_result_webhook(
    data: schemas.FinalResultData, session: AsyncSession
):
    agent_session = await AgentSessionsCRUD.get_by_external_id(session, data.session_id)
    interview = await InterviewCRUD.get_by_external_id(session, data.project_id)
    if not agent_session or interview:
        return
    agent_session_id = agent_session.id

    if len(data.error) > 0:
        agent_session_data = {
            "status": SessionStatusEnum.ERROR,
        }
        await AgentSessionsCRUD.update(session, agent_session, agent_session_data)
        interview_status = InterviewStatusEnum.ERROR
    else:

        agent_session_message_data = schemas.AgentSessionMessageCreate(
            session_id=agent_session_id,
            role=SessionMessageRoleEnum.AGENT,
            message_type=SessionMessageTypeEnum.RESULT,
            content=data.result,
            iteration_number=agent_session.current_iteration,
        )
        await AgentSessionsCRUD.update(
            session, agent_session, {"status": SessionStatusEnum.DONE}
        )

        await AgentSessionMessageCRUD.create(session, agent_session_message_data)
        interview_status = InterviewStatusEnum.DONE

    await InterviewCRUD.update(session, interview, {"status": interview_status})
