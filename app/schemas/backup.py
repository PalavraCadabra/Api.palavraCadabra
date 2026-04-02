from datetime import datetime

from pydantic import BaseModel

from app.schemas.sync import SyncBoardData, SyncCellData, SyncProfileData


class BackupUserData(BaseModel):
    email: str
    full_name: str
    role: str


class BackupExportResponse(BaseModel):
    version: str = "1.0"
    exported_at: str
    user: BackupUserData
    profiles: list[SyncProfileData]
    boards: list[SyncBoardData]
    cells: list[SyncCellData]


class BackupImportRequest(BaseModel):
    version: str
    profiles: list[SyncProfileData] = []
    boards: list[SyncBoardData] = []
    cells: list[SyncCellData] = []


class BackupImportResponse(BaseModel):
    imported: dict[str, int]
    server_time: datetime
