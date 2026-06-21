import base64
import hashlib

from cryptography.fernet import Fernet

from app.core.config import settings


def _fernet() -> Fernet:
    key = settings.token_encryption_key
    if not key:
        # Desarrollo: deriva una clave Fernet de SECRET_KEY. NO usar en producción
        # (en producción se define TOKEN_ENCRYPTION_KEY con una clave Fernet propia).
        digest = hashlib.sha256(settings.secret_key.encode()).digest()
        key = base64.urlsafe_b64encode(digest).decode()
    return Fernet(key.encode())


def encrypt(value: str) -> str:
    return _fernet().encrypt(value.encode()).decode()


def decrypt(token: str) -> str:
    return _fernet().decrypt(token.encode()).decode()
