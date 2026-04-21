from __future__ import annotations

from typing import List, Literal
from pydantic import BaseModel, Field


class DetailTriple(BaseModel):
    subject: str = Field(..., min_length=1)
    predicate: str = Field(..., min_length=1)
    object: str = Field(..., min_length=1)
    evidence_snippet: str = Field(default="")
    fact_type: Literal[
        "state",
        "relation",
        "event",
        "appearance",
        "possession",
        "location",
        "environment",
        "other",
    ] = "other"
    subject_type: Literal[
        "person",
        "object",
        "environment",
        "place",
        "organization",
        "other",
    ] = "other"
    continuity_window: Literal["scene", "same_day", "multi_day", "long_term"] = "same_day"


class DetailTripleExtraction(BaseModel):
    triples: List[DetailTriple] = Field(default_factory=list)


class DetailTripleExtractionResult(BaseModel):
    chapter_text_hash: str = Field(default="")
    triples: List[DetailTriple] = Field(default_factory=list)
