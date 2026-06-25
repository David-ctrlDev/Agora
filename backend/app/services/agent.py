from datetime import datetime, timezone
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent import actions, gemini_runner, tools
from app.agent.llm import Decision, DevAgentLLM
from app.core.config import settings
from app.models.agent_action import AgentAction
from app.models.agent_attachment import AgentAttachment
from app.models.agent_conversation import AgentConversation
from app.models.agent_message import AgentMessage
from app.models.user import User
from app.schemas.agent import ActionRead, MessageRead

# Límite de texto de adjuntos inyectado al LLM (~6k tokens), para no desbordar el contexto.
_MAX_ATTACH_CHARS = 24000

_llm = DevAgentLLM()
_ACTION_INTENTS = {
    "create_meeting",
    "send_email",
    "create_project",
    "create_task",
    "update_task",
    "assign_task",
}
_PROPOSAL_COMPOSERS = {
    "create_meeting": _llm.compose_meeting_proposal,
    "send_email": _llm.compose_email_proposal,
    "create_project": _llm.compose_project_proposal,
    "create_task": _llm.compose_task_proposal,
    "update_task": _llm.compose_update_task_proposal,
    "assign_task": _llm.compose_assign_task_proposal,
}


def _apply_autotitle(conversation: AgentConversation, content: str) -> None:
    """Nombra la conversación con el primer mensaje del usuario."""
    if conversation.title in (None, "Conversación") and content.strip():
        conversation.title = content.strip()[:60]


class ActionNotPending(Exception):
    """La acción ya fue ejecutada o cancelada."""


async def create_conversation(db: AsyncSession, user: User, title: str | None) -> AgentConversation:
    conversation = AgentConversation(user_id=user.id, title=(title or "Conversación")[:200])
    db.add(conversation)
    await db.commit()
    await db.refresh(conversation)
    return conversation


async def list_conversations(db: AsyncSession, user: User) -> list[AgentConversation]:
    result = await db.execute(
        select(AgentConversation)
        .where(AgentConversation.user_id == user.id)
        .order_by(AgentConversation.created_at.desc())
    )
    return list(result.scalars().all())


async def get_conversation(db: AsyncSession, conversation_id: int) -> AgentConversation | None:
    return await db.get(AgentConversation, conversation_id)


async def delete_conversation(db: AsyncSession, conversation: AgentConversation) -> None:
    await db.execute(delete(AgentAction).where(AgentAction.conversation_id == conversation.id))
    await db.execute(delete(AgentAttachment).where(AgentAttachment.conversation_id == conversation.id))
    await db.execute(delete(AgentMessage).where(AgentMessage.conversation_id == conversation.id))
    await db.delete(conversation)
    await db.commit()


async def add_attachment(
    db: AsyncSession,
    conversation: AgentConversation,
    user: User,
    name: str,
    mime_type: str | None,
    text: str,
    source: str,
) -> AgentAttachment:
    attachment = AgentAttachment(
        conversation_id=conversation.id,
        user_id=user.id,
        name=name[:300],
        mime_type=(mime_type or None),
        source=source,
        char_count=len(text),
        content_text=text,
    )
    db.add(attachment)
    await db.commit()
    await db.refresh(attachment)
    return attachment


async def list_attachments(db: AsyncSession, conversation_id: int) -> list[AgentAttachment]:
    result = await db.execute(
        select(AgentAttachment)
        .where(AgentAttachment.conversation_id == conversation_id)
        .order_by(AgentAttachment.id)
    )
    return list(result.scalars().all())


async def get_attachment(db: AsyncSession, attachment_id: int) -> AgentAttachment | None:
    return await db.get(AgentAttachment, attachment_id)


async def delete_attachment(db: AsyncSession, attachment: AgentAttachment) -> None:
    await db.delete(attachment)
    await db.commit()


async def _load_attachments(
    db: AsyncSession, conversation_id: int, ids: list[int]
) -> list[AgentAttachment]:
    if not ids:
        return []
    result = await db.execute(
        select(AgentAttachment)
        .where(
            AgentAttachment.conversation_id == conversation_id,
            AgentAttachment.id.in_(ids),
        )
        .order_by(AgentAttachment.id)
    )
    return list(result.scalars().all())


def _attachments_note(attachments: list[AgentAttachment]) -> str:
    if not attachments:
        return ""
    names = ", ".join(a.name for a in attachments)
    return f"\n\n📎 *Adjuntos:* {names}"


def _attachments_context(attachments: list[AgentAttachment]) -> str:
    if not attachments:
        return ""
    parts: list[str] = []
    budget = _MAX_ATTACH_CHARS
    for a in attachments:
        text = a.content_text or ""
        if len(text) > budget:
            text = text[:budget].rstrip() + "\n…[contenido truncado]"
        budget -= len(text)
        parts.append(f"--- Documento adjunto: «{a.name}» ---\n{text}")
        if budget <= 0:
            break
    return "\n\n".join(parts)


