from fastapi import FastAPI

from app.core.config import settings
from app.routers import areas

app = FastAPI(title=settings.app_name)

app.include_router(areas.router)


@app.get("/api/health", tags=["health"])
async def health() -> dict[str, str]:
    """Liveness check. Útil para verificar que el stack arranca de extremo a extremo."""
    return {"status": "ok", "app": settings.app_name, "env": settings.env}
