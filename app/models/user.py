import enum

from sqlalchemy import Boolean, Enum, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class UserRole(str, enum.Enum):
    patient = "patient"
    caregiver = "caregiver"
    therapist = "therapist"
    admin = "admin"


class User(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(320), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(1024), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, name="user_role"),
        nullable=False,
        default=UserRole.caregiver,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relationships
    profiles: Mapped[list["AACProfile"]] = relationship(  # noqa: F821
        "AACProfile", back_populates="owner", lazy="selectin"
    )
    care_relationships: Mapped[list["CareRelationship"]] = relationship(  # noqa: F821
        "CareRelationship", back_populates="user", lazy="selectin"
    )
