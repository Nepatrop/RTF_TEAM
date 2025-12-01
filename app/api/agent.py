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

from app import schemas
from app.cruds import InterviewCRUD
from app.models import User as UserORM, SessionCallbackEnum
from app.dependencies import get_current_user
from app.services import handle_questions_webhook, handle_final_result_webhook
from app.core.database import get_db

router = APIRouter(prefix="/agent", tags=["agent"])


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


@router.websocket("/ws/agent/sessions/{session_id}")
async def websocket_agent_session(websocket: WebSocket, session_id: int):
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_text()
            await websocket.send_text(f"Message received: {data}")
    except WebSocketDisconnect:
        pass


@router.post("/sessions/start")
async def start_agent_session(db: Session = Depends(get_db)):
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED)


@router.post("/sessions/{session_id}/answer")
async def answer_agent_question(session_id: int, db: Session = Depends(get_db)):
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED)


@router.post("/sessions/{session_id}/cancel")
async def cancel_agent_session(session_id: int, db: Session = Depends(get_db)):
    return {"message": "Cancel agent session endpoint"}


@router.get("/sessions/{session_id}")
async def get_agent_session(session_id: int, db: Session = Depends(get_db)):
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED)


@router.post("/webhook/agent/sessions/update")
async def webhook_agent_update():
    return {"message": "Webhook endpoint"}
