"""Proveedor 'apagado': GitHub deshabilitado (sin repos automáticos ni actividad).

Para entornos donde no se usa GitHub (GITHUB_PROVIDER=none): no genera datos
simulados ni toca la red. La integración real queda disponible cambiando a 'real'.
"""
from app.integrations.github.base import GitHubActivityEvent


class NullGitHubProvider:
    def fetch_activity(self, full_name: str) -> list[GitHubActivityEvent]:  # noqa: ARG002
        return []
