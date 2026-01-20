from pydantic import BaseModel, Field
from typing import List


class Character(BaseModel):
    name: str = Field(description="Name of the character")
    role: str = Field(description="Role of the character in the story, e.g. protagonist, antagonist, sidekick")
    description: str = Field(description="A brief description of the character")
    traits: List[str] = Field(description="List of key traits of the character")


class Setting(BaseModel):
    location: str = Field(description="Location of the setting")
    time_period: str = Field(description="Time period of the setting")
    atmosphere: str = Field(description="Atmosphere or mood of the setting")


class PlotPoint(BaseModel):
    title : str = Field(description="Title of the plot point")
    description: str = Field(description="Description of the plot point")
    significance: str = Field(description="Significance of the plot point to the overall story")


class Resolution(BaseModel):
    description: str = Field(description="Description of the resolution")
    method : str = Field(description="Method by which the mystery is resolved, e.g. deduction, confession, discovery")
    evidence_used : List[str] = Field(description="List of key pieces of evidence used in the resolution")

class RoughOutline(BaseModel):
    title : str = Field(description="Title of the story")
    genre : str = Field(description="Genre of the story")
    synopsis : str = Field(description="A brief synopsis of the story")
    characters : List[Character] = Field(description="List of main characters in the story")
    setting : Setting = Field(description="Details of the story's setting")
    central_mystery : str = Field(description="Description of the central mystery or crime to be solved")
    plot_points : List[PlotPoint] = Field(description="List of major plot points in the story")
    resolution : Resolution = Field(description="Details of the story's resolution")
    note : str = Field(description="Additional notes or comments about the rough outline")