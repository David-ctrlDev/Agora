from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class ProjectProgressSnapshot(Base):
    """Sello del avance de un proyecto en un instante.

    Se captura cada vez que cambia `progress`. Permite reconstruir el avance que
    tenía un proyecto al cierre de un trimestre pasado (seguimiento trimestral).
    """

    __tablename__ = "project_progress_snapshots"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    progress: Mapped[int] = mapped_column(Integer, nullable=False)
    captured_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), index=True
    )
