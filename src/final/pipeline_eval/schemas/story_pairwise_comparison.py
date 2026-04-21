from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class PairwiseCriterionResult(BaseModel):
    winner: Literal["story_a", "story_b", "tie"] = Field(
        ...,
        description="Which story performed better for this criterion",
    )
    rationale: str = Field(..., min_length=20, description="Evidence-based criterion comparison")


class PairwiseCriteriaComparison(BaseModel):
    creativity_and_originality: PairwiseCriterionResult
    coherence_and_structure: PairwiseCriterionResult
    character_depth: PairwiseCriterionResult
    pacing_and_tension: PairwiseCriterionResult
    prose_clarity_and_voice: PairwiseCriterionResult
    clue_fairness_and_visibility: PairwiseCriterionResult
    deduction_chain_logic: PairwiseCriterionResult
    red_herring_quality: PairwiseCriterionResult
    suspect_motives_and_opportunity: PairwiseCriterionResult
    reveal_and_resolution_payoff: PairwiseCriterionResult
    prompt_alignment: PairwiseCriterionResult


class StoryPairwiseComparison(BaseModel):
    story_a_label: str = Field(..., min_length=1)
    story_b_label: str = Field(..., min_length=1)
    overall_winner: Literal["story_a", "story_b", "tie"]
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence in overall decision")
    overall_rationale: str = Field(..., min_length=20)
    criteria: PairwiseCriteriaComparison
    tradeoffs: list[str] = Field(default_factory=list, description="Most important quality tradeoffs")
    improvement_priority_story_a: list[str] = Field(
        default_factory=list,
        description="Top improvements for story A",
    )
    improvement_priority_story_b: list[str] = Field(
        default_factory=list,
        description="Top improvements for story B",
    )
