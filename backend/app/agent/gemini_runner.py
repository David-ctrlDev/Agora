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
        "responsable, estado, avance % y fecha de entrega). Para una ficha a fondo de UN proyecto "
        "—incluido su ROI, costes, beneficios, sprints y fechas— usa project_details. Para el estado "
        "por áreas o del portafolio (avance y proyectos en riesgo) usa areas_overview; para "
        "vencimientos y «qué se entrega pronto» usa upcoming_deliveries; para alertas y riesgos usa "
        "my_notifications; para el contenido de documentos, actas o transcripciones (incluidos los "
        "importados de Drive) usa knowledge_search. Para las reuniones del usuario, su agenda o «qué "
        "reuniones tengo» (hoy, esta semana, este mes) usa my_meetings con el parámetro days "
        "adecuado (1, 7 o 30); si devuelve connected=false, dile que conecte su cuenta de Google. "
        "Si preguntan por «mis tareas» o «qué "
        "tengo», usa my_tasks; si preguntan por las tareas de una persona (incluido el propio "
        "usuario por su nombre), usa tasks_by_assignee. Para acciones con efecto (crear proyecto o "
        "tarea, crear reunión, enviar correo, cambiar o asignar tareas) llama a la herramienta "
        "correspondiente: el sistema pedirá confirmación antes de ejecutarla. MUY IMPORTANTE: si el "
        "usuario pide un proyecto Y sus tareas (un cronograma o plan, normalmente a partir de un acta "
        "o documento adjunto), usa create_project_with_tasks con TODAS las tareas en una sola "
        "llamada; si pide añadir varias tareas a un proyecto existente, usa create_tasks con la lista "
        "completa. Nunca crees las tareas de una en una ni te detengas tras crear solo el proyecto. "
        "Al extraer tareas de un acta o documento, asigna el responsable de cada una (campo assignee) "
        "cuando el documento lo indique. Para crear o planear un sprint usa create_sprint (acepta "
        "fechas opcionales; si no las hay, usa las de por defecto). "
        "Cuando te pidan un diagrama de flujo, un proceso o un esquema, responde con un bloque de "
        "código ```mermaid``` en sintaxis Mermaid (p. ej. `flowchart TD` con nodos y flechas, o "
        "`sequenceDiagram`); se renderiza como un diagrama profesional en el chat. Si el proceso está "
        "en un acta o documento adjunto, extrae los pasos de ahí; mantén las etiquetas cortas. "
        "Si el usuario pide guardar o asignar un diagrama a un proyecto, usa save_diagram con el "
        "código Mermaid del diagrama; queda en la documentación del proyecto. "
        "Responde SIEMPRE de "
        "forma útil; si no hay datos, dilo con naturalidad y sugiere un siguiente paso."
    )

_ACTION_TOOLS = {
    "create_project",
    "create_task",
    "create_project_with_tasks",
    "create_tasks",
    "create_meeting",
    "send_email",
    "update_task",
    "assign_task",
    "save_diagram",
    "create_sprint",
}

_TASK_ITEM_SCHEMA = {
    "type": "object",
    "properties": {
        "title": {"type": "string"},
        "priority": {"type": "string", "enum": ["low", "medium", "high"]},
        "assignee": {"type": "string", "description": "Nombre o correo del responsable (opcional)."},
        "due_date": {"type": "string", "description": "Fecha ISO YYYY-MM-DD si el documento la indica (opcional)."},
    },
    "required": ["title"],
}

