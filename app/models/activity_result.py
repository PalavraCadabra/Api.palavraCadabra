import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, UUIDPrimaryKeyMixin


class ActivityResult(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "activity_results"

    program_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("literacy_programs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    activity_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("literacy_activities.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    profile_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("aac_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Performance
    score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    correct_answers: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_questions: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    time_spent_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Detailed response data
    responses: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # Therapist notes
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    recorded_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Relationships
    program: Mapped["LiteracyProgram"] = relationship("LiteracyProgram", lazy="selectin")  # noqa: F821
    activity: Mapped["LiteracyActivity"] = relationship("LiteracyActivity", lazy="selectin")  # noqa: F821
    profile: Mapped["AACProfile"] = relationship("AACProfile", lazy="selectin")  # noqa: F821
    recorder: Mapped["User"] = relationship("User", lazy="selectin")  # noqa: F821
