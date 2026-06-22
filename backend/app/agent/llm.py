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
        when = args["when"].replace("T", " ").replace("+00:00", " UTC")
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

    def compose_create_project_with_tasks_result(self, result: dict[str, Any]) -> str:
        if not result.get("ok"):
            return f"No pude crear el proyecto: {result.get('error', 'error desconocido')}"
        n = len(result.get("tasks", []))
        return f"✅ Proyecto «{result['name']}» creado en {result['area']} con {n} tarea(s)."

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
        return f"✅ {n} tarea(s) creada(s) en «{result['project']}»."

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
        return f"✅ Reunión creada: «{result['title']}». Enlace de Meet: {result['meet_url']}"

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

    def compose_update_task_proposal(self, args: dict[str, Any]) -> str:
        return (
            "Voy a actualizar esta tarea (requiere tu confirmación):\n"
            f"• Tarea: {args['title'] or '(no identificada)'}\n• Nuevo estado: {args['status']}\n"
            "Pulsa «Confirmar»."
        )

    def compose_update_task_result(self, result: dict[str, Any]) -> str:
        if not result.get("ok"):
            return f"No pude actualizar la tarea: {result.get('error', 'error desconocido')}"
        return f"✅ Tarea «{result['title']}» → {result['status']} ({result['project']})."

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
