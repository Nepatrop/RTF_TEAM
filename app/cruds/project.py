from sqlalchemy import select, or_, func, desc, case
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Tuple

from app.cruds import BaseCRUD
from app.models import Project as ProjectORM
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
                    cls.model.name.ilike(f"%{search}%"),
                    cls.model.description.ilike(f"%{search}%"),
                )
            )

        count_query = select(func.count()).select_from(base_query.subquery())
        total_count = await session.scalar(count_query)

        priority = case((cls.model.name.ilike(f"%{search}%"), 1), else_=0)

        paginated_query = (
            base_query.order_by(
                desc(priority), cls.model.id.desc()
            )  # Сначала по приоритету, потом по ID (стабильность)
            .offset(offset)
            .limit(limit)
        )

        result = await session.execute(paginated_query)
        items = result.scalars().all()

        return items, total_count
