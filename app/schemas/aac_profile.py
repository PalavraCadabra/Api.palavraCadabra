import uuid
from datetime import datetime

from pydantic import BaseModel

from app.models.aac_profile import CommunicationLevel, MotorCapability, VisualCapability


class AACProfileCreate(BaseModel):
    name: str
    communication_level: CommunicationLevel = CommunicationLevel.symbolic
    motor_capability: MotorCapability = MotorCapability.full_touch
    visual_capability: VisualCapability = VisualCapability.standard
    preferred_voice: str = "Camila"
    grid_size_preference: str = "4x5"


class AACProfileUpdate(BaseModel):
    name: str | None = None
    communication_level: CommunicationLevel | None = None
    motor_capability: MotorCapability | None = None
    visual_capability: VisualCapability | None = None
    preferred_voice: str | None = None
    grid_size_preference: str | None = None


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
