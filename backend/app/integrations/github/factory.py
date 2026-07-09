from app.core.config import settings
from app.integrations.github.base import GitHubProvider
from app.integrations.github.mock import MockGitHubProvider
from app.integrations.github.none import NullGitHubProvider


def get_github_provider() -> GitHubProvider:
    """Selecciona el proveedor de GitHub según GITHUB_PROVIDER.

    - "mock" (default): actividad simulada, para desarrollo/demos.
    - "none": GitHub apagado — sin repos ni actividad (producción sin GitHub).
    - "real": GitHub App real (requiere credenciales).
    """
    if settings.github_provider == "real":  # pragma: no cover
        from app.integrations.github.real import RealGitHubProvider

        return RealGitHubProvider()
    if settings.github_provider == "none":
        return NullGitHubProvider()
    return MockGitHubProvider()
