from pydantic import BaseModel, Field
from typing import Optional


class SettingData(BaseModel):
    location: str = Field(description="Primary location where the story takes place")
    time_period: str = Field(description="Time period in which the story is set")
    atmosphere: str = Field(description="Atmosphere or mood of the setting")


class Relationship(BaseModel):
    type: str = Field(description="Type of relationship, e.g., friend, enemy, family, colleague")
    target: str = Field(description="Name of the other actor that this relationship is with")


class Actor(BaseModel):
    name: str = Field(description="Unique name of the actor")
    description: str = Field(
        description=(
            "Static profile only: appearance, mannerisms, personality, social role, and backstory. "
            "Do not include case events (e.g., body discovery, murder circumstances, clue handling, "
            "or investigation outcomes) unless explicitly provided by the user prompt."
        )
    )
    occupation: Optional[str] = Field(description="Occupation of the actor, if relevant")
    character_traits: list[str] = Field(description="List of traits relevant to the story")
    relationships: list[Relationship] = Field(description="List of relationships with other actors")


class Victim(Actor):
    pass


class Suspect(Actor):
    culprit: bool = Field(
        default=False,
        description="Whether this suspect is the culprit. Culprit selection can be performed in a separate step.",
    )


class Detective(Actor):
    type: str = Field(description="Type of detective, e.g., amateur, professional, private eye")
    detective_style: str = Field(description="Detective's style or approach to solving the crime")
    strengths: list[str] = Field(description="Detective's strengths relevant to the investigation")
    weaknesses: list[str] = Field(description="Detective's weaknesses relevant to the investigation")


class SideKick(Actor):
    role: str = Field(description="Sidekick's role in assisting the detective")
    skills: list[str] = Field(description="Sidekick's skills relevant to their role")


class SideCharacter(Actor):
    pass


class ActorPool(BaseModel):
    victim: Victim = Field(description="The victim of the crime")
    suspects: list[Suspect] = Field(description="List of suspects in the story")
    detective: Detective = Field(description="The detective investigating the crime")
    side_kick: Optional[SideKick] = Field(default=None, description="The detective's sidekick, if relevant")
    side_characters: list[SideCharacter] = Field(
        description="Other side characters that are relevant to the story"
    )


class PromptConstraint(BaseModel):
    text: str = Field(description="Constraint text stated by the user")
    hard: bool = Field(
        default=True,
        description="Whether this is a hard requirement that must be preserved downstream",
    )
    source_quote: Optional[str] = Field(
        default=None,
        description="Optional exact quote from the user prompt that captures this constraint",
    )


class PromptConstraints(BaseModel):
    constraints: list[PromptConstraint] = Field(
        default_factory=list,
        description="All constraints explicitly requested by the user",
    )
    banned_elements: list[str] = Field(
        default_factory=list,
        description="Elements the user explicitly asked to avoid",
    )


class StoryData(BaseModel):
    setting: SettingData = Field(description="Finalized setting context used by downstream stages")
    actor_pool: ActorPool = Field(description="Core cast for the story")
    prompt_constraints: PromptConstraints = Field(
        default_factory=PromptConstraints,
        description="Structured ledger of user constraints extracted from the original prompt",
    )