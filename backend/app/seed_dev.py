"""Siembra usuarios de desarrollo con sus áreas. Solo para entorno local.

Uso: docker compose exec backend python -m app.seed_dev
"""
import asyncio

from sqlalchemy import select

from app.core.db import SessionLocal
from app.models.area import Area
from app.models.user import User
from app.models.user_area import UserArea

DEV_USERS: list[dict] = [
    {"email": "wserna@invesa.com", "name": "Wilder Serna", "role": "admin", "areas": []},
    {
        "email": "ana@invesa.com",
        "name": "Ana Gómez",
        "role": "member",
        "areas": [("produccion", "lead")],
    },
    {
        "email": "carlos@invesa.com",
        "name": "Carlos Ruiz",
        "role": "member",
        "areas": [("ambiental", "member"), ("comercial", "member")],
    },
]


async def main() -> None:
    async with SessionLocal() as db:
        areas = {a.slug: a for a in (await db.execute(select(Area))).scalars().all()}
        created = 0
        for spec in DEV_USERS:
            existing = (
                await db.execute(select(User).where(User.email == spec["email"]))
            ).scalar_one_or_none()
            if existing is not None:
                continue
            user = User(email=spec["email"], name=spec["name"], role=spec["role"])
            db.add(user)
            await db.flush()
            for slug, role in spec["areas"]:
                area = areas.get(slug)
                if area is not None:
                    db.add(UserArea(user_id=user.id, area_id=area.id, area_role=role))
            created += 1
        await db.commit()
        print(f"Seed completado. Usuarios creados: {created}")


if __name__ == "__main__":
    asyncio.run(main())
