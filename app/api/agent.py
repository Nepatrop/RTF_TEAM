from fastapi import (
    status,
    APIRouter,
    WebSocket,
    WebSocketDisconnect,
    HTTPException,
    Depends,
)
from sqlalchemy.ext.asyncio import AsyncSession

from app import schemas
from app.cruds import (
    InterviewCRUD,
    AgentSessionsCRUD,
    AgentSessionMessageCRUD,
    ProjectCRUD,
)
from app.models import (
    User as UserORM,
    SessionCallbackEnum,
    SessionStatusEnum,
    SessionMessageTypeEnum,
    SessionMessageRoleEnum,
    InterviewTypeEnum,
    InterviewStatusEnum,
)
from app.dependencies import get_current_user, get_agent
from app.services import (
    handle_questions_webhook,
    handle_final_result_webhook,
    AgentService,
)
from app.core.database import get_db, session as get_session_maker

router = APIRouter(prefix="/agent", tags=["agent"])
ws_router = APIRouter(tags=["websocket"])


@router.post(
    "/webhook",
    status_code=200,
    response_model=None,
    responses={
        400: {"description": "Bad Request", "model": schemas.ErrorResponse},
        401: {"description": "Unauthorized", "model": schemas.ErrorResponse},
        422: {
            "description": "Error: Validation Error",
            "model": schemas.RequestValidationError,
        },
    },
)
async def webhook_update_session(
    payload: schemas.AgentCallback,
    session: AsyncSession = Depends(get_db),
):
    match payload.event:
        case SessionCallbackEnum.QUESTIONS:
            await handle_questions_webhook(payload.data, session)
        case SessionCallbackEnum.FINAL_RESULT:
            await handle_final_result_webhook(payload.data, session)
        case SessionCallbackEnum.PROJECT_UPDATED:
            pass

    return {"status": "ok"}


@ws_router.websocket("/ws/sessions/{session_id}")
async def websocket_agent_session(websocket: WebSocket, session_id: int):
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_text()

            if data == "ping":
                try:
                    async with get_session_maker() as db_session:
                        db_session_obj = await AgentSessionsCRUD.get_by_id(
                            db_session, session_id
                        )

                        if not db_session_obj:
                            await websocket.send_json(
                                {"status": "error", "message": "Session not found"}
                            )
                            continue

                        messages = [
                            {
                                "role": msg.role.value,
                                "message_type": msg.message_type.value,
                                "content": msg.content,
                                "created_at": msg.created_at.isoformat(),
                            }
                            for msg in db_session_obj.messages
                        ]

                        await websocket.send_json(
                            {
                                "status": "ok",
                                "session_id": session_id,
                                "session_status": db_session_obj.status.value,
                                "current_iteration": db_session_obj.current_iteration,
                                "messages": messages if messages else [],
                            }
                        )
                except Exception as e:
                    await websocket.send_json(
                        {"status": "error", "message": f"Server error: {str(e)}"}
                    )
            elif data == "disconnect":
                await websocket.close()
                break
            else:
                await websocket.send_json(
                    {
                        "status": "error",
                        "message": f"Unknown command: {data}. Use 'ping' or 'disconnect'",
                    }
                )

    except WebSocketDisconnect:
        pass
    except Exception as e:
        try:
            await websocket.send_json({"status": "error", "message": str(e)})
        except:
            pass


@router.post(
    "/sessions/start",
    status_code=201,
    response_model=schemas.AgentSessionBase,
    responses={
        400: {"description": "Bad Request", "model": schemas.ErrorResponse},
        401: {"description": "Unauthorized", "model": schemas.ErrorResponse},
        404: {"description": "Not found", "model": schemas.ErrorResponse},
        500: {"description": "Internal Server Error", "model": schemas.ErrorResponse},
    },
)
async def start_agent_session(
    payload: schemas.SessionStartRequest,
    current_user: UserORM = Depends(get_current_user),
    agent: AgentService = Depends(get_agent),
    session: AsyncSession = Depends(get_db),
):
    project = await ProjectCRUD.get_by_id(session, payload.project_id)
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
        project_id=payload.project_id,
    )
    interview = await InterviewCRUD.create(session, interview_data)

    questions_start = [
        "Что хотите сделать?",
        "Какая цель у этой задачи?",
        "Какую ценность несёт данное нововведение?",
    ]
    answers = [
        payload.context_questions.task,
        payload.context_questions.goal,
        payload.context_questions.value,
    ]
    # TO:DO должны сделать файлы необязательными -
    # получим ид проекта и запишем в session_data.external_session_id

    # try:
    #     await agent.health_check()
    #      agent_project = await agent.create_project(agent_project_name)
    #     agent_response = await agent.create_interview_session(
    #         interview.external_id, answers
    #     )
    # except HTTPException as e:
    #     raise HTTPException(
    #         status_code=e.status_code,
    #         detail=f"Failed to create session on agent: {e.detail}",
    #     )

    # external_session_id = agent_response.get("session_id")
    # if not external_session_id:
    #     raise HTTPException(
    #         status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
    #         detail="Agent did not return session_id",
    #     )

    session_data = schemas.AgentSessionCreate(
        interview_id=interview.id,
        external_session_id="asd",
        status=SessionStatusEnum.PROCESSING,
        current_iteration=1,
    )
    db_session = await AgentSessionsCRUD.create(session, session_data)
    agent_session_id = db_session.id
    for question_text, answer_text in zip(questions_start, answers):
        question_msg = schemas.AgentSessionMessageCreate(
            session_id=agent_session_id,
            role=SessionMessageRoleEnum.AGENT,
            content=question_text,
            message_type=SessionMessageTypeEnum.QUESTION,
        )
        await AgentSessionMessageCRUD.create(session, question_msg)

        answer_msg = schemas.AgentSessionMessageCreate(
            session_id=agent_session_id,
            role=SessionMessageRoleEnum.USER,
            content=answer_text,
            message_type=SessionMessageTypeEnum.ANSWER,
        )
        await AgentSessionMessageCRUD.create(session, answer_msg)

    return db_session


