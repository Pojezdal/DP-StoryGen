from __future__ import annotations

from pydantic import BaseModel, Field


class RubricAspectEvaluation(BaseModel):
    score: int = Field(..., ge=0, le=10, description="Aspect score on a 0-10 scale")
    rationale: str = Field(..., min_length=20, description="Why the score was assigned")
    strengths: list[str] = Field(default_factory=list, description="Concrete strengths for this aspect")
    weaknesses: list[str] = Field(default_factory=list, description="Concrete weaknesses for this aspect")


class GeneralStoryRubric(BaseModel):
    creativity_and_originality: RubricAspectEvaluation
    coherence_and_structure: RubricAspectEvaluation
    character_depth: RubricAspectEvaluation
    pacing_and_tension: RubricAspectEvaluation
    prose_clarity_and_voice: RubricAspectEvaluation


class DetectiveFictionRubric(BaseModel):
    clue_fairness_and_visibility: RubricAspectEvaluation
    deduction_chain_logic: RubricAspectEvaluation
    red_herring_quality: RubricAspectEvaluation
    suspect_motives_and_opportunity: RubricAspectEvaluation
    reveal_and_resolution_payoff: RubricAspectEvaluation


class StoryRubricEvaluation(BaseModel):
    overall_score: float = Field(..., ge=0.0, le=10.0, description="Overall score on a 0-10 scale")
    overall_verdict: str = Field(..., min_length=3, description="Short verdict summary")
    general: GeneralStoryRubric
    detective: DetectiveFictionRubric
    prompt_alignment: RubricAspectEvaluation = Field(
        ...,
        description="How well the final story matches the original story-generation prompt and explicit constraints",
    )
