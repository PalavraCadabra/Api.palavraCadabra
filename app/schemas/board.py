import uuid
from datetime import datetime

from pydantic import BaseModel

from app.models.board import BoardType
from app.models.board_cell import CellAction


# --- BoardCell schemas ---


class BoardCellCreate(BaseModel):
    position_row: int
    position_col: int
    symbol_id: uuid.UUID | None = None
    label_override: str | None = None
    action: CellAction = CellAction.speak
    action_target: str | None = None
    background_color: str = "#FFFFFF"
    is_hidden: bool = False


class BoardCellUpdate(BaseModel):
    symbol_id: uuid.UUID | None = None
    label_override: str | None = None
    action: CellAction | None = None
    action_target: str | None = None
    background_color: str | None = None
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
    name: str
    board_type: BoardType = BoardType.core
    grid_rows: int = 4
    grid_cols: int = 5
    is_template: bool = False
    parent_board_id: uuid.UUID | None = None
    cells: list[BoardCellCreate] = []


class BoardUpdate(BaseModel):
    name: str | None = None
    board_type: BoardType | None = None
    grid_rows: int | None = None
    grid_cols: int | None = None
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
