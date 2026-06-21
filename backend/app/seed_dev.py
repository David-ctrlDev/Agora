"""Siembra datos de desarrollo (usuarios, membresías, proyectos, tareas). Solo local.

Uso: docker compose exec backend python -m app.seed_dev
Idempotente: omite lo que ya existe.
"""
import asyncio
from datetime import date

from sqlalchemy import select

from app.core.db import SessionLocal
from app.models.area import Area
from app.models.document import Document
from app.models.project import Project
from app.models.project_member import ProjectMember
from app.models.task import Task
from app.models.user import User
from app.models.user_area import UserArea
from app.services.knowledge import ingest_document

DEV_AREAS: list[dict] = [
    {"name": "Producción", "slug": "produccion", "description": "Procesos productivos y planta"},
    {"name": "Ambiental", "slug": "ambiental", "description": "Gestión ambiental y cumplimiento"},
    {"name": "Comercial", "slug": "comercial", "description": "Ventas y relación con clientes"},
    {"name": "IT", "slug": "it", "description": "Sistemas y desarrollo"},
]

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

DEV_TASKS: list[dict] = [
    {"project": "Renovación planta norte", "title": "Cotizar maquinaria", "status": "in_progress", "priority": "high", "assignee": "ana@invesa.com", "due": date(2026, 7, 10)},
    {"project": "Renovación planta norte", "title": "Plan de obra", "status": "todo", "priority": "medium", "assignee": "ana@invesa.com"},
    {"project": "Renovación planta norte", "title": "Permisos municipales", "status": "blocked", "priority": "high"},
    {"project": "Auditoría ambiental 2026", "title": "Recopilar evidencias", "status": "in_progress", "priority": "medium", "assignee": "carlos@invesa.com", "due": date(2026, 7, 5)},
    {"project": "Auditoría ambiental 2026", "title": "Solicitar permisos al ente", "status": "todo", "priority": "high", "assignee": "carlos@invesa.com", "due": date(2026, 6, 5)},
    {"project": "Auditoría ambiental 2026", "title": "Informe preliminar", "status": "todo", "priority": "high", "assignee": "carlos@invesa.com"},
    {"project": "Campaña comercial Q3", "title": "Definir presupuesto", "status": "todo", "priority": "medium", "assignee": "carlos@invesa.com"},
    {"project": "Migración ERP", "title": "Mapear procesos", "status": "done", "priority": "medium", "assignee": "wserna@invesa.com"},
    {"project": "Migración ERP", "title": "Plan de migración", "status": "blocked", "priority": "high", "assignee": "wserna@invesa.com"},
]


DEV_DOCS: list[dict] = [
    {
        "project": "Renovación planta norte",
        "title": "Acta de inicio",
        "content": (
            "La renovación de la planta norte busca modernizar tres líneas de producción.\n\n"
            "El presupuesto aprobado es de 1.200 millones. El proveedor principal de maquinaria "
            "es AgroTech. Los permisos municipales son el principal riesgo y pueden bloquear el "
            "cronograma.\n\nLa fecha objetivo de entrega es septiembre de 2026."
        ),
    },
    {
        "project": "Auditoría ambiental 2026",
        "title": "Alcance de la auditoría",
        "content": (
            "La auditoría ambiental 2026 cubre vertimientos, residuos peligrosos y emisiones "
            "atmosféricas.\n\nSe revisarán los permisos ambientales vigentes y las evidencias de "
            "cumplimiento. El informe preliminar debe entregarse antes del 15 de julio."
        ),
    },
    {
        "project": "Migración ERP",
        "title": "Plan de migración ERP",
        "content": (
            "La migración del ERP corporativo se hará en tres fases: análisis, configuración y "
            "salida en vivo.\n\nEl proyecto está en pausa a la espera de aprobación presupuestal. "
            "El mapeo de procesos ya está terminado."
        ),
    },
]


async def main() -> None:
    async with SessionLocal() as db:
        existing_slugs = {a.slug for a in (await db.execute(select(Area))).scalars().all()}
        for spec in DEV_AREAS:
            if spec["slug"] not in existing_slugs:
                db.add(Area(name=spec["name"], slug=spec["slug"], description=spec["description"]))
        await db.flush()
        areas = {a.slug: a for a in (await db.execute(select(Area))).scalars().all()}

        for spec in DEV_USERS:
            if (
                await db.execute(select(User).where(User.email == spec["email"]))
            ).scalar_one_or_none() is not None:
                continue
            user = User(email=spec["email"], name=spec["name"], role=spec["role"])
            db.add(user)
            await db.flush()
            for slug, role in spec["areas"]:
                if (area := areas.get(slug)) is not None:
                    db.add(UserArea(user_id=user.id, area_id=area.id, area_role=role))
        await db.flush()

        users = {u.email: u for u in (await db.execute(select(User))).scalars().all()}

        for spec in DEV_PROJECTS:
            area = areas.get(spec["area"])
            if area is None:
                continue
            if (
                await db.execute(
                    select(Project).where(Project.name == spec["name"], Project.area_id == area.id)
                )
            ).scalar_one_or_none() is not None:
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
        await db.flush()

        projects = {p.name: p for p in (await db.execute(select(Project))).scalars().all()}

        created_tasks = 0
        for spec in DEV_TASKS:
            project = projects.get(spec["project"])
            if project is None:
                continue
            if (
                await db.execute(
                    select(Task).where(Task.project_id == project.id, Task.title == spec["title"])
                )
            ).scalar_one_or_none() is not None:
                continue
            assignee = users.get(spec["assignee"]) if spec.get("assignee") else None
            db.add(
                Task(
                    project_id=project.id,
                    title=spec["title"],
                    status=spec.get("status", "todo"),
                    priority=spec.get("priority", "medium"),
                    assignee_id=assignee.id if assignee else None,
                    due_date=spec.get("due"),
                )
            )
            created_tasks += 1

        await db.commit()

        projects_by_name = {
            p.name: p for p in (await db.execute(select(Project))).scalars().all()
        }
        created_docs = 0
        for spec in DEV_DOCS:
            project = projects_by_name.get(spec["project"])
            if project is None:
                continue
            already = (
                await db.execute(
                    select(Document).where(
                        Document.project_id == project.id, Document.title == spec["title"]
                    )
                )
            ).scalar_one_or_none()
            if already is not None:
                continue
            await ingest_document(db, project.id, spec["title"], spec["content"])
            created_docs += 1

        print(
            f"Seed completado. Tareas creadas: {created_tasks}, documentos: {created_docs}"
        )


if __name__ == "__main__":
    asyncio.run(main())
