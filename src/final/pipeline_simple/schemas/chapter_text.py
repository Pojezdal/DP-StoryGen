from __future__ import annotations

from pydantic import BaseModel, Field


class ChapterDraft(BaseModel):
    chapter_number: int = Field(..., ge=1)
    chapter_title: str = Field(..., min_length=3)
    text: str = Field(..., min_length=300)
    short_handoff: str = Field(..., min_length=20)
