"""Agente real sobre Gemini con function-calling.

Las tools de lectura se ejecutan en bucle (acotadas por área); las acciones con
efecto NO se ejecutan: se devuelven como propuesta para que el usuario confirme.
"""
import asyncio
from datetime import datetime, time, timedelta, timezone
from typing import Any

from google.genai import types
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent import actions, tools
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
        "importados de Drive) usa knowledge_search. Google y Drive: google_status dice si hay conexión "
        "(si algo falla por falta de conexión, dile que conecte Google; nunca intentes iniciar sesión "
        "por él); search_drive busca archivos en su Drive; list_project_documents lista los documentos "
        "de un proyecto; import_drive_to_project importa al proyecto los archivos de Drive que coincidan "
        "con un término y los indexa (el servidor resuelve los archivos: tú solo das proyecto y término); "
        "sync_project_drive re-sincroniza. Para las reuniones del usuario, su agenda o «qué "
        "reuniones tengo» (hoy, esta semana, este mes) usa my_meetings con el parámetro days "
        "adecuado (1, 7 o 30); si devuelve connected=false, dile que conecte su cuenta de Google. "
        "Para agendar una reunión de un proyecto «cuando todos coincidan» o «que respete la "
        "disponibilidad», usa SIEMPRE schedule_meeting(project_name, duration_minutes): el servidor "
        "calcula el PRIMER hueco común (free/busy de todos los miembros, en horario laboral evitando "
        "el almuerzo) y toma como asistentes a los MIEMBROS REALES del proyecto, y te devuelve la "
        "reunión lista para confirmar. NUNCA inventes ni reescribas la hora o los asistentes, ni uses "
        "create_meeting para esto. Si te piden una duración concreta («de 1 hora», «media hora», «2 "
        "horas»), pásala como duration_minutes. Si no hay hueco, di el motivo y ofrece ampliar el "
        "plazo (days_ahead). IMPORTANTE — distingue PREGUNTA de ORDEN: solo llama a schedule_meeting "
        "cuando el usuario PIDA explícitamente agendar/crear/cambiar la reunión. Si el usuario hace una "
        "PREGUNTA sobre la reunión ya propuesta («¿es el primer hueco disponible?», «¿por qué esa "
        "hora?», «¿quiénes van?», «¿no hay antes?»), NO crees otra propuesta: RESPÓNDELE EN TEXTO. El "
        "hueco que propone schedule_meeting YA es el más temprano posible por construcción, así que a "
        "«¿es el primero?» respóndele que sí y explícalo (es el primer momento en horario laboral, "
        "evitando el almuerzo, en que TODOS están libres; puede correrse si cambia su disponibilidad). "
        "Si necesitas verificar, usa find_meeting_slot, que solo CONSULTA y NO crea nada. La propuesta "
        "anterior SIGUE VIGENTE: recuérdale que puede confirmarla con el botón «Confirmar y ejecutar» "
        "(o pedir cambios); no la repitas ni la des por perdida. Usa "
        "create_meeting solo para reuniones con hora y asistentes EXPLÍCITOS que indique el usuario. "
        "Si preguntan por «mis tareas» o «qué "
        "tengo», usa my_tasks; si preguntan por las tareas de una persona (incluido el propio "
        "usuario por su nombre), usa tasks_by_assignee; para «las tareas del proyecto X» o ver su "
        "tablero, usa list_tasks. Sobre una tarea concreta: update_task edita estado, prioridad, "
        "fecha, título o descripción (solo los campos a cambiar); assign_task (re)asigna responsable; "
        "delete_task la elimina; comment_task le añade un comentario. Para acciones con efecto (crear "
        "proyecto o tarea, crear/agendar reunión, enviar correo, editar/asignar/eliminar/comentar "
        "tareas, archivar/eliminar proyectos) llama a la herramienta "
        "correspondiente: el sistema pedirá confirmación antes de ejecutarla. MUY IMPORTANTE: si el "
        "usuario pide un proyecto Y sus tareas (un cronograma o plan, normalmente a partir de un acta "
        "o documento adjunto), usa create_project_with_tasks con TODAS las tareas en una sola "
        "llamada; si pide añadir varias tareas a un proyecto existente, usa create_tasks con la lista "
        "completa. Nunca crees las tareas de una en una ni te detengas tras crear solo el proyecto. "
        "Al extraer tareas de un acta o documento y asignar responsables: pon en assignee a la "
        "PERSONA QUE NOMBRA EL DOCUMENTO para esa tarea (su nombre o correo), NO al usuario actual. "
        "Si el documento no indica responsable para una tarea, déjala SIN asignar (assignee vacío). "
        "Nunca asignes todas las tareas al usuario que pide salvo que el documento lo diga. "
        "Para crear o planear un sprint usa create_sprint (acepta fechas opcionales; si no las hay, "
        "usa las de por defecto); para ver los sprints usa list_sprints, para editar uno update_sprint "
        "y para borrarlo delete_sprint. "
        "Cuando te pidan un diagrama de flujo, un proceso o un esquema, responde con un bloque de "
        "código ```mermaid``` en sintaxis Mermaid (p. ej. `flowchart TD` con nodos y flechas, o "
        "`sequenceDiagram`); se renderiza como un diagrama profesional en el chat. Si el proceso está "
        "en un acta o documento adjunto, extrae los pasos de ahí; mantén las etiquetas cortas. "
        "Si el usuario pide guardar o asignar un diagrama a un proyecto, usa save_diagram con el "
        "código Mermaid del diagrama; queda en la documentación del proyecto. "
        "Para archivar un proyecto (quitarlo de la vista activa, REVERSIBLE) usa archive_project; "
        "para eliminarlo PERMANENTEMENTE (irreversible, solo propietario/admin) usa delete_project. "
        "Si el usuario dice «elimina/borra» pero parece que solo quiere ocultarlo, ofrécele archivarlo. "
        "Para cambiar datos de un proyecto (estado, nombre, descripción, fechas, avance, criticidad, "
        "categoría o dueño) usa update_project con solo los campos a cambiar. Para el equipo del "
        "proyecto: list_project_members (ver), add_project_member (añadir o cambiar rol) y "
        "remove_project_member (quitar). Todas piden confirmación antes de ejecutarse. "
        "Áreas y usuarios (gestión): list_areas y list_users para consultar; create_area/update_area, "
        "create_user/update_user_admin y set_user_areas para gestionar. Crear/editar áreas y usuarios "
        "es SOLO para administradores; si el usuario no lo es, el servidor lo rechazará: explícaselo. "
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
    "archive_project",
    "delete_project",
    "delete_task",
    "comment_task",
    "update_project",
    "add_project_member",
    "remove_project_member",
    "update_sprint",
    "delete_sprint",
    "create_area",
    "update_area",
    "create_user",
    "update_user_admin",
    "set_user_areas",
    "sync_project_drive",
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
    {"name": "list_tasks", "description": "Lista TODAS las tareas de un proyecto (título, estado, prioridad, responsable y fecha). Úsala para «qué tareas tiene el proyecto X», «lístame las tareas de X» o para ver el tablero de un proyecto.", "parameters": {"type": "object", "properties": {"project_name": {"type": "string"}}, "required": ["project_name"]}},
    {"name": "recent_activity", "description": "Actividad reciente del repositorio vinculado a los proyectos.", "parameters": {"type": "object", "properties": {}}},
    {"name": "project_summary", "description": "Resumen de un proyecto concreto, por su nombre.", "parameters": {"type": "object", "properties": {"project_name": {"type": "string"}}, "required": ["project_name"]}},
    {"name": "project_details", "description": "Ficha detallada de un proyecto por su nombre: estado, líder, avance %, categoría, criticidad, fechas, tareas, sprints y un ROI de dos lados — el proceso que lo hace (ejecutor: coste, esfuerzo en horas, equipo, complejidad, recursos) y el proceso para el que se hace (beneficiario: área, beneficio, horas ahorradas/mes y año, personas impactadas, reducción de riesgo, valor estratégico). Úsala para preguntas a fondo sobre un proyecto, su ROI, su impacto o su rentabilidad.", "parameters": {"type": "object", "properties": {"project_name": {"type": "string"}}, "required": ["project_name"]}},
    {"name": "areas_overview", "description": "Panorama por área (nº de proyectos, % de avance y cuántos en riesgo) y totales globales accesibles. Úsala para «cómo va cada área», comparativas entre áreas o el estado general del portafolio.", "parameters": {"type": "object", "properties": {}}},
    {"name": "upcoming_deliveries", "description": "Próximas entregas: proyectos no terminados con fecha de entrega, de la más cercana en adelante (con días restantes y avance). Úsala para «qué se entrega pronto», vencimientos o planificación.", "parameters": {"type": "object", "properties": {}}},
    {"name": "my_meetings", "description": "Reuniones próximas del calendario de Google del usuario (las suyas, no por proyecto): título, fecha/hora, enlace de Meet, lugar y asistentes. Úsala para «qué reuniones tengo», «mi agenda» o «esta semana». El parámetro «days» indica cuántos días hacia adelante mirar (1 = hoy, 7 = esta semana, 30 = este mes).", "parameters": {"type": "object", "properties": {"days": {"type": "integer", "description": "Días hacia adelante (por defecto 7)."}}}},
    {"name": "find_meeting_slot", "description": "Mira la disponibilidad (free/busy de Calendar) de TODOS los miembros de un proyecto y propone el primer hueco común en horario laboral (8–17) de lunes a viernes, evitando el almuerzo (12–14). Úsala SIEMPRE antes de agendar una reunión «cuando todos estén libres» / «que coincida la disponibilidad». Devuelve start (ISO con zona), end, duration_minutes y attendees (los correos de los miembros). Después llama a create_meeting con ese when y esos attendees; no inventes el horario.", "parameters": {"type": "object", "properties": {"project_name": {"type": "string"}, "duration_minutes": {"type": "integer", "description": "Duración en minutos (por defecto 60)."}, "days_ahead": {"type": "integer", "description": "Días hacia adelante a explorar (por defecto 7)."}}, "required": ["project_name"]}},
    {"name": "my_notifications", "description": "Alertas y notificaciones sin leer del usuario (riesgos detectados, resúmenes). Úsala para «tengo alertas», «qué riesgos hay» o «novedades».", "parameters": {"type": "object", "properties": {}}},
    {"name": "knowledge_search", "description": "Busca en los documentos/base de conocimiento de los proyectos del usuario, incluidos los archivos importados desde Drive. Úsala para preguntas sobre el contenido de actas, transcripciones, informes o documentos.", "parameters": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}},
    {"name": "google_status", "description": "Estado de la conexión de Google del usuario (si está conectado y con qué permisos). Úsala para «¿tengo Google conectado?» o cuando una acción de Drive/Calendar/Correo falle por falta de conexión.", "parameters": {"type": "object", "properties": {}}},
    {"name": "search_drive", "description": "Busca archivos y carpetas en el Drive del usuario por nombre/término (solo consulta, no importa nada). Úsala para «busca en mi Drive…», «¿tengo el archivo X?» o para localizar documentos antes de importarlos.", "parameters": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}},
    {"name": "list_project_documents", "description": "Lista los documentos vinculados a un proyecto (subidos, importados de Drive o generados), con su origen y fecha. Úsala para «qué documentos tiene el proyecto X».", "parameters": {"type": "object", "properties": {"project_name": {"type": "string"}}, "required": ["project_name"]}},
    {"name": "import_drive_to_project", "description": "Importa al proyecto los archivos de Drive que coincidan con la búsqueda y los indexa para que el agente pueda buscarlos (RAG). El servidor localiza los archivos por el término (no manejes IDs). Úsala para «importa del Drive el acta/los informes… al proyecto X». Requiere edición y Google conectado.", "parameters": {"type": "object", "properties": {"project_name": {"type": "string"}, "query": {"type": "string", "description": "Nombre o término de los archivos a importar."}}, "required": ["project_name", "query"]}},
    {"name": "sync_project_drive", "description": "Re-sincroniza con Google los documentos vinculados al proyecto (trae novedades). Úsala para «sincroniza el Drive/Google del proyecto X». Requiere edición y Google conectado.", "parameters": {"type": "object", "properties": {"project_name": {"type": "string"}}, "required": ["project_name"]}},
    {"name": "create_project", "description": "Crea un proyecto en un área del usuario.", "parameters": {"type": "object", "properties": {"name": {"type": "string"}, "area_name": {"type": "string"}}, "required": ["name"]}},
    {"name": "create_task", "description": "Crea UNA sola tarea dentro de un proyecto. Si vas a crear varias, usa create_tasks.", "parameters": {"type": "object", "properties": {"title": {"type": "string"}, "project_name": {"type": "string"}, "assignee": {"type": "string", "description": "Nombre o correo del responsable, o 'mí' para el usuario actual."}}, "required": ["title"]}},
    {"name": "create_project_with_tasks", "description": "Crea un proyecto Y su listado completo de tareas en UNA sola confirmación. Úsala siempre que el usuario pida «crea un proyecto y sus tareas», un cronograma o un plan de trabajo, especialmente a partir de un acta o documento adjunto: extrae un nombre de proyecto y TODAS las tareas accionables de una vez (no las crees una por una).", "parameters": {"type": "object", "properties": {"name": {"type": "string"}, "area_name": {"type": "string"}, "tasks": {"type": "array", "items": _TASK_ITEM_SCHEMA}}, "required": ["name", "tasks"]}},
    {"name": "create_tasks", "description": "Crea VARIAS tareas a la vez (lote) en un proyecto que YA existe. Úsala cuando el usuario pida añadir un listado/cronograma de tareas a un proyecto existente (no las crees una por una).", "parameters": {"type": "object", "properties": {"project_name": {"type": "string"}, "tasks": {"type": "array", "items": _TASK_ITEM_SCHEMA}}, "required": ["tasks"]}},
    {"name": "create_meeting", "description": "Crea una reunión con enlace de Meet e invitados. Para reuniones de un proyecto «cuando todos estén libres», llama antes a find_meeting_slot y pasa aquí su start como when, sus attendees y el mismo duration_minutes.", "parameters": {"type": "object", "properties": {"title": {"type": "string"}, "attendees": {"type": "array", "items": {"type": "string"}, "description": "Correos de los invitados."}, "when": {"type": "string", "description": "Fecha/hora ISO 8601 (idealmente el start que devuelve find_meeting_slot, con zona horaria)."}, "duration_minutes": {"type": "integer", "description": "Duración en minutos (por defecto 60)."}, "project_name": {"type": "string", "description": "Proyecto al que pertenece la reunión, para enlazarla (opcional)."}}, "required": ["title"]}},
    {"name": "schedule_meeting", "description": "Agenda una reunión de un proyecto EN EL PRIMER HUECO COMÚN de todos sus miembros (el servidor calcula el horario con free/busy y usa como asistentes a los miembros reales del proyecto). Úsala para «reúnenos cuando todos coincidan / respetando la disponibilidad». Es determinista: no inventes ni pases tú la hora ni los asistentes; solo el proyecto, la duración y, si quieres, el título. Devuelve la reunión lista para confirmar.", "parameters": {"type": "object", "properties": {"project_name": {"type": "string"}, "title": {"type": "string", "description": "Título de la reunión (opcional)."}, "duration_minutes": {"type": "integer", "description": "Duración en minutos (por defecto 60)."}, "days_ahead": {"type": "integer", "description": "Días hacia adelante a explorar (por defecto 7)."}}, "required": ["project_name"]}},
    {"name": "send_email", "description": "Envía un correo de notificación.", "parameters": {"type": "object", "properties": {"to": {"type": "array", "items": {"type": "string"}}, "subject": {"type": "string"}, "body": {"type": "string"}}, "required": ["subject"]}},
    {"name": "update_task", "description": "Edita una tarea existente (la identifica por su título). Puede cambiar el estado, la prioridad, la fecha de entrega, el título o la descripción — pasa solo los campos a cambiar. Para cambiar el RESPONSABLE usa assign_task.", "parameters": {"type": "object", "properties": {"title": {"type": "string", "description": "Título actual de la tarea a editar."}, "status": {"type": "string", "enum": ["todo", "in_progress", "blocked", "done"]}, "priority": {"type": "string", "enum": ["low", "medium", "high"]}, "due_date": {"type": "string", "description": "Nueva fecha de entrega ISO YYYY-MM-DD."}, "new_title": {"type": "string", "description": "Nuevo título (si se renombra)."}, "description": {"type": "string", "description": "Nueva descripción."}}, "required": ["title"]}},
    {"name": "assign_task", "description": "Asigna/reasigna una tarea a una persona (nombre o correo, o «mí»).", "parameters": {"type": "object", "properties": {"title": {"type": "string"}, "assignee": {"type": "string"}}, "required": ["title", "assignee"]}},
    {"name": "delete_task", "description": "Elimina una tarea (la identifica por su título). Irreversible; requiere permiso de edición en el proyecto.", "parameters": {"type": "object", "properties": {"title": {"type": "string"}}, "required": ["title"]}},
    {"name": "comment_task", "description": "Añade un comentario a una tarea (identificada por su título).", "parameters": {"type": "object", "properties": {"title": {"type": "string"}, "body": {"type": "string", "description": "Texto del comentario."}}, "required": ["title", "body"]}},
    {"name": "save_diagram", "description": "Guarda en la documentación de un proyecto un diagrama que TÚ generaste (código Mermaid). Úsala cuando el usuario pida guardar o asignar un diagrama a un proyecto. Pasa el código Mermaid completo del diagrama del que se habla.", "parameters": {"type": "object", "properties": {"project_name": {"type": "string"}, "title": {"type": "string"}, "mermaid": {"type": "string", "description": "Código Mermaid completo del diagrama a guardar."}}, "required": ["project_name", "mermaid"]}},
    {"name": "create_sprint", "description": "Crea un sprint en un proyecto. Úsala cuando el usuario pida crear/planear un sprint (p. ej. a partir de un acta o de las tareas existentes). Si no se indican fechas, se usan por defecto (hoy y +14 días).", "parameters": {"type": "object", "properties": {"project_name": {"type": "string"}, "name": {"type": "string"}, "goal": {"type": "string", "description": "Objetivo del sprint (opcional)."}, "start_date": {"type": "string", "description": "Fecha inicio ISO YYYY-MM-DD (opcional)."}, "end_date": {"type": "string", "description": "Fecha fin ISO YYYY-MM-DD (opcional)."}}, "required": ["project_name", "name"]}},
    {"name": "list_sprints", "description": "Lista los sprints de un proyecto (nombre, objetivo, fechas y estado). Úsala para «qué sprints tiene X» o ver su planificación.", "parameters": {"type": "object", "properties": {"project_name": {"type": "string"}}, "required": ["project_name"]}},
    {"name": "update_sprint", "description": "Edita un sprint existente (lo identifica por su nombre dentro del proyecto). Cambia nombre (new_name), objetivo (goal), fechas o estado (planned/active/completed). Pasa solo los campos a cambiar.", "parameters": {"type": "object", "properties": {"project_name": {"type": "string"}, "sprint_name": {"type": "string"}, "new_name": {"type": "string"}, "goal": {"type": "string"}, "start_date": {"type": "string", "description": "ISO YYYY-MM-DD."}, "end_date": {"type": "string", "description": "ISO YYYY-MM-DD."}, "status": {"type": "string", "enum": ["planned", "active", "completed"]}}, "required": ["project_name", "sprint_name"]}},
    {"name": "delete_sprint", "description": "Elimina un sprint (identificado por su nombre dentro del proyecto). Irreversible; requiere edición.", "parameters": {"type": "object", "properties": {"project_name": {"type": "string"}, "sprint_name": {"type": "string"}}, "required": ["project_name", "sprint_name"]}},
    {"name": "list_project_members", "description": "Lista los miembros de un proyecto (nombre, correo y rol). Úsala para «quiénes están en el proyecto X» o «sus miembros».", "parameters": {"type": "object", "properties": {"project_name": {"type": "string"}}, "required": ["project_name"]}},
    {"name": "update_project", "description": "Edita campos de un proyecto existente (lo identifica por su nombre). Puede cambiar: estado (planned/active/on_hold/done/archived), nombre (new_name), descripción, fecha de inicio/entrega, avance (0–100), criticidad, categoría o dueño (owner por nombre/correo). Pasa solo los campos a cambiar. Para archivar puedes usar esto con status=archived o archive_project.", "parameters": {"type": "object", "properties": {"project_name": {"type": "string"}, "status": {"type": "string", "enum": ["planned", "active", "on_hold", "done", "archived"]}, "new_name": {"type": "string"}, "description": {"type": "string"}, "start_date": {"type": "string", "description": "ISO YYYY-MM-DD."}, "due_date": {"type": "string", "description": "ISO YYYY-MM-DD."}, "progress": {"type": "integer", "description": "Avance 0–100."}, "criticality": {"type": "string"}, "category": {"type": "string"}, "owner": {"type": "string", "description": "Nuevo dueño (nombre o correo)."}}, "required": ["project_name"]}},
    {"name": "add_project_member", "description": "Añade una persona como miembro de un proyecto (o cambia su rol si ya es miembro). Requiere permiso de edición.", "parameters": {"type": "object", "properties": {"project_name": {"type": "string"}, "person": {"type": "string", "description": "Nombre o correo de la persona."}, "role": {"type": "string", "enum": ["owner", "editor", "viewer"], "description": "Rol (por defecto editor)."}}, "required": ["project_name", "person"]}},
    {"name": "remove_project_member", "description": "Quita a una persona de los miembros de un proyecto. Requiere permiso de edición.", "parameters": {"type": "object", "properties": {"project_name": {"type": "string"}, "person": {"type": "string", "description": "Nombre o correo de la persona."}}, "required": ["project_name", "person"]}},
    {"name": "archive_project", "description": "Archiva un proyecto (pasa a estado «archivado»). Es REVERSIBLE. Úsala cuando el usuario quiera quitar un proyecto de la vista activa sin borrarlo. Requiere permiso de edición sobre el proyecto.", "parameters": {"type": "object", "properties": {"project_name": {"type": "string"}}, "required": ["project_name"]}},
    {"name": "delete_project", "description": "Elimina un proyecto PERMANENTEMENTE, junto con sus tareas, comentarios y documentos. Es IRREVERSIBLE. Solo el propietario o un admin puede hacerlo. Úsala solo cuando el usuario pida explícitamente borrar/eliminar un proyecto; si parece que solo quiere quitarlo de la vista, sugiérele archivarlo (archive_project).", "parameters": {"type": "object", "properties": {"project_name": {"type": "string"}}, "required": ["project_name"]}},
    {"name": "list_areas", "description": "Lista las áreas (departamentos) de Invesa con su nº de proyectos. Úsala para «qué áreas hay» o «cuántos proyectos por área».", "parameters": {"type": "object", "properties": {}}},
    {"name": "list_users", "description": "Lista los usuarios del sistema (nombre, correo, rol, activo). Solo administradores.", "parameters": {"type": "object", "properties": {}}},
    {"name": "create_area", "description": "Crea una nueva área/departamento. Solo administradores.", "parameters": {"type": "object", "properties": {"name": {"type": "string"}, "description": {"type": "string"}}, "required": ["name"]}},
    {"name": "update_area", "description": "Edita un área (nombre o descripción), identificándola por su nombre actual. Solo administradores.", "parameters": {"type": "object", "properties": {"area_name": {"type": "string"}, "new_name": {"type": "string"}, "description": {"type": "string"}}, "required": ["area_name"]}},
    {"name": "create_user", "description": "Crea un usuario (correo del dominio de la empresa, nombre y rol). Solo administradores. Para asignarle áreas usa después set_user_areas.", "parameters": {"type": "object", "properties": {"email": {"type": "string"}, "name": {"type": "string"}, "role": {"type": "string", "enum": ["admin", "member"]}}, "required": ["email", "name"]}},
    {"name": "update_user_admin", "description": "Edita un usuario (lo identifica por nombre o correo): cambia nombre (new_name), correo (new_email), rol o si está activo (is_active). Solo administradores.", "parameters": {"type": "object", "properties": {"person": {"type": "string"}, "new_name": {"type": "string"}, "new_email": {"type": "string"}, "role": {"type": "string", "enum": ["admin", "member"]}, "is_active": {"type": "boolean"}}, "required": ["person"]}},
    {"name": "set_user_areas", "description": "Define a qué áreas pertenece un usuario (reemplaza sus áreas actuales). Solo administradores.", "parameters": {"type": "object", "properties": {"person": {"type": "string"}, "area_names": {"type": "array", "items": {"type": "string"}}}, "required": ["person", "area_names"]}},
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
            "duration_minutes": int(args.get("duration_minutes") or 60),
            "project_name": args.get("project_name") or None,
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
        return {
            "title": args.get("title", ""),
            "status": args.get("status") or "",
            "priority": args.get("priority") or "",
            "due_date": args.get("due_date") or "",
            "new_title": args.get("new_title") or "",
            "description": args.get("description") or "",
        }
    if name == "assign_task":
        return {"title": args.get("title", ""), "assignee": args.get("assignee", "")}
    if name == "delete_task":
        return {"title": args.get("title", "")}
    if name == "comment_task":
        return {"title": args.get("title", ""), "body": args.get("body", "")}
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
    if name in ("archive_project", "delete_project"):
        return {"project_name": args.get("project_name", "")}
    if name == "update_project":
        return {
            "project_name": args.get("project_name", ""),
            "status": args.get("status") or "",
            "new_name": args.get("new_name") or "",
            "description": args.get("description") or "",
            "start_date": args.get("start_date") or "",
            "due_date": args.get("due_date") or "",
            "progress": args.get("progress") if args.get("progress") is not None else "",
            "criticality": args.get("criticality") or "",
            "category": args.get("category") or "",
            "owner": args.get("owner") or "",
        }
    if name == "add_project_member":
        return {
            "project_name": args.get("project_name", ""),
            "person": args.get("person", ""),
            "role": args.get("role") or "editor",
        }
    if name == "remove_project_member":
        return {"project_name": args.get("project_name", ""), "person": args.get("person", "")}
    if name == "update_sprint":
        return {
            "project_name": args.get("project_name", ""),
            "sprint_name": args.get("sprint_name", ""),
            "new_name": args.get("new_name") or "",
            "goal": args.get("goal") or "",
            "start_date": args.get("start_date") or "",
            "end_date": args.get("end_date") or "",
            "status": args.get("status") or "",
        }
    if name == "delete_sprint":
        return {"project_name": args.get("project_name", ""), "sprint_name": args.get("sprint_name", "")}
    if name == "create_area":
        return {"name": args.get("name", ""), "description": args.get("description") or ""}
    if name == "update_area":
        return {
            "area_name": args.get("area_name", ""),
            "new_name": args.get("new_name") or "",
            "description": args.get("description") or "",
        }
    if name == "create_user":
        return {
            "email": args.get("email", ""),
            "name": args.get("name", ""),
            "role": args.get("role") or "member",
        }
    if name == "update_user_admin":
        out = {
            "person": args.get("person", ""),
            "new_name": args.get("new_name") or "",
            "new_email": args.get("new_email") or "",
            "role": args.get("role") or "",
        }
        if "is_active" in args and args.get("is_active") is not None:
            out["is_active"] = bool(args.get("is_active"))
        return out
    if name == "set_user_areas":
        return {"person": args.get("person", ""), "area_names": list(args.get("area_names") or [])}
    if name == "sync_project_drive":
        return {"project_name": args.get("project_name", "")}
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
        "archive_project": _dev.compose_archive_project_proposal,
        "delete_project": _dev.compose_delete_project_proposal,
        "delete_task": _dev.compose_delete_task_proposal,
        "comment_task": _dev.compose_comment_task_proposal,
        "update_project": _dev.compose_update_project_proposal,
        "add_project_member": _dev.compose_add_project_member_proposal,
        "remove_project_member": _dev.compose_remove_project_member_proposal,
        "update_sprint": _dev.compose_update_sprint_proposal,
        "delete_sprint": _dev.compose_delete_sprint_proposal,
        "create_area": _dev.compose_create_area_proposal,
        "update_area": _dev.compose_update_area_proposal,
        "create_user": _dev.compose_create_user_proposal,
        "update_user_admin": _dev.compose_update_user_admin_proposal,
        "set_user_areas": _dev.compose_set_user_areas_proposal,
        "import_drive": _dev.compose_import_drive_proposal,
        "sync_project_drive": _dev.compose_sync_project_drive_proposal,
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
    if name == "list_tasks":
        return await tools.list_tasks(db, user, args.get("project_name", ""))
    if name == "list_project_members":
        return await tools.list_project_members(db, user, args.get("project_name", ""))
    if name == "list_sprints":
        return await tools.list_sprints(db, user, args.get("project_name", ""))
    if name == "list_areas":
        return await tools.list_areas(db, user)
    if name == "list_users":
        return await tools.list_users(db, user)
    if name == "google_status":
        return await tools.google_status(db, user)
    if name == "search_drive":
        return await tools.search_drive(db, user, args.get("query", ""))
    if name == "list_project_documents":
        return await tools.list_project_documents(db, user, args.get("project_name", ""))
    if name == "my_meetings":
        return await tools.my_meetings(db, user, days=int(args.get("days") or 7))
    if name == "find_meeting_slot":
        return await tools.find_meeting_slot(
            db,
            user,
            args.get("project_name", ""),
            duration_minutes=int(args.get("duration_minutes") or 60),
            days_ahead=int(args.get("days_ahead") or 7),
        )
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
        if name == "schedule_meeting":
            # Agendamiento AUTORITATIVO del servidor: hora y asistentes deterministas
            # (el agente no los provee, así no puede corromperlos).
            slot = await tools.find_meeting_slot(
                db,
                user,
                args.get("project_name", ""),
                duration_minutes=int(args.get("duration_minutes") or 60),
                days_ahead=int(args.get("days_ahead") or 7),
            )
            if not slot.get("found"):
                contents.append(candidate.content)
                contents.append(
                    types.Content(
                        role="tool",
                        parts=[types.Part.from_function_response(name=name, response={"result": slot})],
                    )
                )
                continue
            project_label = slot.get("project") or "proyecto"
            params = {
                "title": (args.get("title") or "").strip() or f"Seguimiento: {project_label}",
                "attendees": slot.get("attendees") or [],
                "when": slot["start"],
                "duration_minutes": int(slot.get("duration_minutes") or 60),
                "project_name": slot.get("project"),
            }
            return _proposal_text("create_meeting", params), {"type": "create_meeting", "params": params}
        if name == "import_drive_to_project":
            # El servidor resuelve los archivos de Drive (el agente no maneja IDs).
            prep = await actions.prepare_import_drive(
                db, user, args.get("project_name", ""), args.get("query", "")
            )
            if not prep.get("ok"):
                contents.append(candidate.content)
                contents.append(
                    types.Content(
                        role="tool",
                        parts=[types.Part.from_function_response(name=name, response={"result": prep})],
                    )
                )
                continue
            params = dict(prep["params"])
            params["titles"] = prep["titles"]
            return _proposal_text("import_drive", params), {"type": "import_drive", "params": params}
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
