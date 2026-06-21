from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.deps import get_current_user
from app.models.agent_action import AgentAction
from app.models.agent_conversation import AgentConversation
from app.models.user import User
from app.schemas.agent import ConversationCreate, ConversationRead, MessageCreate, MessageRead
from app.services import agent as svc

router = APIRouter(prefix="/api/agent", tags=["agent"])


async def _conversation(conversation_id: int, user: User, db: AsyncSession) -> AgentConversation:
    conversation = await svc.get_conversation(db, conversation_id)
    if conversation is None or conversation.user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Conversación no encontrada"
        )
    return conversation


async def _own_action(action_id: int, user: User, db: AsyncSession) -> AgentAction:
    action = await svc.get_action(db, action_id)
    if action is None or action.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Acción no encontrada")
    return action


@router.get("/conversations", response_model=list[ConversationRead])
async def list_conversations(
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> list[AgentConversation]:
    return await svc.list_conversations(db, user)


@router.post("/conversations", response_model=ConversationRead, status_code=status.HTTP_201_CREATED)
async def create_conversation(
    payload: ConversationCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AgentConversation:
    return await svc.create_conversation(db, user, payload.title)


@router.delete("/conversations/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_conversation(
    conversation_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    conversation = await _conversation(conversation_id, user, db)
    await svc.delete_conversation(db, conversation)


@router.get("/conversations/{conversation_id}/messages", response_model=list[MessageRead])
async def list_messages(
    conversation_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[MessageRead]:
    await _conversation(conversation_id, user, db)
    return await svc.list_messages(db, conversation_id)


@router.post("/conversations/{conversation_id}/messages", response_model=MessageRead)
async def send_message(
    conversation_id: int,
    payload: MessageCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MessageRead:
    conversation = await _conversation(conversation_id, user, db)
    return await svc.run_message(db, user, conversation, payload.content)


@router.post("/actions/{action_id}/confirm", response_model=MessageRead)
async def confirm_action(
    action_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> MessageRead:
    action = await _own_action(action_id, user, db)
    try:
        return await svc.confirm_action(db, action)
    except svc.ActionNotPending as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="La acción ya no está pendiente"
        ) from exc


@router.post("/actions/{action_id}/cancel", response_model=MessageRead)
async def cancel_action(
    action_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> MessageRead:
    action = await _own_action(action_id, user, db)
    return await svc.cancel_action(db, action)
