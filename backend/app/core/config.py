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

    # Login (se usará con Google OAuth en la Fase 3)
    google_allowed_hd: str = "invesa.com"
    bootstrap_admin_emails: str = ""

    @property
    def is_development(self) -> bool:
        return self.env == "development"


settings = Settings()
