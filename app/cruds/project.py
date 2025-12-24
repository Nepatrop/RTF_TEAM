from sqlalchemy import select, or_, func, desc, case
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Tuple, Optional
from sqlalchemy.orm import selectinload

from app.exceptions.custom import NotFoundException
from app.cruds import BaseCRUD
from app.models import Project as ProjectORM, AgentSessions
from app.models import User as UserORM


class ProjectCRUD(BaseCRUD):
    model = ProjectORM

    @classmethod
    async def get_list_by_user(
        cls,
        session: AsyncSession,
        user: UserORM,
        search: str,
        offset: int = 0,
        limit: int = 10,
    ) -> Tuple[List[ProjectORM], int]:
        base_query = select(cls.model).where(cls.model.user_id == user.id)

        if search:
            base_query = base_query.where(
                or_(
                    cls.model.title.ilike(f"%{search}%"),
                    cls.model.description.ilike(f"%{search}%"),
                )
            )

        count_query = select(func.count()).select_from(base_query.subquery())
        total_count = await session.scalar(count_query)

        priority = case((cls.model.title.ilike(f"%{search}%"), 1), else_=0)

        paginated_query = (
            base_query.order_by(desc(priority), cls.model.id.desc())
            .offset(offset)
            .limit(limit)
        )

        result = await session.execute(paginated_query)
        items = result.scalars().all()

        return items, total_count

    @classmethod
    async def get_by_external_id(
        cls, session: AsyncSession, external_id: str
    ) -> Optional[ProjectORM]:
        query = select(cls.model).where(cls.model.external_id == external_id)
        result = await session.execute(query)
        return result.scalar_one_or_none()

    @classmethod
    async def get_last(cls, session: AsyncSession) -> Optional[ProjectORM]:
        query = select(cls.model).order_by(cls.model.created_at.desc()).limit(1)
        result = await session.execute(query)
        obj = result.scalar_one_or_none()
        return obj

    @classmethod
    async def get_full_by_id(cls, session: AsyncSession, _id: int):
        query = (
            select(cls.model)
            .where(cls.model.id == _id)
            .options(
                selectinload(cls.model.files),
                selectinload(cls.model.session)
                .selectinload(AgentSessions.requirement)
            )
        )

        result = await session.execute(query)
        obj = result.scalar_one_or_none()

        if obj is None:
            raise NotFoundException(cls.model.__tablename__, "id", _id)

        return obj