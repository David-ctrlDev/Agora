from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent import actions, tools
from app.agent.llm import Decision, DevAgentLLM
from app.models.agent_action import AgentAction
from app.models.agent_conversation import AgentConversation
from app.models.agent_message import AgentMessage
from app.models.user import User
from app.schemas.agent import ActionRead, MessageRead

_llm = DevAgentLLM()
_ACTION_INTENTS = {"create_meeting", "send_email"}


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


async def run_message(
    db: AsyncSession, user: User, conversation: AgentConversation, content: str
) -> MessageRead:
    db.add(AgentMessage(conversation_id=conversation.id, role="user", content=content))
    await db.flush()

    decision = _llm.route(content)

    if decision.intent in _ACTION_INTENTS:
        proposal = (
            _llm.compose_meeting_proposal(decision.args)
            if decision.intent == "create_meeting"
            else _llm.compose_email_proposal(decision.args)
        )
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
        result = actions.execute_create_meeting(action.params)
        text = _llm.compose_meeting_result(result)
    else:
        result = actions.execute_send_email(action.params)
        text = _llm.compose_email_result(result)
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
