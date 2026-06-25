"""Stub determinista de LLM con 'function calling' por heurística.

Decide qué tool usar y redacta la respuesta. En producción se reemplaza por
Gemini (mismo contrato: enrutar a una tool y redactar con los datos obtenidos).
"""
import re
from dataclasses import dataclass, field
from datetime import datetime, time, timedelta, timezone
from typing import Any

EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")

_CREATE_VERBS = ["crea", "crear", "añade", "anade", "agrega", "registra", "agenda", "programa", "organiza"]


def _duration_label(minutes: int) -> str:
    minutes = int(minutes or 60)
    if minutes < 60:
        return f"{minutes} min"
    horas, resto = divmod(minutes, 60)
    return f"{horas} h" + (f" {resto} min" if resto else "")


def _fmt_when(when_iso: str | None, duration_minutes: int = 60) -> str:
    """«29/06 11:00–12:00 (1 h)» a partir de un ISO de inicio y la duración."""
    try:
        start = datetime.fromisoformat((when_iso or "").replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return when_iso or "(por definir)"
    end = start + timedelta(minutes=int(duration_minutes or 60))
    return f"{start.strftime('%d/%m %H:%M')}–{end.strftime('%H:%M')} ({_duration_label(duration_minutes)})"


@dataclass
class Decision:
    intent: str
    args: dict[str, Any] = field(default_factory=dict)


class DevAgentLLM:
    def route(self, message: str) -> Decision:
        m = message.lower()
        wants_create = any(k in m for k in _CREATE_VERBS)

        if "tarea" in m and any(k in m for k in ["asigna", "asignar", "asígna", "asignale", "asignále"]):
            return Decision("assign_task", self._assign_args(message))
        if "tarea" in m and any(
            k in m
            for k in ["marca", "marcar", "avanza", "avanzar", "completa", "completar", "termina", "finaliza", "mueve", "cambia", "pon"]
        ):
            return Decision("update_task", self._update_task_args(message))
        if wants_create and "tarea" in m:
            return Decision("create_task", self._task_args(message))
        if wants_create and "proyecto" in m:
            return Decision("create_project", self._project_args(message))
        if wants_create and any(k in m for k in ["reunión", "reunion", "meeting", "meet"]):
            return Decision("create_meeting", self._meeting_args(message))
        if any(k in m for k in ["correo", "email", "mail", "notifica", "envía", "envia"]):
            return Decision("send_email", self._email_args(message))
        if any(k in m for k in ["vencid", "atrasad", "overdue", "retras"]):
            return Decision("overdue_tasks")
        if any(k in m for k in ["actividad", "github", "commit", "pull request", "release"]):
            return Decision("recent_activity")
        if any(
            k in m
            for k in [
                "documento",
                "acta",
                "según",
                "segun",
                "qué dice",
                "que dice",
                "procedimiento",
                "política",
                "politica",
                "manual",
                "norma",
                "busca",
            ]
        ):
            return Decision("knowledge", {"message": message})
        if any(k in m for k in ["resumen", "resume", "estado de", "cómo va", "como va", "situaci"]):
            return Decision("project_summary", {"message": message})
        return Decision("projects_status")

    # --- extracción de argumentos de acciones ---
    def _attendees(self, message: str) -> list[str]:
        emails = EMAIL_RE.findall(message)
        if emails:
            return emails
        m = re.search(r"\bcon\b(.+?)(?:\bel\b|\bmañana\b|\bhoy\b|\bpara\b|$)", message, re.IGNORECASE)
        if not m:
            return []
        parts = re.split(r",|\sy\s", m.group(1))
        return [p.strip() for p in parts if p.strip()]

    def _when(self, message: str) -> datetime:
        now = datetime.now(timezone.utc)
        base = now if "hoy" in message.lower() else now + timedelta(days=1)
        return datetime.combine(base.date(), time(15, 0), tzinfo=timezone.utc)

    def _meeting_args(self, message: str) -> dict[str, Any]:
        title = "Reunión de proyecto"
        m = re.search(r"\b(sobre|para tratar|acerca de|titulada?)\b\s+(.+)", message, re.IGNORECASE)
        if m:
            title = m.group(2).strip().rstrip(".")
        return {
            "title": title[:120],
            "attendees": self._attendees(message),
            "when": self._when(message).isoformat(),
        }

    def _email_args(self, message: str) -> dict[str, Any]:
        to = EMAIL_RE.findall(message)
        if not to:
            m = re.search(r"\b(a|para)\b\s+([^,\.]+)", message, re.IGNORECASE)
            to = [m.group(2).strip()] if m else []
        subject = "Notificación de Ágora"
        m = re.search(r"\b(asunto|sobre)\b\s+(.+)", message, re.IGNORECASE)
        if m:
            subject = m.group(2).strip().rstrip(".")[:120]
        return {"to": to, "subject": subject, "body": message}

    def _project_args(self, message: str) -> dict[str, Any]:
        name = "Nuevo proyecto"
        area = ""
        m = re.search(r"proyecto\s+(?:llamado\s+)?(.+?)\s+(?:en|para)\s+(?:el área\s+|el area\s+)?(.+)", message, re.IGNORECASE)
        if m:
            name = m.group(1).strip()
            area = m.group(2).strip()
        else:
            m2 = re.search(r"proyecto\s+(?:llamado\s+)?(.+)", message, re.IGNORECASE)
            if m2:
                name = m2.group(1).strip()
        return {"name": name.rstrip(".")[:200], "area_name": area.rstrip(".")}

    def _task_args(self, message: str) -> dict[str, Any]:
        title = "Nueva tarea"
        project = ""
        m = re.search(
            r"tarea\s+(?:llamada\s+)?(.+?)\s+(?:en|al|para)\s+(?:el\s+)?(?:proyecto\s+)?(.+)",
            message,
            re.IGNORECASE,
        )
        if m:
            title = m.group(1).strip()
            project = m.group(2).strip()
        else:
            m2 = re.search(r"tarea\s+(?:llamada\s+)?(.+)", message, re.IGNORECASE)
            if m2:
                title = m2.group(1).strip()
        return {"title": title.rstrip(".")[:300], "project_name": project.rstrip(".")}

    def _update_task_args(self, message: str) -> dict[str, Any]:
        m = message.lower()
        status = "done"
        if any(k in m for k in ["en progreso", "progreso", "empez", "inicia"]):
            status = "in_progress"
        elif any(k in m for k in ["bloquea", "bloqueada", "bloqueado"]):
            status = "blocked"
        elif any(k in m for k in ["por hacer", "pendiente", "todo"]):
            status = "todo"
        match = re.search(r"tarea\s+(.+?)(?:\s+como\b|\s+a\b|\s+en\b|$)", message, re.IGNORECASE)
        title = match.group(1).strip().rstrip(".") if match else ""
        return {"title": title[:300], "status": status}

    def _assign_args(self, message: str) -> dict[str, Any]:
        match = re.search(r"tarea\s+(.+?)\s+a\s+(.+)", message, re.IGNORECASE)
        if match:
            return {
                "title": match.group(1).strip().rstrip(".")[:300],
                "assignee": match.group(2).strip().rstrip("."),
            }
        return {"title": "", "assignee": ""}

    # --- redacción ---
    def compose_projects_status(self, data: list[dict[str, Any]]) -> str:
        if not data:
            return "No tienes proyectos accesibles en tus áreas todavía."
        lines = ["Estado de tus proyectos:"]
        for p in data:
            extra = f" · {p['overdue']} vencida(s)" if p["overdue"] else ""
            lines.append(
                f"• {p['name']} ({p['area']}) — {p['status']}, "
                f"{p['open_tasks']} tarea(s) abierta(s){extra}"
            )
        return "\n".join(lines)

    def compose_overdue_tasks(self, data: list[dict[str, Any]]) -> str:
        if not data:
            return "No hay tareas vencidas en tus proyectos. 🎉"
        lines = [f"Tienes {len(data)} tarea(s) vencida(s):"]
        for t in data:
            lines.append(f"• {t['title']} — {t['project']} (vencía {t['due_date']})")
        return "\n".join(lines)

    def compose_recent_activity(self, data: list[dict[str, Any]]) -> str:
        if not data:
            return "No hay actividad reciente de GitHub en tus proyectos."
        lines = ["Actividad reciente:"]
        for e in data:
            lines.append(f"• [{e['type']}] {e['title']} — {e['repo']} ({e['when']})")
        return "\n".join(lines)

    def compose_project_summary(self, data: dict[str, Any] | None) -> str:
        if data is None:
            return (
                "No encontré un proyecto con ese nombre en tus áreas. "
                "Indícame el nombre exacto o pregunta por el estado general."
            )
        lines = [
            f"Resumen de «{data['name']}» ({data['area']}):",
            f"• Estado: {data['status']}",
            f"• Tareas: {data['open_tasks']} abiertas, {data['overdue']} vencidas, "
            f"{data['done']} hechas",
            f"• Miembros: {data['members']}",
        ]
        if data.get("recent"):
            lines.append(f"• Última actividad: {data['recent']}")
        return "\n".join(lines)

    def compose_knowledge(self, data: list[dict[str, Any]]) -> str:
        if not data:
            return "No encontré información relevante en los documentos de tus proyectos."
        lines = ["Según los documentos:"]
        for item in data[:3]:
            snippet = " ".join(item["content"].split())
            if len(snippet) > 240:
                snippet = snippet[:240] + "…"
            lines.append(f"• {snippet}")
        sources = sorted({item["document_title"] for item in data})
        lines.append("Fuentes: " + ", ".join(sources))
        return "\n".join(lines)

    def compose_meeting_proposal(self, args: dict[str, Any]) -> str:
        attendees = ", ".join(args["attendees"]) if args["attendees"] else "(sin asistentes)"
        when = _fmt_when(args.get("when"), args.get("duration_minutes") or 60)
        return (
            "Voy a crear esta reunión (requiere tu confirmación):\n"
            f"• Título: {args['title']}\n• Asistentes: {attendees}\n• Cuándo: {when}\n"
            "Pulsa «Confirmar» para crearla con enlace de Meet."
        )

    def compose_email_proposal(self, args: dict[str, Any]) -> str:
        to = ", ".join(args["to"]) if args["to"] else "(sin destinatario)"
        return (
            "Voy a enviar este correo (requiere tu confirmación):\n"
            f"• Para: {to}\n• Asunto: {args['subject']}\n"
            "Pulsa «Confirmar» para enviarlo."
        )

    def compose_project_proposal(self, args: dict[str, Any]) -> str:
        area = args["area_name"] or "(área no indicada)"
        return (
            "Voy a crear este proyecto (requiere tu confirmación):\n"
            f"• Nombre: {args['name']}\n• Área: {area}\n"
            "Pulsa «Confirmar» para crearlo."
        )

    def compose_task_proposal(self, args: dict[str, Any]) -> str:
        project = args.get("project_name") or "(proyecto no indicado)"
        lines = [
            "Voy a crear esta tarea (requiere tu confirmación):",
            f"• Título: {args.get('title', '')}",
            f"• Proyecto: {project}",
        ]
        if args.get("assignee"):
            lines.append(f"• Responsable: {args['assignee']}")
        lines.append("Pulsa «Confirmar» para crearla.")
        return "\n".join(lines)

    def _task_line(self, t: Any) -> str:
        if not isinstance(t, dict):
            return str(t)
        bits = []
        if t.get("priority"):
            bits.append(t["priority"])
        if t.get("assignee"):
            bits.append(f"→ {t['assignee']}")
        if t.get("due_date"):
            bits.append(t["due_date"])
        return t.get("title", "") + (f" ({', '.join(bits)})" if bits else "")

    def _task_list_block(self, tasks: list[Any], limit: int = 25) -> str:
        body = "\n".join(f"{i}. {self._task_line(t)}" for i, t in enumerate(tasks[:limit], 1))
        if len(tasks) > limit:
            body += f"\n…y {len(tasks) - limit} más."
        return body

    def compose_create_project_with_tasks_proposal(self, args: dict[str, Any]) -> str:
        area = args.get("area_name") or "(área no indicada)"
        tasks = args.get("tasks") or []
        return (
            "Voy a crear este proyecto y su listado de tareas (requiere tu confirmación):\n\n"
            f"**Proyecto:** {args.get('name', '')} · **Área:** {area}\n\n"
            f"**Tareas ({len(tasks)}):**\n"
            f"{self._task_list_block(tasks)}\n\n"
            "Pulsa «Confirmar» para crear el proyecto con todas sus tareas."
        )

    def _unmatched_note(self, result: dict[str, Any]) -> str:
        unmatched = result.get("unmatched") or []
        if not unmatched:
            return ""
        return (
            f" No encontré como usuarios de Ágora a {', '.join(unmatched)}, "
            "así que esas tareas quedaron sin responsable; puedes asignarlas a mano o "
            "decirme el usuario correcto."
        )

    def compose_create_project_with_tasks_result(self, result: dict[str, Any]) -> str:
        if not result.get("ok"):
            return f"No pude crear el proyecto: {result.get('error', 'error desconocido')}"
        n = len(result.get("tasks", []))
        return (
            f"✅ Proyecto «{result['name']}» creado en {result['area']} con {n} tarea(s)."
            + self._unmatched_note(result)
        )

    def compose_create_tasks_proposal(self, args: dict[str, Any]) -> str:
        project = args.get("project_name") or "(proyecto no indicado)"
        tasks = args.get("tasks") or []
        return (
            "Voy a crear estas tareas (requiere tu confirmación):\n\n"
            f"**Proyecto:** {project}\n\n"
            f"**Tareas ({len(tasks)}):**\n"
            f"{self._task_list_block(tasks)}\n\n"
            "Pulsa «Confirmar» para crearlas."
        )

    def compose_create_tasks_result(self, result: dict[str, Any]) -> str:
        if not result.get("ok"):
            return f"No pude crear las tareas: {result.get('error', 'error desconocido')}"
        n = len(result.get("tasks", []))
        return f"✅ {n} tarea(s) creada(s) en «{result['project']}»." + self._unmatched_note(result)

    def compose_create_sprint_proposal(self, args: dict[str, Any]) -> str:
        lines = [
            "Voy a crear este sprint (requiere tu confirmación):",
            f"• Sprint: {args.get('name') or 'Sprint'}",
            f"• Proyecto: {args.get('project_name') or '(no indicado)'}",
        ]
        if args.get("goal"):
            lines.append(f"• Objetivo: {args['goal']}")
        if args.get("start_date") or args.get("end_date"):
            lines.append(f"• Fechas: {args.get('start_date') or '?'} → {args.get('end_date') or '?'}")
        lines.append("Pulsa «Confirmar» para crearlo.")
        return "\n".join(lines)

    def compose_create_sprint_result(self, result: dict[str, Any]) -> str:
        if not result.get("ok"):
            return f"No pude crear el sprint: {result.get('error', 'error desconocido')}"
        return (
            f"✅ Sprint «{result['name']}» creado en «{result['project']}» "
            f"({result['start']} → {result['end']})."
        )

    def compose_update_sprint_proposal(self, args: dict[str, Any]) -> str:
        etiquetas = {"new_name": "nombre", "goal": "objetivo", "start_date": "inicio", "end_date": "fin", "status": "estado"}
        cambios = [f"{etiquetas[k]} → {args[k]}" for k in etiquetas if str(args.get(k) or "").strip()]
        return (
            "Voy a actualizar este sprint (requiere tu confirmación):\n"
            f"• Proyecto: {args.get('project_name') or '(no identificado)'}  ·  Sprint: {args.get('sprint_name') or '(no indicado)'}\n"
            f"• Cambios: {'; '.join(cambios) if cambios else '(sin cambios indicados)'}\n"
            "Pulsa «Confirmar»."
        )

    def compose_update_sprint_result(self, result: dict[str, Any]) -> str:
        if not result.get("ok"):
            return f"No pude actualizar el sprint: {result.get('error', 'error desconocido')}"
        return f"✅ Sprint «{result['name']}» actualizado en «{result['project']}»."

    def compose_delete_sprint_proposal(self, args: dict[str, Any]) -> str:
        return (
            "⚠️ Voy a ELIMINAR este sprint (requiere tu confirmación):\n"
            f"• Proyecto: {args.get('project_name') or '(no identificado)'}  ·  Sprint: {args.get('sprint_name') or '(no indicado)'}\n"
            "Esta acción no se puede deshacer. Pulsa «Confirmar»."
        )

    def compose_delete_sprint_result(self, result: dict[str, Any]) -> str:
        if not result.get("ok"):
            return f"No pude eliminar el sprint: {result.get('error', 'error desconocido')}"
        return f"🗑️ Sprint «{result['name']}» eliminado de «{result['project']}»."

    def compose_save_diagram_proposal(self, args: dict[str, Any]) -> str:
        return (
            "Voy a guardar este diagrama en la documentación del proyecto (requiere tu confirmación):\n"
            f"• Título: {args.get('title') or 'Diagrama'}\n"
            f"• Proyecto: {args.get('project_name') or '(no indicado)'}\n"
            "Pulsa «Confirmar» para guardarlo."
        )

    def compose_save_diagram_result(self, result: dict[str, Any]) -> str:
        if not result.get("ok"):
            return f"No pude guardar el diagrama: {result.get('error', 'error desconocido')}"
        return f"✅ Diagrama «{result['title']}» guardado en la documentación de «{result['project']}»."

    def compose_meeting_result(self, result: dict[str, Any]) -> str:
        when = _fmt_when(result.get("starts_at"), result.get("duration_minutes") or 60)
        meet = result.get("meet_url")
        meet_line = f" Enlace de Meet: {meet}" if meet else ""
        return f"✅ Reunión creada: «{result['title']}» — {when}.{meet_line}"

    def compose_email_result(self, result: dict[str, Any]) -> str:
        to = ", ".join(result.get("to", [])) or "(sin destinatario)"
        return f"✅ Correo enviado (simulado) a {to} — asunto: «{result['subject']}»."

    def compose_project_result(self, result: dict[str, Any]) -> str:
        if not result.get("ok"):
            return f"No pude crear el proyecto: {result.get('error', 'error desconocido')}"
        return f"✅ Proyecto «{result['name']}» creado en {result['area']}."

    def compose_task_result(self, result: dict[str, Any]) -> str:
        if not result.get("ok"):
            return f"No pude crear la tarea: {result.get('error', 'error desconocido')}"
        who = f" y asignada a {result['assignee']}" if result.get("assignee") else ""
        return f"✅ Tarea «{result['title']}» creada en {result['project']}{who}."

    def compose_archive_project_proposal(self, args: dict[str, Any]) -> str:
        return (
            "Voy a archivar este proyecto (requiere tu confirmación):\n"
            f"• Proyecto: {args.get('project_name') or '(no identificado)'}\n"
            "Pasará a estado «Archivado»; es reversible (puedes reactivarlo después).\n"
            "Pulsa «Confirmar» para archivarlo."
        )

    def compose_archive_project_result(self, result: dict[str, Any]) -> str:
        if not result.get("ok"):
            return f"No pude archivar el proyecto: {result.get('error', 'error desconocido')}"
        if result.get("already"):
            return f"El proyecto «{result['name']}» ya estaba archivado."
        return f"✅ Proyecto «{result['name']}» archivado."

    def compose_delete_project_proposal(self, args: dict[str, Any]) -> str:
        return (
            "⚠️ Voy a ELIMINAR PERMANENTEMENTE este proyecto (requiere tu confirmación):\n"
            f"• Proyecto: {args.get('project_name') or '(no identificado)'}\n"
            "Se borrarán también sus tareas, comentarios y documentos asociados. "
            "Esta acción NO se puede deshacer.\n"
            "Si prefieres conservarlo, considera archivarlo en su lugar.\n"
            "Pulsa «Confirmar» para eliminarlo definitivamente."
        )

    def compose_delete_project_result(self, result: dict[str, Any]) -> str:
        if not result.get("ok"):
            return f"No pude eliminar el proyecto: {result.get('error', 'error desconocido')}"
        return f"🗑️ Proyecto «{result['name']}» eliminado permanentemente."

    def compose_update_project_proposal(self, args: dict[str, Any]) -> str:
        etiquetas = {
            "status": "estado", "new_name": "nombre", "description": "descripción",
            "due_date": "fecha de entrega", "start_date": "fecha de inicio",
            "progress": "avance", "criticality": "criticidad", "category": "categoría",
            "owner": "dueño",
        }
        cambios = [
            f"{etiquetas[k]} → {args[k]}"
            for k in etiquetas
            if str(args.get(k) or "").strip()
        ]
        detalle = "; ".join(cambios) if cambios else "(sin cambios indicados)"
        return (
            "Voy a actualizar este proyecto (requiere tu confirmación):\n"
            f"• Proyecto: {args.get('project_name') or '(no identificado)'}\n• Cambios: {detalle}\n"
            "Pulsa «Confirmar»."
        )

    def compose_update_project_result(self, result: dict[str, Any]) -> str:
        if not result.get("ok"):
            return f"No pude actualizar el proyecto: {result.get('error', 'error desconocido')}"
        return f"✅ Proyecto «{result['name']}» actualizado."

    def compose_add_project_member_proposal(self, args: dict[str, Any]) -> str:
        return (
            "Voy a añadir un miembro al proyecto (requiere tu confirmación):\n"
            f"• Proyecto: {args.get('project_name') or '(no identificado)'}\n"
            f"• Persona: {args.get('person') or '(no indicada)'}  ·  Rol: {args.get('role') or 'editor'}\n"
            "Pulsa «Confirmar»."
        )

    def compose_add_project_member_result(self, result: dict[str, Any]) -> str:
        if not result.get("ok"):
            return f"No pude añadir al miembro: {result.get('error', 'error desconocido')}"
        return f"✅ {result['person']} añadido a «{result['project']}» como {result['role']}."

    def compose_remove_project_member_proposal(self, args: dict[str, Any]) -> str:
        return (
            "Voy a quitar un miembro del proyecto (requiere tu confirmación):\n"
            f"• Proyecto: {args.get('project_name') or '(no identificado)'}\n"
            f"• Persona: {args.get('person') or '(no indicada)'}\n"
            "Pulsa «Confirmar»."
        )

    def compose_remove_project_member_result(self, result: dict[str, Any]) -> str:
        if not result.get("ok"):
            return f"No pude quitar al miembro: {result.get('error', 'error desconocido')}"
        return f"✅ {result['person']} quitado de «{result['project']}»."

    def compose_update_task_proposal(self, args: dict[str, Any]) -> str:
        cambios = []
        if args.get("status"):
            cambios.append(f"estado → {args['status']}")
        if args.get("priority"):
            cambios.append(f"prioridad → {args['priority']}")
        if args.get("due_date"):
            cambios.append(f"fecha → {args['due_date']}")
        if (args.get("new_title") or "").strip():
            cambios.append(f"título → {args['new_title']}")
        if args.get("description"):
            cambios.append("descripción")
        if not cambios:
            cambios.append("estado → done")
        return (
            "Voy a actualizar esta tarea (requiere tu confirmación):\n"
            f"• Tarea: {args.get('title') or '(no identificada)'}\n• Cambios: {', '.join(cambios)}\n"
            "Pulsa «Confirmar»."
        )

    def compose_update_task_result(self, result: dict[str, Any]) -> str:
        if not result.get("ok"):
            return f"No pude actualizar la tarea: {result.get('error', 'error desconocido')}"
        return f"✅ Tarea «{result['title']}» actualizada (estado: {result['status']}) en {result['project']}."

    def compose_delete_task_proposal(self, args: dict[str, Any]) -> str:
        return (
            "⚠️ Voy a ELIMINAR esta tarea (requiere tu confirmación):\n"
            f"• Tarea: {args.get('title') or '(no identificada)'}\n"
            "Esta acción no se puede deshacer. Pulsa «Confirmar»."
        )

    def compose_delete_task_result(self, result: dict[str, Any]) -> str:
        if not result.get("ok"):
            return f"No pude eliminar la tarea: {result.get('error', 'error desconocido')}"
        return f"🗑️ Tarea «{result['title']}» eliminada ({result['project']})."

    def compose_comment_task_proposal(self, args: dict[str, Any]) -> str:
        body = (args.get("body") or "")[:200]
        return (
            "Voy a añadir este comentario (requiere tu confirmación):\n"
            f"• Tarea: {args.get('title') or '(no identificada)'}\n• Comentario: {body}\n"
            "Pulsa «Confirmar»."
        )

    def compose_comment_task_result(self, result: dict[str, Any]) -> str:
        if not result.get("ok"):
            return f"No pude añadir el comentario: {result.get('error', 'error desconocido')}"
        return f"✅ Comentario añadido a «{result['title']}» ({result['project']})."

    def compose_assign_task_proposal(self, args: dict[str, Any]) -> str:
        return (
            "Voy a asignar esta tarea (requiere tu confirmación):\n"
            f"• Tarea: {args['title'] or '(no identificada)'}\n• Responsable: {args['assignee'] or '(no indicado)'}\n"
            "Pulsa «Confirmar»."
        )

    def compose_assign_task_result(self, result: dict[str, Any]) -> str:
        if not result.get("ok"):
            return f"No pude asignar la tarea: {result.get('error', 'error desconocido')}"
        return f"✅ Tarea «{result['title']}» asignada a {result['assignee']} ({result['project']})."
