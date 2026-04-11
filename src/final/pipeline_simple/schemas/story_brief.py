from __future__ import annotations

from pydantic import BaseModel, Field


class StoryConstraint(BaseModel):
    text: str = Field(..., min_length=3)
    hard: bool = True


class CharacterProfile(BaseModel):
    name: str = Field(..., min_length=1)
    role: str = Field(..., min_length=1)
    summary: str = Field(..., min_length=10)


class StoryBrief(BaseModel):
    title: str = Field(..., min_length=3)
    genre: str = Field(default="Detective Mystery", min_length=3)
    setting: str = Field(..., min_length=5)
    time_period: str = Field(..., min_length=3)
    atmosphere: str = Field(..., min_length=3)
    premise: str = Field(..., min_length=20)
    central_mystery: str = Field(..., min_length=20)
    target_chapter_count: int = Field(default=8, ge=3, le=20)
    main_cast: list[CharacterProfile] = Field(default_factory=list)
    constraints: list[StoryConstraint] = Field(default_factory=list)
    narrative_notes: list[str] = Field(default_factory=list)
