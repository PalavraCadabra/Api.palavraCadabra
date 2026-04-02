import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.models.board import BoardType
from app.models.board_cell import CellAction


# --- BoardCell schemas ---


class BoardCellCreate(BaseModel):
    position_row: int = Field(ge=0, le=19)
    position_col: int = Field(ge=0, le=19)
    symbol_id: uuid.UUID | None = None
    label_override: str | None = Field(default=None, max_length=255)
    action: CellAction = CellAction.speak
    action_target: str | None = Field(default=None, max_length=512)
    background_color: str = Field(default="#FFFFFF", max_length=9, pattern=r"^#[0-9A-Fa-f]{6,8}$")
    is_hidden: bool = False


class BoardCellUpdate(BaseModel):
    symbol_id: uuid.UUID | None = None
    label_override: str | None = Field(default=None, max_length=255)
    action: CellAction | None = None
    action_target: str | None = Field(default=None, max_length=512)
    background_color: str | None = Field(
        default=None, max_length=9, pattern=r"^#[0-9A-Fa-f]{6,8}$"
    )
    is_hidden: bool | None = None


class BoardCellRead(BaseModel):
    id: uuid.UUID
    board_id: uuid.UUID
    position_row: int
    position_col: int
    symbol_id: uuid.UUID | None
    label_override: str | None
    action: CellAction
    action_target: str | None
    background_color: str
    is_hidden: bool

    model_config = {"from_attributes": True}


# --- Board schemas ---


class BoardCreate(BaseModel):
    profile_id: uuid.UUID | None = None
    name: str = Field(min_length=1, max_length=255)
    board_type: BoardType = BoardType.core
    grid_rows: int = Field(default=4, ge=1, le=20)
    grid_cols: int = Field(default=5, ge=1, le=20)
    is_template: bool = False
    parent_board_id: uuid.UUID | None = None
    cells: list[BoardCellCreate] = Field(default=[], max_length=400)


class BoardUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    board_type: BoardType | None = None
    grid_rows: int | None = Field(default=None, ge=1, le=20)
    grid_cols: int | None = Field(default=None, ge=1, le=20)
    is_template: bool | None = None


class BoardRead(BaseModel):
    id: uuid.UUID
    profile_id: uuid.UUID | None
    name: str
    board_type: BoardType
    grid_rows: int
    grid_cols: int
    is_template: bool
    parent_board_id: uuid.UUID | None
    cells: list[BoardCellRead] = []
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
