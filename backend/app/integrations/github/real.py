"""Adaptador real de GitHub (GitHub App + API). No se usa en modo mock.

Se activaría con `settings.github_provider == "real"` y credenciales de la
GitHub App. Aquí se harían las llamadas con httpx a la API de GitHub. Se deja
como esqueleto para no realizar peticiones externas en desarrollo.
"""
from app.integrations.github.base import GitHubActivityEvent


class RealGitHubProvider:
    def fetch_activity(self, full_name: str) -> list[GitHubActivityEvent]:  # pragma: no cover
        raise NotImplementedError(
            "El proveedor real de GitHub requiere credenciales y red; usa el proveedor mock."
        )
