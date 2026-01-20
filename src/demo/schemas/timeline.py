from pydantic import BaseModel, Field
from typing import List


class TimePoint(BaseModel):
    time : str = Field(description="The specific time or date of the event")
    description: str = Field(description="Description of the event at this time point")


class Timeline(BaseModel):
    points: List[TimePoint] = Field(description="List of time points in the timeline in chronological order")