async def get_action(db: AsyncSession, action_id: int) -> AgentAction | None:
    return await db.get(AgentAction, action_id)


def _to_message_read(message: AgentMessage, action: AgentAction | None = None) -> MessageRead:
    return MessageRead(
        id=message.id,
        role=message.role,
        content=message.content,
        created_at=message.created_at,
        action=ActionRead.model_validate(action) if action is not None else None,
    )


async def list_messages(db: AsyncSession, conversation_id: int) -> list[MessageRead]:
    messages = list(
        (
            await db.execute(
                select(AgentMessage)
                .where(AgentMessage.conversation_id == conversation_id)
                .order_by(AgentMessage.id)
            )
        ).scalars().all()
    )
    action_rows = list(
        (
            await db.execute(
                select(AgentAction).where(AgentAction.conversation_id == conversation_id)
            )
        ).scalars().all()
    )
    by_message = {a.message_id: a for a in action_rows if a.message_id is not None}
    return [_to_message_read(m, by_message.get(m.id)) for m in messages]


async def _run_read(db: AsyncSession, user: User, decision: Decision) -> tuple[str, Any]:
    intent = decision.intent
    if intent == "overdue_tasks":
        return "overdue_tasks", await tools.overdue_tasks(db, user)
    if intent == "recent_activity":
        return "recent_activity", await tools.recent_activity(db, user)
    if intent == "knowledge":
        return "knowledge", await tools.knowledge_search(db, user, decision.args.get("message", ""))
    if intent == "project_summary":
        summary = await tools.project_summary(db, user, decision.args.get("message", ""))
        if summary is None:
            return "projects_status", await tools.projects_status(db, user)
        return "project_summary", summary
    return "projects_status", await tools.projects_status(db, user)


async def _run_gemini(
    db: AsyncSession,
    user: User,
    conversation: AgentConversation,
    content: str,
    attachments: list[AgentAttachment],
) -> MessageRead:
    history = await list_messages(db, conversation.id)
    _apply_autotitle(conversation, content)
    db.add(
        AgentMessage(
            conversation_id=conversation.id,
            role="user",
            content=content + _attachments_note(attachments),
        )
    )
    await db.flush()

    # Inyecta el contenido de TODOS los documentos de la conversación (no solo los de
    # este mensaje) para que el agente conserve el contexto y no haya que re-adjuntar.
    # Recientes primero (por si hay que truncar al presupuesto) y sin duplicar por nombre,
    # de modo que re-adjuntar el mismo archivo no malgaste contexto.
    conv_attachments = await list_attachments(db, conversation.id)
    seen: set[str] = set()
    unique: list[AgentAttachment] = []
    for a in reversed(conv_attachments):
        if a.name in seen:
            continue
        seen.add(a.name)
        unique.append(a)
    block = _attachments_context(unique)
    model_input = f"{block}\n\n---\n\n{content}" if block else content
    text, action = await gemini_runner.run_turn(db, user, model_input, history)
    assistant = AgentMessage(conversation_id=conversation.id, role="assistant", content=text)
    db.add(assistant)
    await db.flush()

    if action is not None:
        agent_action = AgentAction(
            conversation_id=conversation.id,
            message_id=assistant.id,
            user_id=user.id,
            action_type=action["type"],
            params=action["params"],
            status="pending",
        )
        db.add(agent_action)
        await db.commit()
        await db.refresh(assistant)
        await db.refresh(agent_action)
        return _to_message_read(assistant, agent_action)

    await db.commit()
    await db.refresh(assistant)
    return _to_message_read(assistant)


async def run_message(
    db: AsyncSession,
    user: User,
    conversation: AgentConversation,
    content: str,
    attachment_ids: list[int] | None = None,
) -> MessageRead:
    attachments = await _load_attachments(db, conversation.id, attachment_ids or [])
    if settings.gemini_provider == "real":
        return await _run_gemini(db, user, conversation, content, attachments)

    _apply_autotitle(conversation, content)
    db.add(
        AgentMessage(
            conversation_id=conversation.id,
            role="user",
            content=content + _attachments_note(attachments),
        )
    )
    await db.flush()

    decision = _llm.route(content)

    if decision.intent in _ACTION_INTENTS:
        proposal = _PROPOSAL_COMPOSERS[decision.intent](decision.args)
        assistant = AgentMessage(conversation_id=conversation.id, role="assistant", content=proposal)
        db.add(assistant)
        await db.flush()
        action = AgentAction(
            conversation_id=conversation.id,
            message_id=assistant.id,
            user_id=user.id,
            action_type=decision.intent,
            params=decision.args,
            status="pending",
        )
        db.add(action)
        await db.commit()
        await db.refresh(assistant)
        await db.refresh(action)
        return _to_message_read(assistant, action)

    effective_intent, data = await _run_read(db, user, decision)
    text = getattr(_llm, f"compose_{effective_intent}")(data)
    assistant = AgentMessage(conversation_id=conversation.id, role="assistant", content=text)
    db.add(assistant)
    await db.commit()
    await db.refresh(assistant)
    return _to_message_read(assistant)


