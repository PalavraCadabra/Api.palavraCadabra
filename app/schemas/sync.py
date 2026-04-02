import uuid
from datetime import datetime

from pydantic import BaseModel

from app.models.aac_profile import CommunicationLevel, MotorCapability, VisualCapability
from app.models.board import BoardType
from app.models.board_cell import CellAction


class SyncProfileData(BaseModel):
    id: uuid.UUID
    name: str
    communication_level: CommunicationLevel
    motor_capability: MotorCapability
    visual_capability: VisualCapability
    preferred_voice: str
    grid_size_preference: str | None = None
    updated_at: datetime
    version: int
    device_id: str | None = None
    is_deleted: bool = False

    model_config = {"from_attributes": True}


class SyncBoardData(BaseModel):
    id: uuid.UUID
    profile_id: uuid.UUID | None = None
    name: str
    board_type: BoardType
    grid_rows: int
    grid_cols: int
    is_template: bool = False
    parent_board_id: uuid.UUID | None = None
    updated_at: datetime
    version: int
    device_id: str | None = None
    is_deleted: bool = False

    model_config = {"from_attributes": True}


class SyncCellData(BaseModel):
    id: uuid.UUID
    board_id: uuid.UUID
    position_row: int
    position_col: int
    symbol_id: uuid.UUID | None = None
    label_override: str | None = None
    action: CellAction
    action_target: str | None = None
    background_color: str = "#FFFFFF"
    is_hidden: bool = False
    updated_at: datetime
    version: int
    device_id: str | None = None
    is_deleted: bool = False

    model_config = {"from_attributes": True}


class SyncPushRequest(BaseModel):
    profiles: list[SyncProfileData] = []
    boards: list[SyncBoardData] = []
    cells: list[SyncCellData] = []
    device_id: str


class SyncPullRequest(BaseModel):
    since: datetime | None = None
    device_id: str


class SyncPullResponse(BaseModel):
    profiles: list[SyncProfileData]
    boards: list[SyncBoardData]
    cells: list[SyncCellData]
    server_time: datetime
