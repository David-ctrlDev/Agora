from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class AreaJoinRequest(Base):
    """Solicitud self-service: unirse a un área existente o crear una nueva.

    kind='join'     -> area_id apunta al área a la que se quiere unir.
    kind='new_area' -> proposed_name/description; un admin la crea al aprobar.
    """

    __tablename__ = "area_join_requests"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    kind: Mapped[str] = mapped_column(String(20), nullable=False, default="join")
    area_id: Mapped[int | None] = mapped_column(
        ForeignKey("areas.id", ondelete="CASCADE"), nullable=True, index=True
    )
    proposed_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    proposed_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pending", server_default="pending", index=True
    )
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    decided_by: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
