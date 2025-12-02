from fastapi import (
    status,
    APIRouter,
    WebSocket,
    WebSocketDisconnect,
    HTTPException,
    Depends,
)
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Literal

from app import schemas
from app.cruds import InterviewCRUD, AgentSessionsCRUD, AgentSessionMessageCRUD
from app.models import User as UserORM, SessionCallbackEnum, SessionStatusEnum, SessionMessageTypeEnum, SessionMessageRoleEnum
from app.dependencies import get_current_user, get_agent
from app.services import handle_questions_webhook, handle_final_result_webhook, AgentService
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
async def websocket_agent_session(websocket: WebSocket, session_id: str):
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_text()
            
            if data == "ping":
                try:
                    async with get_session_maker() as db_session:
                        db_session_obj = await AgentSessionsCRUD.get_by_external_id(
                            db_session, session_id
                        )
                        
                        if not db_session_obj:
                            await websocket.send_json({
                                "status": "error",
                                "message": "Session not found"
                            })
                            continue
                        
                        questions = [
                            msg.content
                            for msg in db_session_obj.messages
                            if msg.message_type == SessionMessageTypeEnum.QUESTION
                        ]
                        
                        await websocket.send_json({
                            "status": "ok",
                            "session_id": session_id,
                            "session_status": db_session_obj.status.value,
                            "current_iteration": db_session_obj.current_iteration,
                            "questions": questions if questions else [],
                        })
                except Exception as e:
                    await websocket.send_json({
                        "status": "error",
                        "message": f"Server error: {str(e)}"
                    })
            elif data == "disconnect":
                await websocket.close()
                break
            else:
                await websocket.send_json({
                    "status": "error",
                    "message": f"Unknown command: {data}. Use 'ping' or 'disconnect'"
                })
                
    except WebSocketDisconnect:
        pass
    except Exception as e:
        try:
            await websocket.send_json({
                "status": "error",
                "message": str(e)
            })
        except:
            pass


@router.post(
    "/sessions/start",
    status_code=201,
    response_model=schemas.SessionStatusResponse,
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
    interview = await InterviewCRUD.get_by_external_id(session, payload.project_id)
    if not interview:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Interview not found"
        )

    if interview.project.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not owner of this project",
        )

    context_data = {
        "task": payload.context_questions.task,
        "goal": payload.context_questions.goal,
        "value": payload.context_questions.value,
    }

    try:
        await agent.health_check()
        agent_response = await agent.create_interview_session(
            payload.project_id, context_data
        )
    except HTTPException as e:
        raise HTTPException(
            status_code=e.status_code,
            detail=f"Failed to create session on agent: {e.detail}",
        )

    external_session_id = agent_response.get("session_id")
    if not external_session_id:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Agent did not return session_id",
        )

    session_data = schemas.AgentSessionCreate(
        interview_id=interview.id,
        external_session_id=external_session_id,
        status=SessionStatusEnum.PROCESSING,
        current_iteration=1,
    )
    db_session = await AgentSessionsCRUD.create(session, session_data)

    await AgentSessionsCRUD.update(
        session, db_session, {"context_questions": context_data}
    )

    return schemas.SessionStatusResponse(
        session_id=external_session_id,
        status=SessionStatusEnum.PROCESSING,
        current_iteration=1,
    )


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
    session_id: str,
    payload: schemas.SessionAnswerRequest,
    current_user: UserORM = Depends(get_current_user),
    agent: AgentService = Depends(get_agent),
    session: AsyncSession = Depends(get_db),
):
    db_session = await AgentSessionsCRUD.get_by_external_id(session, session_id)
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
        await agent.submit_answers(session_id, payload.answers)
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
    session_id: str,
    current_user: UserORM = Depends(get_current_user),
    agent: AgentService = Depends(get_agent),
    session: AsyncSession = Depends(get_db),
):
    db_session = await AgentSessionsCRUD.get_by_external_id(session, session_id)
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
        await agent.cancel_session(session_id)
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
    session_id: str,
    current_user: UserORM = Depends(get_current_user),
    agent: AgentService = Depends(get_agent),
    session: AsyncSession = Depends(get_db),
):
    db_session = await AgentSessionsCRUD.get_by_external_id(session, session_id)
    if not db_session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Session not found"
        )

    if db_session.interview.project.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not owner of this project",
        )

    questions = [
        msg.content
        for msg in db_session.messages
        if msg.message_type == SessionMessageTypeEnum.QUESTION
    ]

    return schemas.SessionStatusResponse(
        session_id=session_id,
        status=db_session.status,
        current_iteration=db_session.current_iteration,
        questions=questions if questions else None,
    )


@router.post("/webhook/sessions/update")
async def webhook_agent_update():
    return {"message": "Webhook endpoint"}
