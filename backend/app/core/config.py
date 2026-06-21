from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuración de la app, leída de variables de entorno (.env)."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "Agora"
    env: str = "development"

    database_url: str = "postgresql+asyncpg://agora:agora@db:5432/agora"

    # Sesión / JWT
    secret_key: str = "change-me-please-32-bytes-hex"
    jwt_algorithm: str = "HS256"
    session_cookie_name: str = "agora_session"
    session_cookie_secure: bool = False
    session_cookie_samesite: str = "lax"
    session_max_age_seconds: int = 604800

    # Login (Google OAuth, Fase 3)
    google_allowed_hd: str = "invesa.com"
    bootstrap_admin_emails: str = ""

    # Integraciones externas — proveedor "mock" (sin red) o "real" (con credenciales).
    github_provider: str = "mock"
    github_webhook_secret: str = ""
    google_provider: str = "mock"
    gemini_provider: str = "mock"
    gemini_api_key: str = ""
    gemini_chat_model: str = "gemini-flash-latest"
    gemini_embedding_model: str = "gemini-embedding-001"

    # Cifrado en reposo de tokens OAuth (Fernet). Vacío => se usa una clave derivada de SECRET_KEY (solo dev).
    token_encryption_key: str = ""

    # Notificaciones (Fase 6) — outbox de desarrollo (sin envío real).
    notifications_provider: str = "outbox"
    notifications_run_token: str = ""

    @property
    def is_development(self) -> bool:
        return self.env == "development"


settings = Settings()
