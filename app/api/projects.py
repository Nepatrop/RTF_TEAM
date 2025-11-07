from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.project import ProjectCreate, ProjectResponse

router = APIRouter()


@router.get("/", response_model=list[ProjectResponse])
async def get_projects(db: Session = Depends(get_db)):
    return []


@router.post("/", response_model=ProjectResponse)
async def create_project(project_data: ProjectCreate, db: Session = Depends(get_db)):
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED)


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(project_id: int, db: Session = Depends(get_db)):
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED)


@router.patch("/{project_id}", response_model=ProjectResponse)
async def update_project(project_id: int, db: Session = Depends(get_db)):
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED)


@router.delete("/{project_id}")
async def delete_project(project_id: int, db: Session = Depends(get_db)):
    return {"message": "Delete project endpoint"}
