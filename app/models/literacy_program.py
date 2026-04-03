import enum
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class LiteracyStage(str, enum.Enum):
    foundations = "foundations"        # Etapa 1 — Fundamentos (Pre-letramento)
    emerging = "emerging"             # Etapa 2 — Emergente
    developing = "developing"         # Etapa 3 — Desenvolvimento
    conventional = "conventional"     # Etapa 4 — Convencional


class LiteracyProgram(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "literacy_programs"

    profile_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("aac_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    assigned_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    current_stage: Mapped[LiteracyStage] = mapped_column(
        Enum(LiteracyStage, name="literacy_program_stage"),
        default=LiteracyStage.foundations,
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    profile: Mapped["AACProfile"] = relationship("AACProfile", lazy="selectin")  # noqa: F821
    assigner: Mapped["User"] = relationship("User", lazy="selectin")  # noqa: F821
