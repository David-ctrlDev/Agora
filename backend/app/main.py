from fastapi import FastAPI

from app.core.config import settings
from app.routers import areas, auth, comments, github, projects, tasks, users

app = FastAPI(title=settings.app_name)

app.include_router(auth.router)
app.include_router(areas.router)
app.include_router(projects.router)
app.include_router(tasks.router)
app.include_router(comments.router)
app.include_router(github.router)
app.include_router(users.router)


@app.get("/api/health", tags=["health"])
async def health() -> dict[str, str]:
    """Liveness check. Útil para verificar que el stack arranca de extremo a extremo."""
    return {"status": "ok", "app": settings.app_name, "env": settings.env}
