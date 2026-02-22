from pydantic import BaseModel, Field
from typing import Optional


class ClueSource(BaseModel):
    event_index: int = Field(description="Zero-based index of the crime event in CrimeGraph.crime_events")
    trace_index: int = Field(description="Zero-based index of the trace in the event's traces_left")
    trace_type: Optional[str] = Field(description="Type of the trace, copied from the source trace")
    trace_description: Optional[str] = Field(description="Description of the trace, copied or paraphrased from the source trace")


class Clue(BaseModel):
    id: str = Field(description="Unique identifier for the clue")
    source: ClueSource = Field(description="Reference to the trace this clue is based on")
    observation: str = Field(description="What the detective notices or learns from the trace")
    interpretation: str = Field(description="Interpretation of the observation")
    correctness: str = Field(description="Correctness relative to ground truth: correct, partial, or misleading")
    reliability: str = Field(description="Perceived reliability from detective's perspective: low, medium, or high")
    points_to: list[str] = Field(description="Actor ids this clue seems to implicate or connect to")
    ambiguity: Optional[str] = Field(default=None, description="Why this clue could be misleading, incomplete, or uncertain")


class Inference(BaseModel):
    id: str = Field(description="Unique identifier for the inference")
    derived_from_clue_ids: list[str] = Field(description="Clue ids this inference is logically derived from")
    derived_from_inference_ids: list[str] = Field(default=[], description="Inference ids this inference builds upon, if any")
    reasoning: str = Field(description="Logical reasoning that connects the source clues to this conclusion")
    conclusion: str = Field(description="The conclusion drawn from combining the clues")
    correctness: str = Field(description="Correctness relative to ground truth: correct, partial, or misleading")
    points_to: list[str] = Field(description="Actor ids this inference seems to implicate or connect to")
    ambiguity: Optional[str] = Field(default=None, description="Why this inference could be uncertain or lead to wrong conclusions")


class Hypothesis(BaseModel):
    id: str = Field(description="Unique identifier for the hypothesis")
    suspect_id: str = Field(description="Actor id of the suspect this hypothesis targets")
    claim: str = Field(description="Concise hypothesis statement about how and why the suspect committed the crime")
    supporting_clue_ids: list[str] = Field(default=[], description="Clue ids that support this hypothesis")
    supporting_inference_ids: list[str] = Field(default=[], description="Inference ids that support this hypothesis")
    contradicting_clue_ids: list[str] = Field(default=[], description="Clue ids that weaken this hypothesis, if any")
    contradicting_inference_ids: list[str] = Field(default=[], description="Inference ids that weaken this hypothesis, if any")
    derived_from_hypothesis_ids: list[str] = Field(default=[], description="Hypothesis ids this hypothesis refines or builds upon. Empty if this is an initial hypothesis.")
    confidence: float = Field(description="Confidence score from 0.0 to 1.0")
    correctness: str = Field(description="Correctness relative to ground truth: correct, partial, or incorrect")


class InvestigationGraph(BaseModel):
    clues: list[Clue] = Field(description="Base clues derived directly from traces in the crime graph")
    inferences: list[Inference] = Field(description="Logical conclusions drawn from combining clues or other inferences")
    hypotheses: list[Hypothesis] = Field(description="Complete suspect theories formed from clues and inferences")
    leading_hypothesis_id: Optional[str] = Field(default=None, description="Id of the currently strongest hypothesis")
    notes: Optional[str] = Field(default=None, description="Any brief notes about investigative direction")
