from fastapi import (
    status,
    APIRouter,
    WebSocket,
    WebSocketDisconnect,
    HTTPException,
    Depends,
    Request,
    Header,
)
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
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
    Interview,
    InterviewTypeEnum,
    InterviewStatusEnum,
    QuestionStatusEnum,
    AgentSessions,
    AgentSessionMessage,
)
from app.dependencies import get_current_user, get_agent
from app.services import (
    handle_questions_webhook,
    handle_final_result_webhook,
    handle_error_webhook,
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
    request: Request,
    payload: schemas.AgentCallback,
    session: AsyncSession = Depends(get_db),
    x_request_id: Optional[str] = Header(None, alias="X-Request-ID"),
):
    if not x_request_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="X-Request-ID header is required"
        )

    match payload.event:
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

                        messages = []
                        for msg in db_session_obj.messages:
                            message_data = {
                                "role": msg.role.value,
                                "message_type": msg.message_type.value,
                                "content": msg.content,
                                "created_at": msg.created_at.isoformat(),
                            }
                            if msg.question_id:
                                message_data["question_id"] = msg.question_id
                            if msg.question_number:
                                message_data["question_number"] = msg.question_number
                            if msg.question_status:
                                message_data["question_status"] = msg.question_status.value
                            if msg.explanation:
                                message_data["explanation"] = msg.explanation
                            
                            messages.append(message_data)
                        
                        await websocket.send_json(
                            {
                                "status": "ok",
                                "session_id": session_id,
                                "session_status": db_session_obj.status.value,
                                "agent_session_status": db_session_obj.agent_session_status.value if db_session_obj.agent_session_status else None,
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
    interview = None
    if payload.interview_id:
        interview = await InterviewCRUD.get_by_id(session, payload.interview_id)
        if not interview:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Interview not found"
            )
        
        if interview.project.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not owner of this project",
            )
        
        project = interview.project

    elif payload.project_id and payload.context_questions:
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
    
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either interview_id or (project_id + context_questions) is required"
        )

    try:
        await agent.health_check()
        
        agent_response = await agent.create_interview_session(
            interview_id=interview.id if payload.interview_id else None,
            project_id=project.id,
            context_questions=payload.context_questions.model_dump() if payload.context_questions else None,
            callback_url=payload.callback_url
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
        callback_url=payload.callback_url,
        context_questions=payload.context_questions.model_dump() if payload.context_questions else None,
    )
    db_session = await AgentSessionsCRUD.create(session, session_data)

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
    try:
        from sqlalchemy import select
        from sqlalchemy.orm import selectinload
        
        stmt = (
            select(AgentSessions)
            .options(
                selectinload(AgentSessions.interview)
                .selectinload(Interview.project)
            )
            .where(AgentSessions.id == session_id)
        )
        
        result = await session.execute(stmt)
        db_session = result.scalar_one_or_none()
        
        if not db_session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, 
                detail="Session not found"
            )

        if db_session.interview.project.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not owner of this project",
            )

        if db_session.status != SessionStatusEnum.WAITING_FOR_ANSWERS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Session is not waiting for answers"
            )

        external_session_id = db_session.external_session_id
        current_iteration = db_session.current_iteration
 
        answers_to_send = None
        
        if payload.message:
            answers_to_send = payload.message

            message = AgentSessionMessage(
                session_id=db_session.id,
                role=SessionMessageRoleEnum.USER,
                content=payload.message,
                message_type=SessionMessageTypeEnum.ANSWER,
            )
            session.add(message)
            
        elif payload.answers and isinstance(payload.answers, list):
            answers_to_send = []
            for answer in payload.answers:
                message = AgentSessionMessage(
                    session_id=db_session.id,
                    role=SessionMessageRoleEnum.USER,
                    content=answer.answer,
                    message_type=SessionMessageTypeEnum.ANSWER,
                    question_id=answer.question_id,
                    question_status=QuestionStatusEnum.ANSWERED,
                )
                session.add(message)
                answers_to_send.append({
                    "question_id": answer.question_id,
                    "answer": answer.answer
                })
            
        elif payload.answers and isinstance(payload.answers, dict):
            if "question_id" in payload.answers:
                skip_data = payload.answers
                message_content = skip_data.get("reason", "Question skipped")
                
                message = AgentSessionMessage(
                    session_id=db_session.id,
                    role=SessionMessageRoleEnum.USER,
                    content=message_content,
                    message_type=SessionMessageTypeEnum.ANSWER,
                    question_id=skip_data["question_id"],
                    question_status=QuestionStatusEnum.SKIPPED,
                )
                session.add(message)
                answers_to_send = {"skip": skip_data}
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid skip format. Missing question_id"
                )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid answer format. Provide 'message' or 'answers'"
            )

        db_session.status = SessionStatusEnum.PROCESSING
        
        await session.commit()
        
        if answers_to_send:
            await agent.health_check()
            await agent.submit_answers(
                external_session_id,
                current_iteration,
                answers_to_send,
            )
        return {"status": "accepted"}
        
    except HTTPException:
        await session.rollback()
        raise
    except Exception as e:
        await session.rollback()
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )


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
    try:
        from sqlalchemy import select
        from sqlalchemy.orm import selectinload
        
        stmt = (
            select(AgentSessions)
            .options(
                selectinload(AgentSessions.interview)
                .selectinload(Interview.project)
            )
            .where(AgentSessions.id == session_id)
        )
        
        result = await session.execute(stmt)
        db_session = result.scalar_one_or_none()
        
        if not db_session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, 
                detail="Session not found"
            )
        
        if db_session.interview.project.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not owner of this project",
            )
        
        await agent.health_check()
        await agent.cancel_session(db_session.external_session_id)

        db_session.status = SessionStatusEnum.CANCELLED
        
        await session.commit()
        return {"status": "cancelled"}
        
    except HTTPException:
        await session.rollback()
        raise
    except Exception as e:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )


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

    messages = []
    for msg in db_session.messages:
        message_data = schemas.AgentSessionMessageShallow(
            role=msg.role,
            message_type=msg.message_type,
            content=msg.content,
            question_id=msg.question_id,
            question_number=msg.question_number,
            question_status=msg.question_status,
            explanation=msg.explanation,
            created_at=msg.created_at,
        )
        messages.append(message_data)

    return schemas.SessionStatusResponse(
        id=session_id,
        external_session_id=db_session.external_session_id,
        status=db_session.status,
        agent_session_status=db_session.agent_session_status,
        current_iteration=db_session.current_iteration,
        messages=messages if messages else None,
    )
