import enum
import uuid

from sqlalchemy import Boolean, Enum, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, SyncMixin, TimestampMixin, UUIDPrimaryKeyMixin


class CellAction(str, enum.Enum):
    speak = "speak"
    navigate = "navigate"
    modifier = "modifier"


class BoardCell(UUIDPrimaryKeyMixin, TimestampMixin, SyncMixin, Base):
    __tablename__ = "board_cells"

    board_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("boards.id", ondelete="CASCADE"), nullable=False
    )
    position_row: Mapped[int] = mapped_column(Integer, nullable=False)
    position_col: Mapped[int] = mapped_column(Integer, nullable=False)
    symbol_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("symbols.id", ondelete="SET NULL"), nullable=True
    )
    label_override: Mapped[str | None] = mapped_column(String(255), nullable=True)
    action: Mapped[CellAction] = mapped_column(
        Enum(CellAction, name="cell_action"),
        default=CellAction.speak,
        nullable=False,
    )
    action_target: Mapped[str | None] = mapped_column(String(255), nullable=True)
    background_color: Mapped[str] = mapped_column(String(7), default="#FFFFFF", nullable=False)
    is_hidden: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Relationships
    board: Mapped["Board"] = relationship("Board", back_populates="cells")  # noqa: F821
    symbol: Mapped["Symbol | None"] = relationship("Symbol", lazy="selectin")  # noqa: F821