async def confirm_action(db: AsyncSession, action: AgentAction) -> MessageRead:
    if action.status != "pending":
        raise ActionNotPending()
    if action.action_type == "create_meeting":
        user = await db.get(User, action.user_id)
        result = await actions.execute_create_meeting(db, user, action.params)
        text = _llm.compose_meeting_result(result)
    elif action.action_type == "send_email":
        result = actions.execute_send_email(action.params)
        text = _llm.compose_email_result(result)
    elif action.action_type == "create_project":
        user = await db.get(User, action.user_id)
        result = await actions.execute_create_project(db, user, action.params)
        text = _llm.compose_project_result(result)
    elif action.action_type == "create_task":
        user = await db.get(User, action.user_id)
        result = await actions.execute_create_task(db, user, action.params)
        text = _llm.compose_task_result(result)
    elif action.action_type == "create_project_with_tasks":
        user = await db.get(User, action.user_id)
        result = await actions.execute_create_project_with_tasks(db, user, action.params)
        text = _llm.compose_create_project_with_tasks_result(result)
    elif action.action_type == "create_tasks":
        user = await db.get(User, action.user_id)
        result = await actions.execute_create_tasks(db, user, action.params)
        text = _llm.compose_create_tasks_result(result)
    elif action.action_type == "update_task":
        user = await db.get(User, action.user_id)
        result = await actions.execute_update_task(db, user, action.params)
        text = _llm.compose_update_task_result(result)
    elif action.action_type == "assign_task":
        user = await db.get(User, action.user_id)
        result = await actions.execute_assign_task(db, user, action.params)
        text = _llm.compose_assign_task_result(result)
    elif action.action_type == "save_diagram":
        user = await db.get(User, action.user_id)
        result = await actions.execute_save_diagram(db, user, action.params)
        text = _llm.compose_save_diagram_result(result)
    elif action.action_type == "create_sprint":
        user = await db.get(User, action.user_id)
        result = await actions.execute_create_sprint(db, user, action.params)
        text = _llm.compose_create_sprint_result(result)
    elif action.action_type == "archive_project":
        user = await db.get(User, action.user_id)
        result = await actions.execute_archive_project(db, user, action.params)
        text = _llm.compose_archive_project_result(result)
    elif action.action_type == "delete_project":
        user = await db.get(User, action.user_id)
        result = await actions.execute_delete_project(db, user, action.params)
        text = _llm.compose_delete_project_result(result)
    elif action.action_type == "delete_task":
        user = await db.get(User, action.user_id)
        result = await actions.execute_delete_task(db, user, action.params)
        text = _llm.compose_delete_task_result(result)
    elif action.action_type == "comment_task":
        user = await db.get(User, action.user_id)
        result = await actions.execute_comment_task(db, user, action.params)
        text = _llm.compose_comment_task_result(result)
    elif action.action_type == "update_project":
        user = await db.get(User, action.user_id)
        result = await actions.execute_update_project(db, user, action.params)
        text = _llm.compose_update_project_result(result)
    elif action.action_type == "add_project_member":
        user = await db.get(User, action.user_id)
        result = await actions.execute_add_project_member(db, user, action.params)
        text = _llm.compose_add_project_member_result(result)
    elif action.action_type == "remove_project_member":
        user = await db.get(User, action.user_id)
        result = await actions.execute_remove_project_member(db, user, action.params)
        text = _llm.compose_remove_project_member_result(result)
    elif action.action_type == "update_sprint":
        user = await db.get(User, action.user_id)
        result = await actions.execute_update_sprint(db, user, action.params)
        text = _llm.compose_update_sprint_result(result)
    elif action.action_type == "delete_sprint":
        user = await db.get(User, action.user_id)
        result = await actions.execute_delete_sprint(db, user, action.params)
        text = _llm.compose_delete_sprint_result(result)
    else:
        result = {"ok": False}
        text = "Acción no soportada."
    action.status = "executed"
    action.result = result
    action.executed_at = datetime.now(timezone.utc)
    message = AgentMessage(conversation_id=action.conversation_id, role="assistant", content=text)
    db.add(message)
    await db.commit()
    await db.refresh(message)
    return _to_message_read(message)


async def cancel_action(db: AsyncSession, action: AgentAction) -> MessageRead:
    if action.status == "pending":
        action.status = "cancelled"
    message = AgentMessage(
        conversation_id=action.conversation_id, role="assistant", content="Acción cancelada."
    )
    db.add(message)
    await db.commit()
    await db.refresh(message)
    return _to_message_read(message)
