from collections.abc import AsyncGenerator

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

import app.models  # noqa: F401  (registra todos los modelos en Base.metadata)
from app.core import db as db_module
from app.core.config import settings
from app.core.db import Base, register_pgvector
from app.main import app

# Las pruebas usan siempre proveedores simulados (deterministas, sin red),
# aunque el entorno real tenga GEMINI_PROVIDER=real.
settings.gemini_provider = "mock"
# El alta automática de repositorio se prueba aparte; no en cada proyecto de test.
settings.github_autocreate_repo = False

TEST_DB_URL = "postgresql+asyncpg://agora:agora@db:5432/agora_test"
ADMIN_DB_URL = "postgresql+asyncpg://agora:agora@db:5432/postgres"


@pytest_asyncio.fixture
async def engine() -> AsyncGenerator[AsyncEngine, None]:
    # Crea la base de datos de test si no existe (idempotente).
    admin = create_async_engine(ADMIN_DB_URL, isolation_level="AUTOCOMMIT")
    async with admin.connect() as conn:
        exists = await conn.scalar(
            text("SELECT 1 FROM pg_database WHERE datname = 'agora_test'")
        )
        if not exists:
            await conn.execute(text("CREATE DATABASE agora_test"))
    await admin.dispose()

    eng = create_async_engine(TEST_DB_URL)
    async with eng.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    await eng.dispose()  # cierra conexiones creadas antes de registrar el códec
    register_pgvector(eng)
    yield eng
    await eng.dispose()


@pytest_asyncio.fixture
async def session(engine: AsyncEngine) -> AsyncGenerator[AsyncSession, None]:
    maker = async_sessionmaker(engine, expire_on_commit=False)
    async with maker() as s:
        yield s


@pytest_asyncio.fixture
async def client(session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield session

    app.dependency_overrides[db_module.get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()
