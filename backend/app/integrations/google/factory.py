from app.core.config import settings
from app.integrations.google.base import GoogleProvider
from app.integrations.google.mock import MockGoogleProvider


def get_google_provider() -> GoogleProvider:
    if settings.google_provider == "real":  # pragma: no cover
        from app.integrations.google.real import RealGoogleProvider

        return RealGoogleProvider()
    return MockGoogleProvider()
