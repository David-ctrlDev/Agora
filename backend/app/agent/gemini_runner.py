"""Agente real sobre Gemini con function-calling.

Las tools de lectura se ejecutan en bucle (acotadas por área); las acciones con
efecto NO se ejecutan: se devuelven como propuesta para que el usuario confirme.
"""
import asyncio
from datetime import datetime, time, timedelta, timezone
from typing import Any

from google.genai import types
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent import tools
from app.agent.gemini_client import get_gemini_client
from app.agent.llm import DevAgentLLM
from app.core.config import settings
from app.models.user import User
from app.schemas.agent import MessageRead

_dev = DevAgentLLM()  # reutilizamos sus plantillas de propuesta (deterministas)

def _system(user: User) -> str:
    return (
        "Eres el asistente de Ágora, la plataforma interna de gestión de proyectos de Invesa. "
        f"El usuario actual es {user.name} ({user.email}), con rol {user.role}. "
        "Responde en español, claro y conciso, usando Markdown cuando ayude (listas, negritas). "
        "Usa las herramientas para consultar datos reales; están acotadas a las áreas del usuario, "
        "así que nunca inventes proyectos, tareas ni cifras. Para «qué proyectos lidera X», el "
        "avance/porcentaje de proyectos o una visión general, usa projects_overview (incluye "
        "responsable, estado, avance % y fecha de entrega). Si preguntan por «mis tareas» o «qué "
        "tengo», usa my_tasks; si preguntan por las tareas de una persona (incluido el propio "
        "usuario por su nombre), usa tasks_by_assignee. Para acciones con efecto (crear proyecto o "
        "tarea, crear reunión, enviar correo, cambiar o asignar tareas) llama a la herramienta "
        "correspondiente: el sistema pedirá confirmación antes de ejecutarla. Responde SIEMPRE de "
        "forma útil; si no hay datos, dilo con naturalidad y sugiere un siguiente paso."
    )

_ACTION_TOOLS = {
    "create_project",
    "create_task",
    "create_meeting",
    "send_email",
    "update_task",
    "assign_task",
}

_FUNCTION_DECLARATIONS = [
    {"name": "projects_status", "description": "Estado de los proyectos del usuario: tareas abiertas y vencidas.", "parameters": {"type": "object", "properties": {}}},
    {"name": "projects_overview", "description": "Panorama de proyectos accesibles con su responsable/líder, estado, avance en porcentaje (%) y fecha de entrega. Úsala para «qué proyectos lidera X», el avance/porcentaje de uno o varios proyectos, o una visión general.", "parameters": {"type": "object", "properties": {}}},
    {"name": "overdue_tasks", "description": "Lista las tareas vencidas en los proyectos del usuario.", "parameters": {"type": "object", "properties": {}}},
    {"name": "my_tasks", "description": "Tareas abiertas asignadas al usuario actual.", "parameters": {"type": "object", "properties": {}}},
    {"name": "tasks_by_assignee", "description": "Tareas asignadas a una persona (por nombre o correo).", "parameters": {"type": "object", "properties": {"person": {"type": "string"}}, "required": ["person"]}},
    {"name": "recent_activity", "description": "Actividad reciente del repositorio vinculado a los proyectos.", "parameters": {"type": "object", "properties": {}}},
    {"name": "project_summary", "description": "Resumen de un proyecto concreto, por su nombre.", "parameters": {"type": "object", "properties": {"project_name": {"type": "string"}}, "required": ["project_name"]}},
    {"name": "knowledge_search", "description": "Busca en los documentos/base de conocimiento de los proyectos del usuario.", "parameters": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}},
    {"name": "create_project", "description": "Crea un proyecto en un área del usuario.", "parameters": {"type": "object", "properties": {"name": {"type": "string"}, "area_name": {"type": "string"}}, "required": ["name"]}},
    {"name": "create_task", "description": "Crea una tarea dentro de un proyecto.", "parameters": {"type": "object", "properties": {"title": {"type": "string"}, "project_name": {"type": "string"}, "assignee": {"type": "string", "description": "Nombre o correo del responsable, o 'mí' para el usuario actual."}}, "required": ["title"]}},
    {"name": "create_meeting", "description": "Crea una reunión con enlace de Meet e invitados.", "parameters": {"type": "object", "properties": {"title": {"type": "string"}, "attendees": {"type": "array", "items": {"type": "string"}}, "when": {"type": "string", "description": "Fecha/hora ISO 8601 (opcional)"}}, "required": ["title"]}},
    {"name": "send_email", "description": "Envía un correo de notificación.", "parameters": {"type": "object", "properties": {"to": {"type": "array", "items": {"type": "string"}}, "subject": {"type": "string"}, "body": {"type": "string"}}, "required": ["subject"]}},
    {"name": "update_task", "description": "Cambia el estado de una tarea.", "parameters": {"type": "object", "properties": {"title": {"type": "string"}, "status": {"type": "string", "enum": ["todo", "in_progress", "blocked", "done"]}}, "required": ["title", "status"]}},
    {"name": "assign_task", "description": "Asigna una tarea a una persona (nombre o correo).", "parameters": {"type": "object", "properties": {"title": {"type": "string"}, "assignee": {"type": "string"}}, "required": ["title", "assignee"]}},
]

