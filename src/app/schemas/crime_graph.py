from pydantic import BaseModel, Field
from typing import Optional

class Relationship(BaseModel):
    type: str = Field(description="Type of relationship, e.g., friend, enemy, family, colleague")
    to: str = Field(description="ID of the other actor in the relationship")

class Actor(BaseModel):
    id: str = Field(description="Unique identifier for the actor")
    relationships: list[Relationship] = Field(description="List of relationships this actor has with other actors in the story, the relationships do not need to be symmetric, e.g., if actor A is a friend of actor B, it does not necessarily mean that actor B is a friend of actor A, the relationships should be based on the input data and should not be inferred based on common sense or general knowledge")
    
class Victim(Actor):
    pass

class Suspect(Actor):
    occupation: str = Field(description="Occupation of the suspect")
    motive: str = Field(description="Specific motive for commiting the crime based on the input data.")
    crime_relevant_traits: list[str] = Field(description="List of traits that are relevant to the crime, e.g., ['greedy', 'jealous']")
    possible_alibi: str = Field(description="Possible alibi for the suspect, e.g., 'was at the pub' or 'was out of town'")
    possible_method: str = Field(description="Concreate possible method for committing the crime, if the method is explicitly specified in the input data, use that method as the possible method but concretize it, e.g., if the specified method is poisoning, a concrete possible method could be 'poisoned the victim's drink with arsenic', otherwise, if the method is not explicitly specified in the input data, infer a possible method based on the suspect's occupation, traits and motive")
    possible_means: list[str] = Field(description="List of possible means for committing the crime, e.g., if the crime is poisoning, possible means could be ['is pharmacist'] or ['prepares food'], if the crime is shooting, possible means could be ['is a hunter'] or ['has a history of violence']")
    culprit: bool = Field(description="Whether the suspect is the culprit of the crime or not, leave false unless the culprit is explicitly specified in the input data, in which case set to true")
    
class ActorPool(BaseModel):
    victim: Victim = Field(description="The victim of the crime")
    suspects: list[Suspect] = Field(description="List of suspects in the story")


class CrimeTrace(BaseModel):
    type: str = Field(description="Type of crime trace, e.g., physical evidence, witness, forensic evidence, digital evidence")
    description: str = Field(description="Description of the crime trace, e.g., 'Fingeprints on the glass used for poisoning', 'A witness saw the suspect arguing with the victim', 'Missing gun from the victim's collection', 'Toxicology report showing presence of poison in the victim's system'")

class CrimeEvent(BaseModel):
    type: str = Field(description="Type of crime event, e.g., decision, preparation, execution or cover-up")
    description: str = Field(description="Description of the crime event, e.g., 'The suspect poisoned the victim's drink at the party', 'The suspect gained access to the victim's house by persuading the maid to let them in', 'The suspect bought a gun.'")
    actors_involved: list[str] = Field(description="List of actor ids involved in the crime event, e.g., ['victim_id', 'suspect_id1']")
    location: Optional[str] = Field(description="Location where the crime event takes place, if relevant")
    time: Optional[str] = Field(description="Time when the crime event takes place relative to the crime itself, e.g., 'two days before the crime', 'the night of the crime', if relevant")
    traces_left: list[CrimeTrace] = Field(description="List of crime traces left by this crime event, e.g., fingerprints, witnesses, forensic evidence, digital evidence")
    
class CrimeGraph(BaseModel):
    crime_events: list[CrimeEvent] = Field(description="List of crime events that make up the crime, including the crime itself and any relevant events leading up to or following the crime")
