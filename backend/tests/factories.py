"""Helpers para construir datos en las pruebas."""
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.area import Area
from app.models.user import User
from app.models.user_area import UserArea


async def create_area(session: AsyncSession, name: str, slug: str) -> Area:
    area = Area(name=name, slug=slug)
    session.add(area)
    await session.commit()
    await session.refresh(area)
    return area


async def create_user(session: AsyncSession, email: str, name: str, role: str = "member") -> User:
    user = User(email=email, name=name, role=role)
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


async def add_membership(
    session: AsyncSession, user_id: int, area_id: int, role: str = "member"
) -> None:
    session.add(UserArea(user_id=user_id, area_id=area_id, area_role=role))
    await session.commit()


async def login(client: AsyncClient, user_id: int) -> None:
    response = await client.post("/api/auth/dev-login", json={"user_id": user_id})
    assert response.status_code == 200, response.text
