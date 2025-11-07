from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import EmailStr
from app.cruds import BaseCRUD
from app.models import User as UserORM


class UserCRUD(BaseCRUD):
    model = UserORM

    @classmethod
    async def get_by_email(cls, session: AsyncSession, email: EmailStr) -> UserORM:
        query = select(cls.model).where(cls.model.email == email)
        result = await session.execute(query)
        obj = result.scalar_one_or_none()
        return obj
