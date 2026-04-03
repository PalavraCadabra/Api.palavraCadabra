import uuid
from datetime import datetime

from pydantic import BaseModel, Field


# --- LiteracyProgram schemas ---

class LiteracyProgramCreate(BaseModel):
    profile_id: uuid.UUID
    name: str = Field(min_length=1, max_length=255)
    current_stage: str = "foundations"
    notes: str | None = None


class LiteracyProgramRead(BaseModel):
    id: uuid.UUID
    profile_id: uuid.UUID
    assigned_by: uuid.UUID
    name: str
    current_stage: str
    is_active: bool
    started_at: datetime
    notes: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class LiteracyProgramUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    current_stage: str | None = None
    is_active: bool | None = None
    notes: str | None = None


# --- LiteracyActivity schemas ---

class LiteracyActivityCreate(BaseModel):
    activity_type: str
    stage: str
    title: str = Field(min_length=1, max_length=255)
    description: str = ""
    difficulty_level: int = Field(default=1, ge=1, le=5)
    content: dict
    symbol_ids: list[uuid.UUID] | None = None
    estimated_duration_minutes: int = Field(default=5, ge=1)


class LiteracyActivityRead(BaseModel):
    id: uuid.UUID
    activity_type: str
    stage: str
    title: str
    description: str
    difficulty_level: int
    content: dict
    symbol_ids: list[uuid.UUID] | None
    estimated_duration_minutes: int
    is_template: bool
    created_at: datetime

    model_config = {"from_attributes": True}


# --- ActivityResult schemas ---

class ActivityResultCreate(BaseModel):
    program_id: uuid.UUID
    activity_id: uuid.UUID
    profile_id: uuid.UUID
    score: int | None = Field(default=None, ge=0, le=100)
    correct_answers: int = Field(default=0, ge=0)
    total_questions: int = Field(default=0, ge=0)
    time_spent_seconds: int = Field(default=0, ge=0)
    responses: dict | None = None
    notes: str | None = None


class ActivityResultRead(BaseModel):
    id: uuid.UUID
    program_id: uuid.UUID
    activity_id: uuid.UUID
    profile_id: uuid.UUID
    started_at: datetime
    completed_at: datetime | None
    score: int | None
    correct_answers: int
    total_questions: int
    time_spent_seconds: int
    responses: dict | None
    notes: str | None

    model_config = {"from_attributes": True}


# --- Progress summary ---

class LiteracyProgressSummary(BaseModel):
    program_id: uuid.UUID
    profile_name: str
    current_stage: str
    total_activities_completed: int
    average_score: float
    total_time_minutes: int
    activities_by_type: dict  # {activity_type: {completed: N, avg_score: N}}
    milestones: list[dict]
    recommendations: list[str]
