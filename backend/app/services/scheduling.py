"""Propone el primer hueco común de los miembros de un proyecto (Calendar free/busy).

Horario laboral local (UTC offset de la empresa), de lunes a viernes, excluyendo
el almuerzo (12:00–14:00). Devuelve un instante listo para create_meeting.
"""
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.project import Project
from app.models.project_member import ProjectMember
from app.models.user import User
from app.services import google as google_service

# Ventanas laborales locales (hora inicio/fin): jornada 8–17, excluyendo almuerzo 12–14.
# (una reunión de 1 h puede empezar como muy tarde a las 16:00.)
_WORK_WINDOWS = [(8, 0, 12, 0), (14, 0, 17, 0)]
_STEP = timedelta(minutes=30)


def _local_tz() -> timezone:
    return timezone(timedelta(hours=settings.app_utc_offset_hours))


def _parse(dt: str) -> datetime:
    return datetime.fromisoformat(dt.replace("Z", "+00:00"))


async def member_emails(db: AsyncSession, project: Project) -> list[str]:
    rows = (
        await db.execute(
            select(User.email)
            .join(ProjectMember, ProjectMember.user_id == User.id)
            .where(ProjectMember.project_id == project.id)
        )
    ).scalars().all()
    return sorted({e for e in rows if e})


async def suggest_slot(
    db: AsyncSession,
    user: User,
    project: Project,
    duration_minutes: int = 60,
    days_ahead: int = 7,
) -> dict[str, Any]:
    tz = _local_tz()
    emails = await member_emails(db, project)
    if not emails:
        return {"found": False, "reason": "el proyecto no tiene miembros con correo."}

    now = datetime.now(timezone.utc)
    days_ahead = max(1, min(int(days_ahead or 7), 30))
    try:
        busy_map = await google_service.free_busy(
            db, user, emails, now.isoformat(), (now + timedelta(days=days_ahead)).isoformat()
        )
    except google_service.GoogleNotConnected:
        return {"found": False, "reason": "Google no está conectado para leer calendarios."}
    except Exception:
        return {"found": False, "reason": "no pude leer la disponibilidad (reconecta Google para el permiso de calendarios)."}

    busy: list[tuple[datetime, datetime]] = []
    for slots in busy_map.values():
        for b in slots:
            try:
                busy.append((_parse(b["start"]), _parse(b["end"])))
            except Exception:
                pass

    dur = timedelta(minutes=max(15, min(int(duration_minutes or 60), 480)))
    earliest = now.astimezone(tz) + timedelta(minutes=5)

    for offset in range(0, days_ahead + 1):
        day = (now.astimezone(tz) + timedelta(days=offset)).date()
        if day.weekday() >= 5:  # sábado/domingo
            continue
        for sh, sm, eh, em in _WORK_WINDOWS:
            win_start = datetime(day.year, day.month, day.day, sh, sm, tzinfo=tz)
            win_end = datetime(day.year, day.month, day.day, eh, em, tzinfo=tz)
            t = max(win_start, earliest)
            # alinear a la cuadrícula de 30 min
            if t.minute not in (0, 30) or t.second:
                t = t.replace(second=0, microsecond=0, minute=(0 if t.minute < 30 else 30))
                if t < max(win_start, earliest):
                    t += _STEP
            while t + dur <= win_end:
                t_utc, end_utc = t.astimezone(timezone.utc), (t + dur).astimezone(timezone.utc)
                if not any(bs < end_utc and t_utc < be for bs, be in busy):
                    return {
                        "found": True,
                        "start": t.isoformat(),
                        "end": (t + dur).isoformat(),
                        "duration_minutes": int(dur.total_seconds() // 60),
                        "attendees": emails,
                        "local_label": t.strftime("%d/%m %H:%M"),
                    }
                t += _STEP
    return {
        "found": False,
        "attendees": emails,
        "reason": "no encontré un hueco común en horario laboral (8–17, evitando 12–14) en ese plazo.",
    }
