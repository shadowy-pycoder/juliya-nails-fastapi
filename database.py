from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
import sqlalchemy.orm as so

from config import config


class Base(so.DeclarativeBase):
    pass


engine = create_async_engine(config.DATABASE_URL, echo=True)
async_session_maker = async_sessionmaker(engine, expire_on_commit=False, autoflush=False)


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_maker() as session:
        yield session
