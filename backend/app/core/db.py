from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings

engine = create_async_engine(settings.database_url, future=True, echo=False)

SessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    """Base declarativa para todos los modelos."""


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependencia de FastAPI: provee una sesión async por request."""
    async with SessionLocal() as session:
        yield session
