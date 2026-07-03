from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class CatalogTerm(Base):
    """Maestra de valores para campos de proyecto (proceso, categoría, tipo).

    `kind` define de qué maestra es. `norm` (nombre en mayúsculas y sin espacios
    de borde) da unicidad por maestra para que no se repitan variantes de mayúsculas.
    """

    __tablename__ = "catalog_terms"
    __table_args__ = (UniqueConstraint("kind", "norm", name="uq_catalog_kind_norm"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    kind: Mapped[str] = mapped_column(String(20), nullable=False, index=True)  # process|category|project_type
    name: Mapped[str] = mapped_column(String(120), nullable=False)  # forma a mostrar
    norm: Mapped[str] = mapped_column(String(120), nullable=False)  # clave normalizada (unicidad)
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
