from pydantic import BaseModel, Field
from typing import List

class GlobalStoryEvaluation(BaseModel):
    overall_coherence_score: int = Field(description="Overall coherence score (0-5)")
    detective_logic_strength_score: int = Field(description="Detective logic strength score (0-5)")
    twist_originality_score: int = Field(description="Twist originality score (0-5)")
    clue_payoff_quality_score: int = Field(description="Clue payoff quality score (0-5)")
    suspect_motivation_strength_score: int = Field(description="Suspect motivation strength score (0-5)")
    fair_play_rule_respect_score: int = Field(description="Fair play rule respect score (0-5)")
    final_resolution_strength_score: int = Field(description="Final resolution strength score (0-5)")

    major_plot_holes: List[str] = Field(description="List of major plot holes")
    internal_inconsistencies: List[str] = Field(description="List of internal inconsistencies")
    weak_clues: List[str] = Field(description="List of weak clues")
    dropped_threads: List[str] = Field(description="List of dropped threads, unresolved mysteries")

    recommendations_structural: List[str] = Field(description="List of structural recommendations")
    recommendations_characters: List[str] = Field(description="List of character recommendations")
    recommendations_clues: List[str] = Field(description="List of clue recommendations")
    recommendations_pacing: List[str] = Field(description="List of pacing recommendations")