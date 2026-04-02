import uuid
from datetime import datetime

from pydantic import BaseModel


class LanguageExpansionRequest(BaseModel):
    symbols: list[str]  # List of symbol labels in order
    context: dict | None = None  # Optional context (time, location, etc.)


class LanguageExpansionResponse(BaseModel):
    expanded: str
    alternatives: list[str] = []
    explanation: str = ""


class BoardGenerationRequest(BaseModel):
    profile_id: uuid.UUID
    board_type: str = "personal"
    context: str = "geral"
    auto_create: bool = False


class BoardGenerationResponse(BaseModel):
    name: str
    grid_rows: int
    grid_cols: int
    cells: list[dict]
    rationale: str = ""
    board_id: str | None = None


class ClinicalInsightsRequest(BaseModel):
    profile_id: uuid.UUID
    since: datetime | None = None
    until: datetime | None = None
