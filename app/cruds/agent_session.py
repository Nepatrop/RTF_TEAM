from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_, func, desc, case
from typing import Optional

from app.cruds import BaseCRUD
from app.models import (
    AgentSessions as AgentSessionsORM,
    AgentSessionMessage as AgentSessionsMessageORM,
    SessionMessageTypeEnum, AgentSessionRequirement as AgentSessionRequirementORM,
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

    @classmethod
    async def get_by_project_id(
        cls, session: AsyncSession, project_id: int
    ) -> Optional[AgentSessionsORM]:
        query = select(cls.model).where(cls.model.project_id == project_id)
        result = await session.execute(query)
        return result.scalar_one_or_none()


class AgentSessionMessageCRUD(BaseCRUD):
    model = AgentSessionsMessageORM

    @classmethod
    async def get_by_external_question_id(
        cls, session: AsyncSession, question_id: str
    ) -> Optional[AgentSessionsMessageORM]:
        query = select(cls.model).where(cls.model.question_external_id == question_id)
        result = await session.execute(query)
        return result.scalar_one_or_none()

    @classmethod
    async def answer_exists(
        cls,
        session: AsyncSession,
        question_id: int,
    ) -> bool:
        result = await session.execute(
            select(cls.model.id).where(
                cls.model.parent_message_id == question_id,
                cls.model.message_type == SessionMessageTypeEnum.ANSWER,
            )
        )
        return result.first() is not None

class AgentSessionRequirementCRUD(BaseCRUD):
    model = AgentSessionRequirementORM

    @classmethod
    async def get_by_session_id(
            cls, session: AsyncSession, session_id: int
    ) -> Optional[AgentSessionRequirementORM]:
        query = select(cls.model).where(cls.model.session_id == session_id)
        result = await session.execute(query)
        return result.scalar_one_or_none()