_FUNCTION_DECLARATIONS = [
    {"name": "projects_status", "description": "Estado de los proyectos del usuario: tareas abiertas y vencidas.", "parameters": {"type": "object", "properties": {}}},
    {"name": "projects_overview", "description": "Panorama de proyectos accesibles con su responsable/líder, estado, avance en porcentaje (%) y fecha de entrega. Úsala para «qué proyectos lidera X», el avance/porcentaje de uno o varios proyectos, o una visión general.", "parameters": {"type": "object", "properties": {}}},
    {"name": "overdue_tasks", "description": "Lista las tareas vencidas en los proyectos del usuario.", "parameters": {"type": "object", "properties": {}}},
    {"name": "my_tasks", "description": "Tareas abiertas asignadas al usuario actual.", "parameters": {"type": "object", "properties": {}}},
    {"name": "tasks_by_assignee", "description": "Tareas asignadas a una persona (por nombre o correo).", "parameters": {"type": "object", "properties": {"person": {"type": "string"}}, "required": ["person"]}},
    {"name": "recent_activity", "description": "Actividad reciente del repositorio vinculado a los proyectos.", "parameters": {"type": "object", "properties": {}}},
    {"name": "project_summary", "description": "Resumen de un proyecto concreto, por su nombre.", "parameters": {"type": "object", "properties": {"project_name": {"type": "string"}}, "required": ["project_name"]}},
    {"name": "project_details", "description": "Ficha detallada de un proyecto por su nombre: estado, líder, avance %, categoría, criticidad, fechas, tareas, sprints y un ROI de dos lados — el proceso que lo hace (ejecutor: coste, esfuerzo en horas, equipo, complejidad, recursos) y el proceso para el que se hace (beneficiario: área, beneficio, horas ahorradas/mes y año, personas impactadas, reducción de riesgo, valor estratégico). Úsala para preguntas a fondo sobre un proyecto, su ROI, su impacto o su rentabilidad.", "parameters": {"type": "object", "properties": {"project_name": {"type": "string"}}, "required": ["project_name"]}},
    {"name": "areas_overview", "description": "Panorama por área (nº de proyectos, % de avance y cuántos en riesgo) y totales globales accesibles. Úsala para «cómo va cada área», comparativas entre áreas o el estado general del portafolio.", "parameters": {"type": "object", "properties": {}}},
    {"name": "upcoming_deliveries", "description": "Próximas entregas: proyectos no terminados con fecha de entrega, de la más cercana en adelante (con días restantes y avance). Úsala para «qué se entrega pronto», vencimientos o planificación.", "parameters": {"type": "object", "properties": {}}},
    {"name": "my_meetings", "description": "Reuniones próximas del calendario de Google del usuario (las suyas, no por proyecto): título, fecha/hora, enlace de Meet, lugar y asistentes. Úsala para «qué reuniones tengo», «mi agenda» o «esta semana». El parámetro «days» indica cuántos días hacia adelante mirar (1 = hoy, 7 = esta semana, 30 = este mes).", "parameters": {"type": "object", "properties": {"days": {"type": "integer", "description": "Días hacia adelante (por defecto 7)."}}}},
    {"name": "my_notifications", "description": "Alertas y notificaciones sin leer del usuario (riesgos detectados, resúmenes). Úsala para «tengo alertas», «qué riesgos hay» o «novedades».", "parameters": {"type": "object", "properties": {}}},
    {"name": "knowledge_search", "description": "Busca en los documentos/base de conocimiento de los proyectos del usuario, incluidos los archivos importados desde Drive. Úsala para preguntas sobre el contenido de actas, transcripciones, informes o documentos.", "parameters": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}},
    {"name": "create_project", "description": "Crea un proyecto en un área del usuario.", "parameters": {"type": "object", "properties": {"name": {"type": "string"}, "area_name": {"type": "string"}}, "required": ["name"]}},
    {"name": "create_task", "description": "Crea UNA sola tarea dentro de un proyecto. Si vas a crear varias, usa create_tasks.", "parameters": {"type": "object", "properties": {"title": {"type": "string"}, "project_name": {"type": "string"}, "assignee": {"type": "string", "description": "Nombre o correo del responsable, o 'mí' para el usuario actual."}}, "required": ["title"]}},
    {"name": "create_project_with_tasks", "description": "Crea un proyecto Y su listado completo de tareas en UNA sola confirmación. Úsala siempre que el usuario pida «crea un proyecto y sus tareas», un cronograma o un plan de trabajo, especialmente a partir de un acta o documento adjunto: extrae un nombre de proyecto y TODAS las tareas accionables de una vez (no las crees una por una).", "parameters": {"type": "object", "properties": {"name": {"type": "string"}, "area_name": {"type": "string"}, "tasks": {"type": "array", "items": _TASK_ITEM_SCHEMA}}, "required": ["name", "tasks"]}},
    {"name": "create_tasks", "description": "Crea VARIAS tareas a la vez (lote) en un proyecto que YA existe. Úsala cuando el usuario pida añadir un listado/cronograma de tareas a un proyecto existente (no las crees una por una).", "parameters": {"type": "object", "properties": {"project_name": {"type": "string"}, "tasks": {"type": "array", "items": _TASK_ITEM_SCHEMA}}, "required": ["tasks"]}},
    {"name": "create_meeting", "description": "Crea una reunión con enlace de Meet e invitados.", "parameters": {"type": "object", "properties": {"title": {"type": "string"}, "attendees": {"type": "array", "items": {"type": "string"}}, "when": {"type": "string", "description": "Fecha/hora ISO 8601 (opcional)"}}, "required": ["title"]}},
    {"name": "send_email", "description": "Envía un correo de notificación.", "parameters": {"type": "object", "properties": {"to": {"type": "array", "items": {"type": "string"}}, "subject": {"type": "string"}, "body": {"type": "string"}}, "required": ["subject"]}},
    {"name": "update_task", "description": "Cambia el estado de una tarea.", "parameters": {"type": "object", "properties": {"title": {"type": "string"}, "status": {"type": "string", "enum": ["todo", "in_progress", "blocked", "done"]}}, "required": ["title", "status"]}},
    {"name": "assign_task", "description": "Asigna una tarea a una persona (nombre o correo).", "parameters": {"type": "object", "properties": {"title": {"type": "string"}, "assignee": {"type": "string"}}, "required": ["title", "assignee"]}},
    {"name": "save_diagram", "description": "Guarda en la documentación de un proyecto un diagrama que TÚ generaste (código Mermaid). Úsala cuando el usuario pida guardar o asignar un diagrama a un proyecto. Pasa el código Mermaid completo del diagrama del que se habla.", "parameters": {"type": "object", "properties": {"project_name": {"type": "string"}, "title": {"type": "string"}, "mermaid": {"type": "string", "description": "Código Mermaid completo del diagrama a guardar."}}, "required": ["project_name", "mermaid"]}},
    {"name": "create_sprint", "description": "Crea un sprint en un proyecto. Úsala cuando el usuario pida crear/planear un sprint (p. ej. a partir de un acta o de las tareas existentes). Si no se indican fechas, se usan por defecto (hoy y +14 días).", "parameters": {"type": "object", "properties": {"project_name": {"type": "string"}, "name": {"type": "string"}, "goal": {"type": "string", "description": "Objetivo del sprint (opcional)."}, "start_date": {"type": "string", "description": "Fecha inicio ISO YYYY-MM-DD (opcional)."}, "end_date": {"type": "string", "description": "Fecha fin ISO YYYY-MM-DD (opcional)."}}, "required": ["project_name", "name"]}},
]

