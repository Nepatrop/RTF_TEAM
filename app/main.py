from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging

from app.core.config import settings
from app.api import auth, user, projects, interviews, agent
from app.exceptions import init_exception_handlers

app = FastAPI(title=settings.PROJECT_NAME)
# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# Exceptions
init_exception_handlers(app)

# Маршруты
app.include_router(auth.router)
app.include_router(user.router)
app.include_router(projects.router)
app.include_router(interviews.router)
app.include_router(agent.router)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


@app.get("/")
async def root():
    return {"project": settings.PROJECT_NAME, "status": "active"}
