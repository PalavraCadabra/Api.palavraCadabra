import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, Integer, String, func
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, UUIDPrimaryKeyMixin


class GrammaticalClass(str, enum.Enum):
    pronoun = "pronoun"
    verb = "verb"
    adjective = "adjective"
    noun = "noun"
    social_phrase = "social_phrase"
    misc = "misc"
    question = "question"


class Symbol(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "symbols"

    arasaac_id: Mapped[int | None] = mapped_column(Integer, index=True, nullable=True)
    label_pt: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    category: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    image_url: Mapped[str] = mapped_column(String(1024), nullable=False)
    grammatical_class: Mapped[GrammaticalClass] = mapped_column(
        Enum(GrammaticalClass, name="grammatical_class"),
        nullable=False,
    )
    fitzgerald_color: Mapped[str] = mapped_column(String(7), nullable=False)
    frequency_rank: Mapped[int | None] = mapped_column(Integer, nullable=True)
    keywords: Mapped[list[str] | None] = mapped_column(ARRAY(String), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
