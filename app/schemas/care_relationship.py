import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field

from app.models.care_relationship import RelationshipType


class CareRelationshipCreate(BaseModel):
    profile_id: uuid.UUID
    user_id: uuid.UUID | None = None  # Se convidando usuário existente
    email: EmailStr | None = None  # Se convidando por email
    relationship_type: RelationshipType


class CareRelationshipRead(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    profile_id: uuid.UUID
    relationship_type: RelationshipType
    permissions: dict | None = None
    created_at: datetime
    # Dados aninhados do usuário e perfil
    user_name: str | None = None
    user_email: str | None = None
    profile_name: str | None = None

    model_config = {"from_attributes": True}


class InviteRequest(BaseModel):
    profile_id: uuid.UUID
    email: EmailStr
    relationship_type: RelationshipType
    message: str | None = Field(default=None, max_length=500)


class InviteResponse(BaseModel):
    id: uuid.UUID
    profile_id: uuid.UUID
    email: str
    relationship_type: RelationshipType
    status: str = "pending"
    message: str | None = None
