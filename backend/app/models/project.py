from datetime import date, datetime

from sqlalchemy import Date, DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    area_id: Mapped[int] = mapped_column(
        ForeignKey("areas.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="planned", server_default="planned"
    )
    owner_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    progress: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    estimated_cost: Mapped[float | None] = mapped_column(Float, nullable=True)
    actual_cost: Mapped[float | None] = mapped_column(Float, nullable=True)
    expected_benefit: Mapped[float | None] = mapped_column(Float, nullable=True)
    actual_benefit: Mapped[float | None] = mapped_column(Float, nullable=True)
    currency: Mapped[str] = mapped_column(
        String(3), nullable=False, default="COP", server_default="COP"
    )
    # Campos del roadmap (importados del Excel de planeación de TI).
    initiative: Mapped[str | None] = mapped_column(String(120), nullable=True)  # proyecto padre
    proposed_by: Mapped[str | None] = mapped_column(String(160), nullable=True)
    project_type: Mapped[str | None] = mapped_column(String(60), nullable=True)  # tipo
    category: Mapped[str | None] = mapped_column(String(80), nullable=True)
    criticality: Mapped[str | None] = mapped_column(String(20), nullable=True)
    process: Mapped[str | None] = mapped_column(String(120), nullable=True)
    benefits: Mapped[str | None] = mapped_column(Text, nullable=True)
    change_management: Mapped[str | None] = mapped_column(String(20), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )
