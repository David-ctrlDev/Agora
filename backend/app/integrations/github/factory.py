from app.core.config import settings
from app.integrations.github.base import GitHubProvider
from app.integrations.github.mock import MockGitHubProvider


def get_github_provider() -> GitHubProvider:
    """Selecciona el proveedor de GitHub. En desarrollo siempre es el mock.

    Para producción (`github_provider == "real"`) se devolvería RealGitHubProvider.
    """
    if settings.github_provider == "real":  # pragma: no cover
        from app.integrations.github.real import RealGitHubProvider

        return RealGitHubProvider()
    return MockGitHubProvider()
