from __future__ import annotations

from pydantic import BaseModel, Field


class ChapterOutline(BaseModel):
    chapter_number: int = Field(..., ge=1)
    chapter_title: str = Field(..., min_length=3)
    chapter_purpose: str = Field(..., min_length=20)
    chapter_summary: str = Field(..., min_length=120)
    key_events: list[str] = Field(default_factory=list)
    clues_or_revelations: list[str] = Field(default_factory=list)
    suspicion_shift: str = Field(..., min_length=10)
    ending_hook: str = Field(..., min_length=10)
    target_word_count: int = Field(default=1200, ge=600, le=2500)


class ChapterOutlinePackage(BaseModel):
    arc_overview: str = Field(..., min_length=60)
    continuity_rules: list[str] = Field(default_factory=list)
    chapters: list[ChapterOutline] = Field(default_factory=list, min_length=3)
