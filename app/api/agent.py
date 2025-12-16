from fastapi import (
    status,
    APIRouter,
    WebSocket,
    WebSocketDisconnect,
    HTTPException,
    Depends,
    Request,
    Header,
    Path,
)
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from app import schemas
from app.cruds import (
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
    QuestionStatusEnum,
)
from app.dependencies import get_current_user, get_agent
from app.services import (
    handle_questions_webhook,
    handle_final_result_webhook,
    handle_error_webhook,
    handle_project_update_webhook,
    AgentService,
)
from app.core.database import get_db, session as get_session_maker
from pydantic import PositiveInt

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
    request: Request,
    payload: schemas.AgentCallback,
    session: AsyncSession = Depends(get_db),
    x_request_id: str = Header(..., alias="X-Request-ID"),
):
    if not x_request_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="X-Request-ID header is required",
        )

    match payload.event:
        case SessionCallbackEnum.PROJECT_UPDATED:
            await handle_project_update_webhook(request, payload.data, session)
        case SessionCallbackEnum.QUESTIONS:
            await handle_questions_webhook(request, payload.data, session)
        case SessionCallbackEnum.FINAL_RESULT:
            await handle_final_result_webhook(request, payload.data, session)
        case SessionCallbackEnum.ERROR:
            await handle_error_webhook(request, payload.data, session)

    return {"status": "ok", "request_id": x_request_id}


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

                        questions = sorted(
                            [
                                m
                                for m in db_session_obj.messages
                                if m.message_type == SessionMessageTypeEnum.QUESTION
                            ],
                            key=lambda x: x.question_number,
                        )
                        answers = [
                            m
                            for m in db_session_obj.messages
                            if m.message_type == SessionMessageTypeEnum.ANSWER
                        ]

                        dialogue = []
                        stop = False
                        for q in questions:
                            if stop:
                                break

                            answer = next(
                                (a for a in answers if a.parent_message_id == q.id),
                                None,
                            )

                            if answer:
                                answer_dict = {
                                    "id": answer.id,
                                    "content": answer.content,
                                    "created_at": answer.created_at.isoformat(),
                                }
                                if answer.is_skipped:
                                    answer_dict["is_skipped"] = True

                                dialogue.append(
                                    {
                                        "question": {
                                            "id": q.id,
                                            "content": q.content,
                                            "question_number": q.question_number,
                                            "status": q.question_status.value,
                                            "explanation": q.explanation,
                                            "created_at": q.created_at.isoformat(),
                                        },
                                        "answer": answer_dict,
                                    }
                                )
                            else:
                                dialogue.append(
                                    {
                                        "question": {
                                            "id": q.id,
                                            "content": q.content,
                                            "question_number": q.question_number,
                                            "status": q.question_status.value,
                                            "explanation": q.explanation,
                                            "created_at": q.created_at.isoformat(),
                                        },
                                        "answer": None,
                                    }
                                )
                                stop = True

                        payload = {
                            "status": "ok",
                            "session_id": session_id,
                            "session_status": db_session_obj.status.value,
                            "current_iteration": db_session_obj.current_iteration,
                            "dialogue": dialogue,
                        }

                        await websocket.send_json(payload)

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
    "/sessions/start/project/{project_id}",
    status_code=201,
    response_model=schemas.AgentSessionBase,
    responses={
        400: {"description": "Bad Request", "model": schemas.ErrorResponse},
        401: {"description": "Unauthorized", "model": schemas.ErrorResponse},
        404: {"description": "Not found", "model": schemas.ErrorResponse},
        500: {"description": "Internal Server Error", "model": schemas.ErrorResponse},
    },
)
async def start_agent_session_on_project(
    payload: schemas.SessionStartProjectContextRequest,
    project_id: PositiveInt = Path(..., description="The identifier of project"),
    current_user: UserORM = Depends(get_current_user),
    agent: AgentService = Depends(get_agent),
    session: AsyncSession = Depends(get_db),
):
    project = await ProjectCRUD.get_by_id(session, project_id)

    if not project.external_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You can not start session with this project",
        )

    try:
        await agent.health_check()

        await agent.create_session_on_project(project.external_id, payload.user_goal)
    except HTTPException as e:
        raise HTTPException(
            status_code=e.status_code,
            detail=f"Failed to create session on agent: {e.detail}",
        )
    session_data = {
        "project_id": project.id,
        "user_goal": payload.user_goal,
        "status": SessionStatusEnum.PROCESSING,
    }

    agent_session = await AgentSessionsCRUD.create(session, session_data)

    return agent_session


