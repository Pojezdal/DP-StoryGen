from pydantic import BaseModel, Field
from typing import List


class Chapter(BaseModel):
    title: str = Field(description="Title of the chapter")
    summary: str = Field(description="Summary of the chapter's content")
    key_events: List[str] = Field(description="List of key events that occur in the chapter")

class DetailedOutline(BaseModel):
    chappter_count: int = Field(description="Total number of chapters in the story")
    chapters: List[Chapter] = Field(description="List of chapters with detailed information")