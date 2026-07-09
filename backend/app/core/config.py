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
    session_max_age_seconds: int = 86400  # 1 día (máximo absoluto de la sesión)

    # Login (Google OAuth, Fase 3)
    google_allowed_hd: str = "invesa.com"
    # Auto-provisión: cualquier cuenta del dominio permitido entra (se crea como member
    # en el primer login). Si es False, solo entran usuarios ya creados (lista blanca).
    google_auto_provision: bool = True
    bootstrap_admin_emails: str = ""
    # Super administradores globales (ven y gestionan todo). Fijados por configuración,
    # no por un rol en BD, para que nadie se vuelva super admin por error. Coma-separado.
    superadmin_emails: str = "wserna@invesa.com"

    # Integraciones externas — proveedor "mock" (sin red) o "real" (con credenciales).
    github_provider: str = "mock"
    github_webhook_secret: str = ""
    # Al crear un proyecto se crea/vincula un repositorio de forma transparente (sin UI).
    github_autocreate_repo: bool = True
    google_provider: str = "mock"
    google_client_id: str = ""
    google_client_secret: str = ""
    google_oauth_redirect_uri: str = "http://localhost:5173/api/auth/google/callback"
    google_oauth_scopes: str = (
        "openid email profile "
        "https://www.googleapis.com/auth/directory.readonly "
        "https://www.googleapis.com/auth/calendar.events "
        "https://www.googleapis.com/auth/calendar.freebusy "
        "https://www.googleapis.com/auth/drive.readonly "
        # Escritura sobre archivos/carpetas creados por la app (documentación por proyecto en Drive).
        "https://www.googleapis.com/auth/drive.file "
        "https://www.googleapis.com/auth/gmail.send"
    )
    # Zona horaria local de la empresa (Colombia, sin DST). Las horas sin zona
    # (p. ej. de un formulario) y los valores por defecto se interpretan aquí.
    app_utc_offset_hours: int = -5
    # Documentación en Drive como "filesystem" del proyecto (carpeta + sync/re-vectorizado).
    # Activo, pero solo opera con google_provider=real + el owner con Drive conectado (escritura).
    drive_docs_enabled: bool = True
    # Cuenta operadora (Workspace) cuyo token usa el job de sync sin usuario presente.
    drive_docs_operator_email: str = ""
    # Carpeta raíz (o Unidad compartida) donde se crean las carpetas de proyecto; vacío => raíz del operador.
    drive_docs_root_id: str = ""
    gemini_provider: str = "mock"
    gemini_api_key: str = ""
    gemini_chat_model: str = "gemini-flash-latest"
    gemini_embedding_model: str = "gemini-embedding-001"
    # Tarifa para estimar el costo del agente (USD por 1M de tokens). Entrada y salida
    # por separado (más certero). Ajusta según el modelo/precios vigentes de Google.
    gemini_price_input_per_1m: float = 0.10
    gemini_price_output_per_1m: float = 0.40

    # Cifrado en reposo de tokens OAuth (Fernet). Vacío => se usa una clave derivada de SECRET_KEY (solo dev).
    token_encryption_key: str = ""

    # Notificaciones (Fase 6) — outbox de desarrollo (sin envío real).
    notifications_provider: str = "outbox"
    notifications_run_token: str = ""

    @property
    def is_development(self) -> bool:
        return self.env == "development"

    @property
    def superadmin_email_set(self) -> set[str]:
        return {e.strip().lower() for e in self.superadmin_emails.split(",") if e.strip()}


settings = Settings()