_TOOLS = [types.Tool(function_declarations=_FUNCTION_DECLARATIONS)]


def _default_when() -> str:
    base = datetime.now(timezone.utc) + timedelta(days=1)
    return datetime.combine(base.date(), time(15, 0), tzinfo=timezone.utc).isoformat()


def _map_params(name: str, args: dict[str, Any]) -> dict[str, Any]:
    if name == "create_meeting":
        return {
            "title": args.get("title", "Reunión"),
            "attendees": list(args.get("attendees") or []),
            "when": args.get("when") or _default_when(),
        }
    if name == "send_email":
        return {"to": list(args.get("to") or []), "subject": args.get("subject", ""), "body": args.get("body", "")}
    if name == "create_project":
        return {"name": args.get("name", "Nuevo proyecto"), "area_name": args.get("area_name", "")}
    if name == "create_task":
        return {
            "title": args.get("title", "Nueva tarea"),
            "project_name": args.get("project_name", ""),
            "assignee": args.get("assignee", ""),
        }
    if name == "update_task":
        return {"title": args.get("title", ""), "status": args.get("status", "done")}
    if name == "assign_task":
        return {"title": args.get("title", ""), "assignee": args.get("assignee", "")}
    return dict(args)


def _proposal_text(name: str, params: dict[str, Any]) -> str:
    composer = {
        "create_meeting": _dev.compose_meeting_proposal,
        "send_email": _dev.compose_email_proposal,
        "create_project": _dev.compose_project_proposal,
        "create_task": _dev.compose_task_proposal,
        "update_task": _dev.compose_update_task_proposal,
        "assign_task": _dev.compose_assign_task_proposal,
    }[name]
    return composer(params)


async def _run_read(db: AsyncSession, user: User, name: str, args: dict[str, Any]) -> Any:
    if name == "projects_overview":
        return await tools.projects_overview(db, user)
    if name == "overdue_tasks":
        return await tools.overdue_tasks(db, user)
    if name == "my_tasks":
        return await tools.my_tasks(db, user)
    if name == "tasks_by_assignee":
        return await tools.tasks_by_assignee(db, user, args.get("person", ""))
    if name == "recent_activity":
        return await tools.recent_activity(db, user)
    if name == "project_summary":
        data = await tools.project_summary(db, user, args.get("project_name", ""))
        return data if data is not None else {"found": False}
    if name == "knowledge_search":
        return await tools.knowledge_search(db, user, args.get("query", ""))
    return await tools.projects_status(db, user)


async def run_turn(
    db: AsyncSession, user: User, content: str, history: list[MessageRead]
) -> tuple[str, dict | None]:
    """Devuelve (texto_asistente, accion_pendiente|None)."""
    client = get_gemini_client()
    contents: list[types.Content] = []
    for message in history:
        role = "user" if message.role == "user" else "model"
        contents.append(types.Content(role=role, parts=[types.Part.from_text(text=message.content)]))
    contents.append(types.Content(role="user", parts=[types.Part.from_text(text=content)]))

    system = _system(user)
    config = types.GenerateContentConfig(system_instruction=system, tools=_TOOLS, temperature=0)

    for _ in range(6):
        response = await asyncio.to_thread(
            client.models.generate_content,
            model=settings.gemini_chat_model,
            contents=contents,
            config=config,
        )
        candidate = response.candidates[0]
        parts = candidate.content.parts or []
        calls = [p.function_call for p in parts if getattr(p, "function_call", None)]
        if not calls:
            text = "".join(p.text for p in parts if getattr(p, "text", None))
            return (text.strip() or "¿En qué puedo ayudarte con tus proyectos?"), None

        call = calls[0]
        name = call.name
        args = dict(call.args or {})
        if name in _ACTION_TOOLS:
            params = _map_params(name, args)
            return _proposal_text(name, params), {"type": name, "params": params}

        data = await _run_read(db, user, name, args)
        contents.append(candidate.content)
        contents.append(
            types.Content(
                role="tool",
                parts=[types.Part.from_function_response(name=name, response={"result": data})],
            )
        )

    # Forzar una respuesta final en texto con el contexto ya recogido (sin más herramientas).
    final = await asyncio.to_thread(
        client.models.generate_content,
        model=settings.gemini_chat_model,
        contents=contents,
        config=types.GenerateContentConfig(system_instruction=system, temperature=0),
    )
    text = (final.text or "").strip()
    return (text or "Revisé tus proyectos pero no encontré nada concreto para responder."), None
