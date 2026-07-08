from fastapi import FastAPI

from app.core.config import settings
from app.routers import (
    admin,
    agent,
    analytics,
    area_admin,
    area_requests,
    areas,
    audit,
    auth,
    catalog,
    comments,
    economics,
    github,
    google,
    knowledge,
    notifications,
    projects,
    sprints,
    tasks,
    users,
)

app = FastAPI(title=settings.app_name)

app.include_router(auth.router)
app.include_router(areas.router)
app.include_router(area_requests.router)
app.include_router(projects.router)
app.include_router(tasks.router)
app.include_router(comments.router)
app.include_router(github.router)
app.include_router(google.router)
app.include_router(knowledge.router)
app.include_router(agent.router)
app.include_router(notifications.router)
app.include_router(analytics.router)
app.include_router(sprints.router)
app.include_router(economics.router)
app.include_router(audit.router)
app.include_router(users.router)
app.include_router(admin.router)
app.include_router(area_admin.router)
app.include_router(catalog.router)


@app.get("/api/health", tags=["health"])
async def health() -> dict[str, str]:
    """Liveness check. Útil para verificar que el stack arranca de extremo a extremo."""
    return {"status": "ok", "app": settings.app_name, "env": settings.env}