_TOOLS = [types.Tool(function_declarations=_FUNCTION_DECLARATIONS)]


def _default_when() -> str:
    # Mañana a las 15:00 hora LOCAL de la empresa (no UTC), para que no se desfase.
    local_tz = timezone(timedelta(hours=settings.app_utc_offset_hours))
    base = datetime.now(local_tz) + timedelta(days=1)
    return datetime.combine(base.date(), time(15, 0), tzinfo=local_tz).isoformat()


def _normalize_tasks(raw: Any) -> list[dict[str, Any]]:
    """Convierte la lista de tareas del modelo en dicts limpios (tolera strings y proto)."""
    items = list(raw) if raw else []
    out: list[dict[str, Any]] = []
    for it in items[:50]:
        if isinstance(it, str):
            title = it.strip()
            if title:
                out.append({"title": title[:300]})
            continue
        try:
            d = dict(it)
        except (TypeError, ValueError):
            continue
        title = str(d.get("title") or "").strip()
        if not title:
            continue
        entry: dict[str, Any] = {"title": title[:300]}
        if d.get("priority") in ("low", "medium", "high"):
            entry["priority"] = d["priority"]
        if d.get("assignee"):
            entry["assignee"] = str(d["assignee"])
        if d.get("due_date"):
            entry["due_date"] = str(d["due_date"])
        out.append(entry)
    return out


