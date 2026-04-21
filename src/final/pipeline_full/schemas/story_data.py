from pydantic import BaseModel, Field
from typing import Optional


class SettingLandmark(BaseModel):
    name: str = Field(description="Name of an important local place")
    function: str = Field(description="Why this place matters in the story")
    local_color: Optional[str] = Field(
        default=None,
        description="Short detail that makes the place memorable and interesting."
    )


class TraitFacet(BaseModel):
    trait: str = Field(description="Trait label")
    manifestation: str = Field(description="How this trait appears in daily behavior")
    vulnerability: str = Field(description="How this trait can backfire under pressure")


class TechnologyProfile(BaseModel):
    era_anchor: str = Field(
        description="Short statement anchoring technology to the specific year range and local context"
    )
    ubiquitous: list[str] = Field(
        default_factory=list,
        description="Technologies that are common and unsurprising in this world",
    )
    emerging: list[str] = Field(
        default_factory=list,
        description="Technologies that exist but are early, patchy, or socially limited",
    )
    socially_unusual: list[str] = Field(
        default_factory=list,
        description="Technologies whose use by certain demographics would require justification",
    )
    plausibility_notes: Optional[str] = Field(
        default=None,
        description="2-4 sentence note about adoption limits, connectivity, and local usage norms",
    )


class SettingData(BaseModel):
    location: str = Field(description="Primary location where the story takes place")
    time_period: str = Field(description="Time period in which the story is set")
    atmosphere: str = Field(description="Atmosphere or mood of the setting")
    sensory_anchors: list[str] = Field(
        default_factory=list,
        description=(
            "Concrete sensory details that make the world feel lived-in "
            "(e.g., recurring sounds, smells, textures, weather cues)"
        ),
    )
    social_texture: Optional[str] = Field(
        default=None,
        description="Short paragraph describing social dynamics, norms, and local power structures",
    )
    quirky_customs: list[str] = Field(
        default_factory=list,
        description="Recurring local habits, rituals, or eccentric traditions that shape daily life",
    )
    landmarks: list[SettingLandmark] = Field(
        default_factory=list,
        description="Important local landmarks used as stable story-world anchors",
    )
    technology_profile: Optional[TechnologyProfile] = Field(
        default=None,
        description="Technology adoption baseline for the setting and time period",
    )


class Relationship(BaseModel):
    type: str = Field(description="Type of relationship, e.g., friend, enemy, family, colleague")
    target: str = Field(description="Name of the other actor that this relationship is with")
    dynamic: Optional[str] = Field(
        default=None,
        description="Current emotional/social dynamic between the two actors",
    )
    history: Optional[str] = Field(
        default=None,
        description="Short note about how this relationship became what it is",
    )
    tension_level: Optional[int] = Field(
        default=None,
        ge=1,
        le=5,
        description="Relationship pressure from 1 (calm) to 5 (volatile)",
    )


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
    character_traits: list[TraitFacet] = Field(
        default_factory=list,
        description=(
            "List of character traits with their manifestations and vulnerabilities"
        ),
    )
    public_persona: Optional[str] = Field(
        default=None,
        description="How the actor appears to others in the community",
    )
    routines: list[str] = Field(
        default_factory=list,
        description="Regular habits that make the actor feel grounded in the world",
    )
    relationships: list[Relationship] = Field(description="List of relationships with other actors")


class Victim(Actor):
    pass


class Suspect(Actor):
    possible_motive: str = Field(
        description="A plausible motive for the suspect to commit the crime. It might be based on a known relationship, a secret, a character trait, "
        "or an inferred desire. This is not necessarily the true motive, but it should be credible and fit with the suspect's profile. "
        "It should be specific and distinct from the motives of other suspects, to create a rich and engaging mystery. "
        "If the user has explicitly specified a motive in the prompt, make sure to include it here and keep it consistent with the rest of the profile."
        )
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