from pydantic import BaseModel, Field
from typing import List


class CharacterActions(BaseModel):
    """Key actions performed by characters in these chapters."""
    character: str = Field(description="Name of the character")
    actions: List[str] = Field(description="List of actions performed by the character")


class Clue(BaseModel):
    """A clue, whether physical, verbal, behavioral, or environmental."""
    description: str = Field(description="Description of the clue")
    type: str = Field(description="Type of the clue, e.g. 'physical', 'behavioral', 'testimony', 'timeline'")
    relevance: str = Field(description="Relevance of the clue, e.g. 'major', 'minor', 'red herring'")


class ChapterChunkSummary(BaseModel):
    chapter_numbers: List[int] = Field(description="List of chapter numbers included in this summary")
    short_summary: str = Field(description="A brief summary of the chapters, around 4-6 sentences")
    key_events: List[str] = Field(description="List of key events in the chapters")
    major_character_actions: List[CharacterActions] = Field(description="Key actions performed by characters in these chapters")
    revealed_clues: List[Clue] = Field(description="List of clues revealed in these chapters")
    introduced_mysteries: List[str] = Field(description="List of mysteries introduced in these chapters")
    foreshadowing_elements: List[str] = Field(description="List of foreshadowing elements present in these chapters")


class SimilarWork(BaseModel):
    title: str = Field(description="Title of the similar work")
    aspect: str = Field(description="Aspect in which this work is similar to the evaluated chapters")


class SimilarityEvaluation(BaseModel):
    plot_similarity: str = Field(description="Similarity of the plot to common detective story tropes")
    character_archetype_similarity: str = Field(description="Similarity of characters to common detective story archetypes")
    setting_similarity: str = Field(description="Similarity of the setting to common detective story settings")
    similar_works: List[SimilarWork] = Field(description="List of similar detective works identified")


class ConsistencyEvaluation(BaseModel):
    character_behavior_consistency: str = Field(description="Consistency of character behavior across chapters")
    timeline_consistency: str = Field(description="Consistency of the timeline across chapters")
    logic_flaws: List[str] = Field(description="List of identified logic flaws")
    contradictions: List[str] = Field(description="List of identified contradictions")


class DetectiveGenreMetrics(BaseModel):
    clue_fairness_score: int = Field(description="Clue fairness score (0-5)")
    pacing_score: int = Field(description="Pacing score (0-5)")
    tension_curve_score: int = Field(description="Tension curve score (0-5)")
    red_herring_quality_score: int = Field(description="Red herring quality score (0-5)")
    mystery_engagement_score: int = Field(description="Mystery engagement score (0-5)")
    

class ChapterChunkEvaluation(BaseModel):
    summary: ChapterChunkSummary = Field(description="Summary of the chapter chunk")
    consistency: ConsistencyEvaluation = Field(description="Consistency evaluation of the chapter chunk")
    similarity: SimilarityEvaluation = Field(description="Similarity evaluation of the chapter chunk")
    detective_metrics: DetectiveGenreMetrics = Field(description="Detective genre metrics for the chapter chunk")