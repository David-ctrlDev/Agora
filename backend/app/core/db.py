from collections.abc import AsyncGenerator

from pgvector.asyncpg import register_vector
from sqlalchemy import event
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings

engine = create_async_engine(settings.database_url, future=True, echo=False)

SessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    """Base declarativa para todos los modelos."""


def register_pgvector(target_engine: AsyncEngine) -> None:
    """Registra el códec de pgvector en cada conexión asyncpg del engine.

    Requiere que la extensión `vector` ya exista en la base de datos.
    """

    @event.listens_for(target_engine.sync_engine, "connect")
    def _connect(dbapi_connection, _record):  # type: ignore[no-untyped-def]
        dbapi_connection.run_async(register_vector)


register_pgvector(engine)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependencia de FastAPI: provee una sesión async por request."""
    async with SessionLocal() as session:
        yield session
