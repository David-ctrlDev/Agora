import hashlib
import math
import re
from typing import Protocol

from app.core.config import settings

EMBEDDING_DIM = 768

_TOKEN_RE = re.compile(r"[a-záéíóúñü0-9]+", re.IGNORECASE)


def _tokens(text: str) -> list[str]:
    return _TOKEN_RE.findall(text.lower())


class EmbeddingProvider(Protocol):
    dim: int

    def embed(self, text: str) -> list[float]: ...


class LocalHashingEmbedding:
    """Embedding determinista por 'hashing trick' con signo. Sin red.

    Comparte dimensión (768) con text-embedding-004 para poder cambiar a Gemini
    sin tocar el esquema. Texto con tokens compartidos -> vectores cercanos.
    """

    dim = EMBEDDING_DIM

    def embed(self, text: str) -> list[float]:
        vector = [0.0] * EMBEDDING_DIM
        for token in _tokens(text):
            digest = int(hashlib.md5(token.encode()).hexdigest(), 16)
            index = digest % EMBEDDING_DIM
            sign = 1.0 if (digest >> 8) % 2 == 0 else -1.0
            vector[index] += sign
        norm = math.sqrt(sum(v * v for v in vector))
        if norm > 0:
            vector = [v / norm for v in vector]
        return vector


def get_embedding_provider() -> EmbeddingProvider:
    if settings.gemini_provider == "real":  # pragma: no cover
        # Aquí se devolvería un proveedor que llama a text-embedding-004 de Gemini.
        raise NotImplementedError("El proveedor real de embeddings requiere GEMINI_API_KEY.")
    return LocalHashingEmbedding()
