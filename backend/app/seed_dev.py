"""Siembra datos de desarrollo (usuarios, áreas-membresías, proyectos). Solo local.

Uso: docker compose exec backend python -m app.seed_dev
Idempotente: omite lo que ya existe.
"""
import asyncio
from datetime import date

from sqlalchemy import select

from app.core.db import SessionLocal
from app.models.area import Area
from app.models.project import Project
from app.models.project_member import ProjectMember
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

DEV_PROJECTS: list[dict] = [
    {
        "name": "Renovación planta norte",
        "area": "produccion",
        "owner": "ana@invesa.com",
        "status": "active",
        "due": date(2026, 9, 30),
        "description": "Modernización de líneas de producción de la planta norte.",
        "members": [("carlos@invesa.com", "viewer")],
    },
    {
        "name": "Auditoría ambiental 2026",
        "area": "ambiental",
        "owner": "carlos@invesa.com",
        "status": "active",
        "due": date(2026, 7, 15),
        "description": "Auditoría de cumplimiento ambiental anual.",
    },
    {
        "name": "Campaña comercial Q3",
        "area": "comercial",
        "owner": "carlos@invesa.com",
        "status": "planned",
        "due": date(2026, 8, 1),
        "description": "Lanzamiento de campaña para el tercer trimestre.",
    },
    {
        "name": "Migración ERP",
        "area": "it",
        "owner": "wserna@invesa.com",
        "status": "on_hold",
        "due": date(2026, 12, 1),
        "description": "Migración del ERP corporativo a la nueva versión.",
    },
]


async def main() -> None:
    async with SessionLocal() as db:
        areas = {a.slug: a for a in (await db.execute(select(Area))).scalars().all()}

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
        await db.flush()

        users = {u.email: u for u in (await db.execute(select(User))).scalars().all()}

        created_projects = 0
        for spec in DEV_PROJECTS:
            area = areas.get(spec["area"])
            if area is None:
                continue
            existing = (
                await db.execute(
                    select(Project).where(
                        Project.name == spec["name"], Project.area_id == area.id
                    )
                )
            ).scalar_one_or_none()
            if existing is not None:
                continue
            owner = users.get(spec["owner"])
            project = Project(
                name=spec["name"],
                description=spec.get("description"),
                area_id=area.id,
                status=spec.get("status", "planned"),
                owner_id=owner.id if owner else None,
                due_date=spec.get("due"),
            )
            db.add(project)
            await db.flush()
            if owner is not None:
                db.add(ProjectMember(project_id=project.id, user_id=owner.id, role="owner"))
            for email, role in spec.get("members", []):
                member = users.get(email)
                if member is not None and (owner is None or member.id != owner.id):
                    db.add(ProjectMember(project_id=project.id, user_id=member.id, role=role))
            created_projects += 1

        await db.commit()
        print(f"Seed completado. Proyectos creados: {created_projects}")


if __name__ == "__main__":
    asyncio.run(main())
