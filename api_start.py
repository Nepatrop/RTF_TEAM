import uvicorn
from alembic import command
from alembic.config import Config
from app.core.config import settings
from app.main import app

if __name__ == '__main__':
    alembic_config = Config("alembic.ini")
    command.upgrade(alembic_config, "head")
    uvicorn.run(
        "api_start:app",
        host='0.0.0.0',
        port=8080,
        reload=settings.RELOAD,
    )
