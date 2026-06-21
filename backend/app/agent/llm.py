"""Stub determinista de LLM con 'function calling' por heurística.

Decide qué tool usar y redacta la respuesta. En producción se reemplaza por
Gemini (mismo contrato: enrutar a una tool y redactar con los datos obtenidos).
"""
import re
from dataclasses import dataclass, field
from datetime import datetime, time, timedelta, timezone
from typing import Any

EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")


@dataclass
class Decision:
    intent: str
    args: dict[str, Any] = field(default_factory=dict)


class DevAgentLLM:
    def route(self, message: str) -> Decision:
        m = message.lower()
        wants_meeting = any(k in m for k in ["reunión", "reunion", "meeting", "meet"])
        wants_create = any(k in m for k in ["crea", "cre", "agenda", "agénda", "program", "organiza"])
        if wants_meeting and wants_create:
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
        m = message.lower()
        now = datetime.now(timezone.utc)
        base = now + timedelta(days=1)
        if "hoy" in m:
            base = now
        # 10:00 (aprox. America/Bogota, UTC-5) = 15:00 UTC
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

    def compose_meeting_result(self, result: dict[str, Any]) -> str:
        return f"✅ Reunión creada: «{result['title']}». Enlace de Meet: {result['meet_url']}"

    def compose_email_result(self, result: dict[str, Any]) -> str:
        to = ", ".join(result.get("to", [])) or "(sin destinatario)"
        return f"✅ Correo enviado (simulado) a {to} — asunto: «{result['subject']}»."

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
