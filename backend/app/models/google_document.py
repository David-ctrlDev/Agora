from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class GoogleDocument(Base):
    """Archivo de Drive o evento de Calendar vinculado a un proyecto (cacheado)."""

    __tablename__ = "google_documents"
    __table_args__ = (
        UniqueConstraint("project_id", "source", "external_id", name="uq_google_doc"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    source: Mapped[str] = mapped_column(String(20), nullable=False)  # drive | calendar
    external_id: Mapped[str] = mapped_column(String(255), nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    kind: Mapped[str | None] = mapped_column(String(80), nullable=True)
    web_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    occurred_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
