import enum
import uuid

from sqlalchemy import Enum, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class RelationshipType(str, enum.Enum):
    caregiver = "caregiver"
    therapist = "therapist"
    teacher = "teacher"
    admin = "admin"


class CareRelationship(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "care_relationships"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    profile_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("aac_profiles.id", ondelete="CASCADE"), nullable=False
    )
    relationship_type: Mapped[RelationshipType] = mapped_column(
        Enum(RelationshipType, name="relationship_type"),
        nullable=False,
    )
    permissions: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="care_relationships")  # noqa: F821
    profile: Mapped["AACProfile"] = relationship(  # noqa: F821
        "AACProfile", back_populates="care_relationships"
    )
