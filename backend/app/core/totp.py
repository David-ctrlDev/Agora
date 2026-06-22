"""TOTP (RFC 6238) en Python puro — sin dependencias externas."""
import base64
import hashlib
import hmac
import secrets
import struct
import time
from urllib.parse import quote


def generate_secret() -> str:
    """Secreto base32 de 160 bits, compatible con apps de autenticación."""
    return base64.b32encode(secrets.token_bytes(20)).decode("ascii").rstrip("=")


def _hotp(secret: str, counter: int, digits: int = 6) -> str:
    padding = "=" * ((8 - len(secret) % 8) % 8)
    key = base64.b32decode(secret + padding, casefold=True)
    digest = hmac.new(key, struct.pack(">Q", counter), hashlib.sha1).digest()
    offset = digest[-1] & 0x0F
    code = (struct.unpack(">I", digest[offset : offset + 4])[0] & 0x7FFFFFFF) % (10**digits)
    return str(code).zfill(digits)


def verify(secret: str, code: str, *, window: int = 1, step: int = 30) -> bool:
    """Verifica un código TOTP, tolerando ±`window` pasos por desfase de reloj."""
    cleaned = (code or "").replace(" ", "").strip()
    if not secret or not cleaned.isdigit():
        return False
    counter = int(time.time() // step)
    return any(
        hmac.compare_digest(_hotp(secret, counter + offset), cleaned)
        for offset in range(-window, window + 1)
    )


def provisioning_uri(secret: str, account: str, issuer: str = "Agora") -> str:
    """URI otpauth:// para el QR de enrolamiento."""
    label = quote(f"{issuer}:{account}")
    params = f"secret={secret}&issuer={quote(issuer)}&algorithm=SHA1&digits=6&period=30"
    return f"otpauth://totp/{label}?{params}"
