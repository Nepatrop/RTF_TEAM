from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session

from app.core.database import get_db

router = APIRouter()

@router.get("/")
async def get_interviews(project_id: int = None, db: Session = Depends(get_db)):
    return []

@router.post("/projects/{project_id}/interviews/upload")
async def upload_interview(
    project_id: int, 
    type: str, 
    file: UploadFile = File(...), 
    db: Session = Depends(get_db)
):
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED
    )

@router.get("/{interview_id}")
async def get_interview(interview_id: int, db: Session = Depends(get_db)):
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED
    )

@router.patch("/{interview_id}")
async def update_interview(interview_id: int, db: Session = Depends(get_db)):
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED
    )

@router.delete("/{interview_id}")
async def delete_interview(interview_id: int, db: Session = Depends(get_db)):
    return {"message": "Delete interview endpoint"}