@router.post(
    "/sessions/start/context",
    status_code=201,
    response_model=schemas.AgentSessionBase,
    responses={
        400: {"description": "Bad Request", "model": schemas.ErrorResponse},
        401: {"description": "Unauthorized", "model": schemas.ErrorResponse},
        404: {"description": "Not found", "model": schemas.ErrorResponse},
        500: {"description": "Internal Server Error", "model": schemas.ErrorResponse},
    },
)
async def start_agent_session_on_context(
    payload: schemas.SessionStartManualContextRequest,
    current_user: UserORM = Depends(get_current_user),
    agent: AgentService = Depends(get_agent),
    session: AsyncSession = Depends(get_db),
):
    try:
        await agent.health_check()

        await agent.create_interview_session_on_context(
            payload.context_questions, payload.user_goal
        )
    except HTTPException as e:
        raise HTTPException(
            status_code=e.status_code,
            detail=f"Failed to create session on agent: {e.detail}",
        )
    session_data = {
        "status": SessionStatusEnum.PROCESSING,
    }

    agent_session = await AgentSessionsCRUD.create(session, session_data)

    return agent_session


@router.post(
    "/sessions/{session_id}/answer/{question_id}",
    status_code=200,
    response_model=schemas.UserSessionAnswerShallow,
    responses={
        400: {"description": "Bad Request", "model": schemas.ErrorResponse},
        401: {"description": "Unauthorized", "model": schemas.ErrorResponse},
        404: {"description": "Not found", "model": schemas.ErrorResponse},
        500: {"description": "Internal Server Error", "model": schemas.ErrorResponse},
    },
)
async def submit_text_answers(
    payload: schemas.SessionAnswerRequest,
    session_id: PositiveInt = Path(..., description="The identifier of session"),
    question_id: int = Path(..., description="The identifier of question"),
    current_user: UserORM = Depends(get_current_user),
    agent: AgentService = Depends(get_agent),
    session: AsyncSession = Depends(get_db),
):
    question = await AgentSessionMessageCRUD.get_by_id(session, question_id)
    if not question:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Question not found"
        )
    agent_session = await AgentSessionsCRUD.get_by_id(session, session_id)
    project = await ProjectCRUD.get_by_id(session, agent_session.project_id)
    if project.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not owner of this project",
        )

    if agent_session.status != SessionStatusEnum.WAITING_FOR_ANSWERS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Session is not waiting for answers",
        )

    message_data = {
        "session_id": agent_session.id,
        "parent_message_id": question.id,
        "role": SessionMessageRoleEnum.USER,
        "content": payload.answer,
        "is_skipped": payload.is_skipped,
        "message_type": SessionMessageTypeEnum.ANSWER,
    }

    message = await AgentSessionMessageCRUD.create(session, message_data)
    question_external_id = question.question_external_id

    try:
        await agent.health_check()
        await agent.submit_text_answer(
            session_id, question_external_id, payload.answer, payload.is_skipped
        )
    except HTTPException as e:
        raise HTTPException(
            status_code=e.status_code,
            detail=f"Failed to submit answer in agent: {e.detail}",
        )
    return message


@router.post(
    "/sessions/{session_id}/cancel",
    status_code=200,
    response_model=schemas.AgentSessionMessageShallow,
    responses={
        401: {"description": "Unauthorized", "model": schemas.ErrorResponse},
        404: {"description": "Not found", "model": schemas.ErrorResponse},
        500: {"description": "Internal Server Error", "model": schemas.ErrorResponse},
    },
)
async def cancel_session(
    session_id: PositiveInt = Path(..., description="The identifier of session"),
    current_user: UserORM = Depends(get_current_user),
    agent: AgentService = Depends(get_agent),
    session: AsyncSession = Depends(get_db),
):
    agent_session = await AgentSessionsCRUD.get_by_id(session, session_id)

    if agent_session.project.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not owner of this project",
        )

    try:
        await agent.health_check()
        await agent.cancel_session(session_id)
    except HTTPException as e:
        raise HTTPException(
            status_code=e.status_code,
            detail=f"Failed to submit answer in agent: {e.detail}",
        )

    agent_session_data = {
        "status": SessionStatusEnum.CANCELLED,
    }
    agent_session = await AgentSessionsCRUD.update(
        session, agent_session, agent_session_data
    )

    return agent_session


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
    session_id: PositiveInt = Path(..., description="The identifier of session"),
    current_user: UserORM = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    agent_session = await AgentSessionsCRUD.get_by_id(session, session_id)

    if agent_session.project.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not owner of this project",
        )

    messages = []
    for msg in agent_session.messages:
        message_data = schemas.AgentSessionMessageShallow(
            role=msg.role,
            message_type=msg.message_type,
            content=msg.content,
            question_external_id=msg.question_external_id,
            question_number=msg.question_number,
            question_status=msg.question_status,
            explanation=msg.explanation,
            created_at=msg.created_at,
        )
        messages.append(message_data)

    return schemas.SessionStatusResponse(
        id=session_id,
        external_session_id=agent_session.external_session_id,
        status=agent_session.status,
        current_iteration=agent_session.current_iteration,
        messages=messages if messages else None,
    )
