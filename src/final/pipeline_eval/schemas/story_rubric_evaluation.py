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


class StoryRubricEvaluationWithoutOverall(BaseModel):
    overall_verdict: str = Field(..., min_length=3, description="Short verdict summary")
    general: GeneralStoryRubric
    detective: DetectiveFictionRubric
    prompt_alignment: RubricAspectEvaluation = Field(
        ...,
        description="How well the final story matches the original story-generation prompt and explicit constraints",
    )

    def aspect_scores(self) -> list[int]:
        return [
            self.general.creativity_and_originality.score,
            self.general.coherence_and_structure.score,
            self.general.character_depth.score,
            self.general.pacing_and_tension.score,
            self.general.prose_clarity_and_voice.score,
            self.detective.clue_fairness_and_visibility.score,
            self.detective.deduction_chain_logic.score,
            self.detective.red_herring_quality.score,
            self.detective.suspect_motives_and_opportunity.score,
            self.detective.reveal_and_resolution_payoff.score,
            self.prompt_alignment.score,
        ]

    def computed_overall_score(self) -> float:
        scores = self.aspect_scores()
        if not scores:
            return 0.0
        return round(sum(scores) / len(scores), 1)


class StoryRubricEvaluation(StoryRubricEvaluationWithoutOverall):
    overall_score: float = Field(..., ge=0.0, le=10.0, description="Overall score on a 0-10 scale")

    @classmethod
    def from_without_overall(
        cls,
        evaluation: StoryRubricEvaluationWithoutOverall,
    ) -> "StoryRubricEvaluation":
        return cls(
            overall_score=evaluation.computed_overall_score(),
            overall_verdict=evaluation.overall_verdict,
            general=evaluation.general,
            detective=evaluation.detective,
            prompt_alignment=evaluation.prompt_alignment,
        )
