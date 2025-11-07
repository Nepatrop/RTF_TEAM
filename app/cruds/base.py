from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Type, TypeVar, Generic
from pydantic import BaseModel

from app.exceptions.custom import NotFoundException

T = TypeVar("T")


class BaseCRUD(Generic[T]):
    model: Type[T]

    @classmethod
    async def create(cls, session: AsyncSession, obj: BaseModel) -> T:
        obj_data = obj.model_dump()
        db_obj = cls.model(**obj_data)
        session.add(db_obj)
        await session.commit()
        await session.refresh(db_obj)
        return db_obj

    @classmethod
    async def get_by_id(cls, session: AsyncSession, _id: int) -> T:
        query = select(cls.model).where(cls.model.id == _id)
        result = await session.execute(query)
        obj = result.scalar_one_or_none()
        if obj is None:
            raise NotFoundException(cls.model.__tablename__, "id", _id)
        return obj

    @classmethod
    async def update(cls, session: AsyncSession, _id: int, upd_obj: dict) -> T:
        obj = await cls.get_by_id(session, _id)
        for key, value in upd_obj.items():
            setattr(obj, key, value)
        session.add(obj)
        await session.commit()
        await session.refresh(obj)
        return obj

    @classmethod
    async def remove(cls, session: AsyncSession, _id: int) -> None:
        obj = await cls.get_by_id(session, _id)
        await session.delete(obj)
        await session.commit()
