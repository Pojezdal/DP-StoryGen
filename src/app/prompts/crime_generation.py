
SYSTEM_INSTRUCTION = """You are constructing the objective crime timeline for a detective story.
This is the ground truth of what actually happened. Ensure that the timeline is consistent with the provided input data and with common conventions of detective stories.
Also ensure logical consistency within the timeline itself and causality, e.g., the preparation for the crime must happen before the execution of the crime, the decision to commit the crime must happen before the preparation and execution, etc.

Generate events that describe the crime, the events leading up to the crime, and the events immediately following the crime.
The events should describe:
- Decision: any decision made by any actor that is relevant to the crime, e.g., the decision to commit the crime itself, the decision to choose a specific method for committing the crime, the decision to target a specific victim, the decision to frame someone else for the crime, etc., including the motivations behind those decisions
- Preparation: any preparation made for the crime, e.g., buying a weapon, researching the victim's schedule, acquiring a key to the victim's house, ensuring an alibi for the time of the crime
- Execution: the execution of the crime itself, e.g., the act of poisoning the victim's drink, the act of shooting the victim, the act of breaking into the house to commit the crime
- Cover-up: any action taken to cover up the crime, e.g., cleaning up the crime scene, moving the body, staging the crime scene to look like a burglary, deleting digital evidence, persuading witnesses to lie

Each event can leave behind crime traces, that migh be discovered by the detective during the investigation and help solve the crime.

Uses concrete and specific descriptions for the crime events and crime traces, avoid vague or generic descriptions. For example, instead of saying "the suspect prepared for the crime", say "the suspect bought a bottle of arsenic from the local pharmacy",
or instead of saying "the suspect left behind evidence at the crime scene", say "the suspect left fingerprints on the glass used for poisoning".
Try to be creative and imaginative with the crime events and crime traces to provide an engaging and intriguing crime timeline.
"""

PROMPT_TEMPLATE = """Based on the following input data and provided actor pool, generate a structured crime graph that describes the objective crime timeline for a detective story.

Input data:
{input_data}

Actor pool:
{actor_pool}
"""
