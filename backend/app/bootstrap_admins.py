"""Asegura los administradores iniciales definidos en BOOTSTRAP_ADMIN_EMAILS.

Idempotente y seguro en producción: para cada correo de la lista, si el usuario
existe lo marca admin/activo; si no existe, lo crea como admin (podrá entrar con
Google, que enriquece su nombre/avatar). No-op si la variable está vacía. Se ejecuta
en el arranque (docker-entrypoint.sh), tras las migraciones.
"""
import asyncio

from sqlalchemy import select

from app.core.config import settings
from app.core.db import SessionLocal
from app.models.user import User


async def ensure_admins() -> None:
    emails = [e.strip().lower() for e in (settings.bootstrap_admin_emails or "").split(",") if e.strip()]
    if not emails:
        return
    async with SessionLocal() as db:
        for email in emails:
            user = (await db.execute(select(User).where(User.email == email))).scalar_one_or_none()
            if user is None:
                db.add(User(email=email, name=email.split("@")[0], role="admin", is_active=True))
                print(f"[bootstrap] admin creado: {email}")
            elif user.role != "admin" or not user.is_active:
                user.role = "admin"
                user.is_active = True
                print(f"[bootstrap] admin asegurado: {email}")
        await db.commit()


if __name__ == "__main__":
    asyncio.run(ensure_admins())
