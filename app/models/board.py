import enum
import uuid

from sqlalchemy import Boolean, Enum, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, SyncMixin, TimestampMixin, UUIDPrimaryKeyMixin


class BoardType(str, enum.Enum):
    core = "core"
    category = "category"
    personal = "personal"
    activity = "activity"


class Board(UUIDPrimaryKeyMixin, TimestampMixin, SyncMixin, Base):
    __tablename__ = "boards"

    profile_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("aac_profiles.id", ondelete="CASCADE"), nullable=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    board_type: Mapped[BoardType] = mapped_column(
        Enum(BoardType, name="board_type"),
        default=BoardType.core,
        nullable=False,
    )
    grid_rows: Mapped[int] = mapped_column(Integer, default=4, nullable=False)
    grid_cols: Mapped[int] = mapped_column(Integer, default=5, nullable=False)
    is_template: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    parent_board_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("boards.id", ondelete="SET NULL"), nullable=True
    )

    # Relationships
    profile: Mapped["AACProfile | None"] = relationship(  # noqa: F821
        "AACProfile", back_populates="boards"
    )
    cells: Mapped[list["BoardCell"]] = relationship(  # noqa: F821
        "BoardCell", back_populates="board", lazy="selectin", cascade="all, delete-orphan"
    )
    parent_board: Mapped["Board | None"] = relationship(
        "Board", remote_side="Board.id", lazy="noload"
    )