@router.post(
    "/sessions/{session_id}/answers",
    status_code=200,
    response_model=dict,
    responses={
        400: {"description": "Bad Request", "model": schemas.ErrorResponse},
        401: {"description": "Unauthorized", "model": schemas.ErrorResponse},
        404: {"description": "Not found", "model": schemas.ErrorResponse},
        500: {"description": "Internal Server Error", "model": schemas.ErrorResponse},
    },
)
async def submit_text_answers(
    session_id: int,
    payload: schemas.SessionAnswerRequest,
    current_user: UserORM = Depends(get_current_user),
    agent: AgentService = Depends(get_agent),
    session: AsyncSession = Depends(get_db),
):
    db_session = await AgentSessionsCRUD.get_by_id(session, session_id)
    if not db_session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Session not found"
        )

    if db_session.interview.project.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not owner of this project",
        )

    try:
        await agent.health_check()
        await agent.submit_answers(
            db_session.external_session_id,
            db_session.current_iteration,
            payload.answers,
        )
    except HTTPException as e:
        raise HTTPException(
            status_code=e.status_code, detail=f"Failed to submit answers: {e.detail}"
        )

    answer_message = schemas.AgentSessionMessageCreate(
        session_id=db_session.id,
        role=SessionMessageRoleEnum.USER,
        content=payload.answers,
        message_type=SessionMessageTypeEnum.ANSWER,
    )
    await AgentSessionMessageCRUD.create(session, answer_message)
    session_data = {"status": SessionStatusEnum.PROCESSING}
    await AgentSessionsCRUD.update(session, db_session, session_data)

    return {"status": "accepted"}


@router.post(
    "/sessions/{session_id}/cancel",
    status_code=200,
    response_model=dict,
    responses={
        401: {"description": "Unauthorized", "model": schemas.ErrorResponse},
        404: {"description": "Not found", "model": schemas.ErrorResponse},
        500: {"description": "Internal Server Error", "model": schemas.ErrorResponse},
    },
)
async def cancel_session(
    session_id: int,
    current_user: UserORM = Depends(get_current_user),
    agent: AgentService = Depends(get_agent),
    session: AsyncSession = Depends(get_db),
):
    db_session = await AgentSessionsCRUD.get_by_id(session, session_id)
    if not db_session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Session not found"
        )

    if db_session.interview.project.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not owner of this project",
        )

    try:
        await agent.health_check()
        await agent.cancel_session(db_session.external_session_id)
    except HTTPException as e:
        raise HTTPException(
            status_code=e.status_code, detail=f"Failed to cancel session: {e.detail}"
        )

    await AgentSessionsCRUD.update(
        session, db_session, {"status": SessionStatusEnum.CANCELLED}
    )

    return {"status": "cancelled"}


@router.get(
    "/sessions/{session_id}",
    status_code=200,
    response_model=schemas.SessionStatusResponse,
    responses={
        401: {"description": "Unauthorized", "model": schemas.ErrorResponse},
        404: {"description": "Not found", "model": schemas.ErrorResponse},
        500: {"description": "Internal Server Error", "model": schemas.ErrorResponse},
    },
)
async def get_session_status(
    session_id: int,
    current_user: UserORM = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    db_session = await AgentSessionsCRUD.get_by_id(session, session_id)
    if not db_session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Session not found"
        )

    if db_session.interview.project.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not owner of this project",
        )

    messages = [
        {
            "role": msg.role.value,
            "message_type": msg.message_type.value,
            "content": msg.content,
            "created_at": msg.created_at.isoformat(),
        }
        for msg in db_session.messages
    ]

    return schemas.SessionStatusResponse(
        id=session_id,
        external_session_id=db_session.external_session_id,
        status=db_session.status,
        current_iteration=db_session.current_iteration,
        messages=messages if messages else None,
    )
