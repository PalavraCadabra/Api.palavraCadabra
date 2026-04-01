import enum
import uuid

from sqlalchemy import Enum, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class CommunicationLevel(str, enum.Enum):
    pre_symbolic = "pre_symbolic"
    symbolic = "symbolic"
    emerging_language = "emerging_language"
    contextual_language = "contextual_language"


class MotorCapability(str, enum.Enum):
    full_touch = "full_touch"
    limited_touch = "limited_touch"
    switch_scanning = "switch_scanning"
    eye_gaze = "eye_gaze"


class VisualCapability(str, enum.Enum):
    standard = "standard"
    low_vision = "low_vision"
    high_contrast_needed = "high_contrast_needed"


class AACProfile(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "aac_profiles"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    communication_level: Mapped[CommunicationLevel] = mapped_column(
        Enum(CommunicationLevel, name="communication_level"),
        default=CommunicationLevel.symbolic,
        nullable=False,
    )
    motor_capability: Mapped[MotorCapability] = mapped_column(
        Enum(MotorCapability, name="motor_capability"),
        default=MotorCapability.full_touch,
        nullable=False,
    )
    visual_capability: Mapped[VisualCapability] = mapped_column(
        Enum(VisualCapability, name="visual_capability"),
        default=VisualCapability.standard,
        nullable=False,
    )
    preferred_voice: Mapped[str] = mapped_column(String(50), default="Camila", nullable=False)
    grid_size_preference: Mapped[str] = mapped_column(String(10), default="4x5", nullable=False)

    # Relationships
    owner: Mapped["User"] = relationship("User", back_populates="profiles")  # noqa: F821
    boards: Mapped[list["Board"]] = relationship(  # noqa: F821
        "Board", back_populates="profile", lazy="selectin"
    )
    usage_logs: Mapped[list["UsageLog"]] = relationship(  # noqa: F821
        "UsageLog", back_populates="profile", lazy="noload"
    )
    care_relationships: Mapped[list["CareRelationship"]] = relationship(  # noqa: F821
        "CareRelationship", back_populates="profile", lazy="selectin"
    )
    literacy_milestones: Mapped[list["LiteracyMilestone"]] = relationship(  # noqa: F821
        "LiteracyMilestone", back_populates="profile", lazy="selectin"
    )
