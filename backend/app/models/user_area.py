from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class UserArea(Base):
    """Pertenencia de un usuario a un área, con su rol dentro de ella (lead/member)."""

    __tablename__ = "user_areas"

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    area_id: Mapped[int] = mapped_column(
        ForeignKey("areas.id", ondelete="CASCADE"), primary_key=True
    )
    area_role: Mapped[str] = mapped_column(
        String(20), nullable=False, default="member", server_default="member"
    )
