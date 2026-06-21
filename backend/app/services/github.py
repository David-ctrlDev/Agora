from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.integrations.github.base import GitHubActivityEvent
from app.integrations.github.factory import get_github_provider
from app.models.github_event import GitHubEvent
from app.models.github_repo import GitHubRepo


class RepoAlreadyLinked(Exception):
    """El repositorio ya está vinculado a este proyecto."""


async def list_repos(db: AsyncSession, project_id: int) -> list[GitHubRepo]:
    result = await db.execute(
        select(GitHubRepo).where(GitHubRepo.project_id == project_id).order_by(GitHubRepo.full_name)
    )
    return list(result.scalars().all())


async def get_repo(db: AsyncSession, repo_id: int) -> GitHubRepo | None:
    return await db.get(GitHubRepo, repo_id)


async def link_repo(db: AsyncSession, project_id: int, full_name: str) -> GitHubRepo:
    repo = GitHubRepo(
        project_id=project_id, full_name=full_name, html_url=f"https://github.com/{full_name}"
    )
    db.add(repo)
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise RepoAlreadyLinked() from exc
    await db.refresh(repo)
    await sync_repo(db, repo)
    return repo


async def unlink_repo(db: AsyncSession, repo: GitHubRepo) -> None:
    await db.delete(repo)
    await db.commit()


async def _store_event(db: AsyncSession, repo_id: int, event: GitHubActivityEvent) -> bool:
    existing = await db.execute(
        select(GitHubEvent.id).where(
            GitHubEvent.repo_id == repo_id, GitHubEvent.external_id == event.external_id
        )
    )
    if existing.scalar_one_or_none() is not None:
        return False
    db.add(
        GitHubEvent(
            repo_id=repo_id,
            event_type=event.event_type,
            external_id=event.external_id,
            title=event.title[:500],
            author=event.author,
            html_url=event.html_url,
            occurred_at=event.occurred_at,
        )
    )
    return True


async def sync_repo(db: AsyncSession, repo: GitHubRepo) -> int:
    provider = get_github_provider()
    new = 0
    for event in provider.fetch_activity(repo.full_name):
        if await _store_event(db, repo.id, event):
            new += 1
    await db.commit()
    return new


async def list_project_activity(
    db: AsyncSession, project_id: int, limit: int = 50
) -> list[GitHubEvent]:
    repo_ids = select(GitHubRepo.id).where(GitHubRepo.project_id == project_id)
    result = await db.execute(
        select(GitHubEvent)
        .where(GitHubEvent.repo_id.in_(repo_ids))
        .order_by(GitHubEvent.occurred_at.desc())
        .limit(limit)
    )
    return list(result.scalars().all())


async def store_webhook_event(
    db: AsyncSession, full_name: str, event: GitHubActivityEvent
) -> int:
    repos = (
        await db.execute(select(GitHubRepo).where(GitHubRepo.full_name == full_name))
    ).scalars().all()
    stored = 0
    for repo in repos:
        if await _store_event(db, repo.id, event):
            stored += 1
    await db.commit()
    return stored
