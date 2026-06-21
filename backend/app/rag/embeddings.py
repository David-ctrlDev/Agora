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


class GeminiEmbedding:
    """Embeddings reales de Gemini, con salida a 768 dims para encajar con el esquema."""

    dim = EMBEDDING_DIM

    def embed(self, text: str) -> list[float]:
        from google.genai import types

        from app.agent.gemini_client import get_gemini_client

        client = get_gemini_client()
        result = client.models.embed_content(
            model=settings.gemini_embedding_model,
            contents=text or " ",
            config=types.EmbedContentConfig(output_dimensionality=EMBEDDING_DIM),
        )
        return list(result.embeddings[0].values)


def get_embedding_provider() -> EmbeddingProvider:
    if settings.gemini_provider == "real":
        return GeminiEmbedding()
    return LocalHashingEmbedding()
