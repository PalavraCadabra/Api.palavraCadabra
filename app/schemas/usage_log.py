import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class UsageLogCreate(BaseModel):
    profile_id: uuid.UUID
    event_type: str = Field(
        min_length=1,
        max_length=50,
        description="symbol_selected, board_navigated, message_spoken, prediction_used, session_start, session_end",
    )
    event_data: dict | None = None
    session_id: uuid.UUID | None = None
    timestamp: datetime | None = None  # Optional — server uses now() if not provided


class UsageLogRead(BaseModel):
    id: uuid.UUID
    profile_id: uuid.UUID
    timestamp: datetime
    event_type: str
    event_data: dict | None
    session_id: uuid.UUID | None

    model_config = {"from_attributes": True}
