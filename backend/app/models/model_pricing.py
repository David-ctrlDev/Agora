from datetime import datetime

from sqlalchemy import DateTime, Float, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class ModelPricing(Base):
    """Tarifa por modelo para estimar el costo del agente (USD por 1M de tokens).

    La gestiona el super admin desde el módulo de Costos. Los cambios aplican a
    consumos futuros; lo ya registrado conserva el costo calculado en su momento.
    """

    __tablename__ = "model_pricing"

    id: Mapped[int] = mapped_column(primary_key=True)
    model: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)
    input_per_1m: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    output_per_1m: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )
