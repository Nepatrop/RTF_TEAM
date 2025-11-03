from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.api import auth

app = FastAPI(title=settings.PROJECT_NAME)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Маршруты
app.include_router(auth.router, prefix="/auth", tags=["auth"])
# app.include_router(users.router, prefix="/user", tags=["users"])
# app.include_router(projects.router, prefix="/projects", tags=["projects"])
# app.include_router(interviews.router, prefix="/interviews", tags=["interviews"])
# app.include_router(agent.router, prefix="/agent", tags=["agent"])

@app.get("/")
async def root():
    return {"message": "Business Requirements AI Agent API"}