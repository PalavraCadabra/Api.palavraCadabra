import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.models.aac_profile import CommunicationLevel, MotorCapability, VisualCapability


class AACProfileCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    communication_level: CommunicationLevel = CommunicationLevel.symbolic
    motor_capability: MotorCapability = MotorCapability.full_touch
    visual_capability: VisualCapability = VisualCapability.standard
    preferred_voice: str = Field(default="Camila", max_length=50)
    grid_size_preference: str = Field(
        default="4x5", max_length=10, pattern=r"^\d{1,2}x\d{1,2}$"
    )


class AACProfileUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    communication_level: CommunicationLevel | None = None
    motor_capability: MotorCapability | None = None
    visual_capability: VisualCapability | None = None
    preferred_voice: str | None = Field(default=None, max_length=50)
    grid_size_preference: str | None = Field(
        default=None, max_length=10, pattern=r"^\d{1,2}x\d{1,2}$"
    )


class AACProfileRead(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    name: str
    communication_level: CommunicationLevel
    motor_capability: MotorCapability
    visual_capability: VisualCapability
    preferred_voice: str
    grid_size_preference: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
