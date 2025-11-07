from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from app.cruds import BaseCRUD
from app.models import RefreshToken as RefreshTokenORM


class RefreshTokenCRUD(BaseCRUD):
    model = RefreshTokenORM

    @classmethod
    async def get_by_token(cls, session: AsyncSession, token: str) -> RefreshTokenORM:
        query = select(cls.model).where(cls.model.token == token)
        result = await session.execute(query)
        obj = result.scalar_one_or_none()
        return obj

    @classmethod
    async def remove_by_user(cls, session: AsyncSession, user_id: int) -> None:
        query = delete(cls.model).where(cls.model.user_id == user_id)
        await session.execute(query)
        await session.commit()
