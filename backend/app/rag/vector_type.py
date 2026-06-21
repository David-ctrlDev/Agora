from typing import Any

from pgvector.sqlalchemy import Vector as _PGVector


class Vector(_PGVector):
    """Tipo `vector` que delega la (de)serialización en el códec de asyncpg.

    pgvector.sqlalchemy convierte la lista a texto en su bind_processor, lo que
    choca con `register_vector` (que espera una lista). Aquí usamos procesadores
    identidad para que la lista de floats llegue intacta al códec de asyncpg.
    """

    cache_ok = True

    def bind_processor(self, dialect: Any):  # type: ignore[override]
        return None

    def result_processor(self, dialect: Any, coltype: Any):  # type: ignore[override]
        return None
