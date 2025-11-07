from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from app.core.config import settings

engine = create_async_engine(settings.DATABASE_URL)
session = async_sessionmaker(autocommit=False, autoflush=False, bind=engine)


async def get_db():
    async with session() as new_session:
        yield new_session
