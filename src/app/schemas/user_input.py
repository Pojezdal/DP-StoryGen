from pydantic import BaseModel, Field
from typing import Optional


class StructureData(BaseModel):
    length: Optional[int] = Field(description="Length of the story in chapters (8-12 chapters scaling with complexity)")
    complexity: Optional[str] = Field(description="Complexity of the plot (e.g., simple, moderate, complex)")
    twist_specifications: Optional[str] = Field(description="Any specific constraints or requirements related to plot twists")
    red_herring_specifications: Optional[str] = Field(description="Any specific constraints or requirements related to red herrings")

class SettingData(BaseModel):
    location: Optional[str] = Field(description="Location where the story takes place")
    time_period: Optional[str] = Field(description="Time period in which the story is set")
    atmosphere: Optional[str] = Field(description="Atmosphere or mood of the setting")
    isolation_level: Optional[str] = Field(description="Level of isolation in the setting (e.g., isolated mansion, bustling city, remote village)")
    
class CrimeData(BaseModel):
    crime_type: Optional[str] = Field(description="Type of crime around which the story revolves")
    method: Optional[str] = Field(description="Method used to commit the crime")
    motive: Optional[str] = Field(description="Motive behind the crime")
    specifications: Optional[str] = Field(description="Any specific constraints or requirements related to the crime")
    
class CharactersData(BaseModel):
    detective_type: Optional[str] = Field(description="Type of detective (e.g., amateur, professional, private investigator)")
    detective_specifications: Optional[str] = Field(description="Any specific constraints or requirements related to the detective")
    sidekick_type: Optional[str] = Field(description="Type of sidekick (e.g., loyal friend, comic relief, reluctant partner)")
    sidekick_specifications: Optional[str] = Field(description="Any specific constraints or requirements related to the sidekick")
    suspect_count: Optional[int] = Field(description="Number of suspects in the story (3-6 suspects scaling with complexity)")
    
class InputData(BaseModel):
    title: Optional[str] = Field(description="Title of the story")
    genre: Optional[str] = Field(description="Genre of the story")
    theme: Optional[str] = Field(description="Theme of the story")
    core_idea: Optional[str] = Field(description="Core idea or premise of the story")
    
    setting: SettingData = Field(description="Details about the setting of the story")
    crime: CrimeData = Field(description="Details about the crime around which the story revolves")
    characters: CharactersData = Field(description="Details about the main characters in the story")
    structure: StructureData = Field(description="Details about the structure of the story")