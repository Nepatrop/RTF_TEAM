from sqlalchemy import select, or_, func, desc, case
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Tuple

from app.cruds import BaseCRUD
from app.models import Project as ProjectORM
from app.models import Interview as InterviewORM

class InterviewCRUD(BaseCRUD):
    model = InterviewORM

    @classmethod
    async def get_list_by_project(
        cls,
        session: AsyncSession,
        project: ProjectORM,
        search: str,
        offset: int = 0,
        limit: int = 10,
    ) -> Tuple[List[ProjectORM], int]:
        base_query = select(cls.model).where(cls.model.project_id == project.id)

        count_query = select(func.count()).select_from(base_query.subquery())
        total_count = await session.scalar(count_query)

        priority = case((cls.model.name.ilike(f"%{search}%"), 1), else_=0)

        paginated_query = (
            base_query.order_by(
                desc(priority), cls.model.id.desc()
            )
            .offset(offset)
            .limit(limit)
        )

        result = await session.execute(paginated_query)
        items = result.scalars().all()

        return items, total_count

    @classmethod
    async def count_by_project(
            cls,
            session: AsyncSession,
            project: ProjectORM,
    )-> int:
        query = select(func.count(cls.model.id)).where(cls.model.project_id == project.id)
        result = await session.execute(query)
        return result.scalar()
