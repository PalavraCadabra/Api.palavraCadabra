import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, UUIDPrimaryKeyMixin


class LiteracyStage(str, enum.Enum):
    pre_literacy = "pre_literacy"
    emerging = "emerging"
    developing = "developing"
    conventional = "conventional"


class LiteracyMilestone(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "literacy_milestones"

    profile_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("aac_profiles.id", ondelete="CASCADE"), nullable=False
    )
    milestone_type: Mapped[str] = mapped_column(String(100), nullable=False)
    stage: Mapped[LiteracyStage] = mapped_column(
        Enum(LiteracyStage, name="literacy_stage"),
        nullable=False,
    )
    achieved_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    recorded_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    profile: Mapped["AACProfile"] = relationship(  # noqa: F821
        "AACProfile", back_populates="literacy_milestones"
    )
    recorder: Mapped["User"] = relationship("User", lazy="selectin")  # noqa: F821
