import enum
import uuid

from sqlalchemy import Enum, ForeignKey, Integer, String, Text, Boolean
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.literacy_program import LiteracyStage


class ActivityType(str, enum.Enum):
    # Stage 1 — Foundations
    symbol_matching = "symbol_matching"
    letter_recognition = "letter_recognition"
    phonological_awareness = "phonological_awareness"
    print_awareness = "print_awareness"

    # Stage 2 — Emerging
    letter_sound = "letter_sound"
    sight_words = "sight_words"
    shared_reading = "shared_reading"
    emergent_writing = "emergent_writing"

    # Stage 3 — Developing
    word_decoding = "word_decoding"
    sentence_building = "sentence_building"
    reading_comprehension = "reading_comprehension"
    symbol_to_text = "symbol_to_text"

    # Stage 4 — Conventional
    independent_reading = "independent_reading"
    functional_writing = "functional_writing"
    text_communication = "text_communication"


class LiteracyActivity(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "literacy_activities"

    activity_type: Mapped[ActivityType] = mapped_column(
        Enum(ActivityType, name="activity_type"),
        nullable=False,
    )
    stage: Mapped[LiteracyStage] = mapped_column(
        Enum(LiteracyStage, name="literacy_program_stage", create_type=False),
        nullable=False,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    difficulty_level: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    # Activity content stored as JSONB
    content: Mapped[dict] = mapped_column(JSONB, nullable=False)

    # Optional: link to specific symbols
    symbol_ids: Mapped[list[uuid.UUID] | None] = mapped_column(
        ARRAY(UUID(as_uuid=True)), nullable=True
    )

    # Metadata
    estimated_duration_minutes: Mapped[int] = mapped_column(
        Integer, nullable=False, default=5
    )
    is_template: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Relationships
    creator: Mapped["User"] = relationship("User", lazy="selectin")  # noqa: F821
