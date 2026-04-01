import uuid
from datetime import datetime

from pydantic import BaseModel

from app.models.symbol import GrammaticalClass


class SymbolCreate(BaseModel):
    arasaac_id: int | None = None
    label_pt: str
    category: str
    image_url: str
    grammatical_class: GrammaticalClass
    fitzgerald_color: str
    frequency_rank: int | None = None
    keywords: list[str] | None = None


class SymbolUpdate(BaseModel):
    label_pt: str | None = None
    category: str | None = None
    image_url: str | None = None
    grammatical_class: GrammaticalClass | None = None
    fitzgerald_color: str | None = None
    frequency_rank: int | None = None
    keywords: list[str] | None = None


class SymbolRead(BaseModel):
    id: uuid.UUID
    arasaac_id: int | None
    label_pt: str
    category: str
    image_url: str
    grammatical_class: GrammaticalClass
    fitzgerald_color: str
    frequency_rank: int | None
    keywords: list[str] | None
    created_at: datetime

    model_config = {"from_attributes": True}
