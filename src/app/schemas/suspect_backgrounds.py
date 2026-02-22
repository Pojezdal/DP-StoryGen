from pydantic import BaseModel, Field
from typing import Optional


class BackgroundTrace(BaseModel):
    type: str = Field(description="Type of trace, e.g., physical evidence, witness, digital evidence, behavioral pattern")
    description: str = Field(description="Description of the trace that could be discovered during investigation")


class BackgroundEvent(BaseModel):
    type: str = Field(description="Type of event, e.g., confrontation, concealment, opportunity_seeking, coincidence, preparation")
    description: str = Field(description="Description of what the suspect was doing (innocent but potentially suspicious)")
    actors_involved: list[str] = Field(description="List of actor ids involved in this event")
    location: Optional[str] = Field(description="Location where this event takes place")
    time: Optional[str] = Field(description="Time when this event takes place relative to the crime, e.g., 'two days before the crime', 'the night of the crime'")
    agenda: str = Field(description="The suspect's actual (innocent) motivation for this action, e.g., 'trying to borrow money', 'hiding an affair', 'avoiding embarrassment'")
    traces_left: list[BackgroundTrace] = Field(description="Traces left by this event that could be misinterpreted as crime-related")


class SuspectBackground(BaseModel):
    suspect_id: str = Field(description="Actor id of the suspect this background belongs to")
    background_events: list[BackgroundEvent] = Field(description="Innocent activities this suspect was involved in around the time of the crime")


class SuspectBackgrounds(BaseModel):
    backgrounds: list[SuspectBackground] = Field(description="Background timelines for each innocent suspect (not the culprit)")
