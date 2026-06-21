from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.task_comment import TaskComment
from app.models.user import User
from app.schemas.comment import CommentRead


async def list_comments(db: AsyncSession, task_id: int) -> list[CommentRead]:
    rows = (
        await db.execute(
            select(TaskComment, User.name)
            .outerjoin(User, User.id == TaskComment.author_id)
            .where(TaskComment.task_id == task_id)
            .order_by(TaskComment.created_at)
        )
    ).all()
    return [
        CommentRead(
            id=comment.id,
            body=comment.body,
            author_id=comment.author_id,
            author_name=author_name,
            created_at=comment.created_at,
        )
        for (comment, author_name) in rows
    ]


async def add_comment(db: AsyncSession, task_id: int, author_id: int, body: str) -> CommentRead:
    comment = TaskComment(task_id=task_id, author_id=author_id, body=body.strip())
    db.add(comment)
    await db.commit()
    await db.refresh(comment)
    author = await db.get(User, author_id)
    return CommentRead(
        id=comment.id,
        body=comment.body,
        author_id=comment.author_id,
        author_name=author.name if author else None,
        created_at=comment.created_at,
    )
