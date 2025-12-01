from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_, func, desc, case
from typing import Optional

from app.cruds import BaseCRUD
from app.models import (
    AgentSessions as AgentSessionsORM,
    AgentSessionMessage as AgentSessionsMessageORM,
)


class AgentSessionsCRUD(BaseCRUD):
    model = AgentSessionsORM

    @classmethod
    async def get_by_external_id(
        cls, session: AsyncSession, external_session_id: str
    ) -> Optional[AgentSessionsORM]:
        query = select(cls.model).where(
            cls.model.external_session_id == external_session_id
        )
        result = await session.execute(query)
        return result.scalar_one_or_none()


class AgentSessionMessageCRUD(BaseCRUD):
    model = AgentSessionsMessageORM