def _map_params(name: str, args: dict[str, Any]) -> dict[str, Any]:
    if name == "create_project_with_tasks":
        return {
            "name": args.get("name", "Nuevo proyecto"),
            "area_name": args.get("area_name", ""),
            "tasks": _normalize_tasks(args.get("tasks")),
        }
    if name == "create_tasks":
        return {
            "project_name": args.get("project_name", ""),
            "tasks": _normalize_tasks(args.get("tasks")),
        }
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
    if name == "save_diagram":
        return {
            "project_name": args.get("project_name", ""),
            "title": args.get("title") or "Diagrama",
            "mermaid": args.get("mermaid", ""),
        }
    if name == "create_sprint":
        return {
            "project_name": args.get("project_name", ""),
            "name": args.get("name") or "Sprint",
            "goal": args.get("goal") or "",
            "start_date": args.get("start_date") or "",
            "end_date": args.get("end_date") or "",
        }
    return dict(args)


def _proposal_text(name: str, params: dict[str, Any]) -> str:
    composer = {
        "create_meeting": _dev.compose_meeting_proposal,
        "send_email": _dev.compose_email_proposal,
        "create_project": _dev.compose_project_proposal,
        "create_task": _dev.compose_task_proposal,
        "create_project_with_tasks": _dev.compose_create_project_with_tasks_proposal,
        "create_tasks": _dev.compose_create_tasks_proposal,
        "update_task": _dev.compose_update_task_proposal,
        "assign_task": _dev.compose_assign_task_proposal,
        "save_diagram": _dev.compose_save_diagram_proposal,
        "create_sprint": _dev.compose_create_sprint_proposal,
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
    if name == "project_details":
        data = await tools.project_details(db, user, args.get("project_name", ""))
        return data if data is not None else {"found": False}
    if name == "areas_overview":
        return await tools.areas_overview(db, user)
    if name == "upcoming_deliveries":
        return await tools.upcoming_deliveries(db, user)
    if name == "my_meetings":
        return await tools.my_meetings(db, user, days=int(args.get("days") or 7))
    if name == "my_notifications":
        return await tools.my_notifications(db, user)
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

    for _ in range(8):
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

    # Último turno: ya sin herramientas. Que responda con lo recogido y, si no pudo
    # completar algo, lo diga y sugiera el siguiente paso (en vez de quedarse corto).
    final_system = (
        system
        + " Este es tu ÚLTIMO turno y ya NO puedes usar herramientas. Responde de forma útil con "
        "la información que tengas. Si no pudiste completar algo (faltan datos, no identificaste "
        "el proyecto, o la acción no existe), dilo con claridad y propón el siguiente paso o pide "
        "lo que falta. Nunca respondas en vacío ni con evasivas."
    )
    final = await asyncio.to_thread(
        client.models.generate_content,
        model=settings.gemini_chat_model,
        contents=contents,
        config=types.GenerateContentConfig(system_instruction=final_system, temperature=0),
    )
    text = (final.text or "").strip()
    return (
        text
        or "No logré completar del todo lo que pediste. ¿Me das un poco más de detalle "
        "—el proyecto, las fechas o a quién asignar— para intentarlo de nuevo?"
    ), None
