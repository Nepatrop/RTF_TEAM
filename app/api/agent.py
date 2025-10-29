from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db

router = APIRouter()

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
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED
    )

@router.post("/sessions/{session_id}/answer")
async def answer_agent_question(session_id: int, db: Session = Depends(get_db)):
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED
    )

@router.post("/sessions/{session_id}/cancel")
async def cancel_agent_session(session_id: int, db: Session = Depends(get_db)):
    return {"message": "Cancel agent session endpoint"}

@router.get("/sessions/{session_id}")
async def get_agent_session(session_id: int, db: Session = Depends(get_db)):
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED
    )

@router.post("/webhook/agent/sessions/update")
async def webhook_agent_update():
    return {"message": "Webhook endpoint"}
