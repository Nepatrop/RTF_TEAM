from app.core.config import settings
from app.services import AgentService


async def get_agent():
    service = AgentService(
        url=settings.EXTERNAL_API_URL,
        callback_url=settings.CALLBACK_URL,
    )
    yield service
