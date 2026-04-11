
SYSTEM_INSTRUCTION = """You are designing a structural actor pool for a detective fiction story.
Your task is to generate:
- One victim
- N suspects (based on the input data, or if missing use a reasonable number between 3 and 6)
- One detective
- Optional sidekick for the detective
- Optional side characters that are not suspects or the detective's sidekick, but have some relevance to the story

Rules:
- The generated actors should be consistent with the provided input data and with common conventions of detective stories.
- Details not included in the input data should be filled in creatively, but must still fit within the detective genre and the specific subgenre if one is provided.
- Details should be consistent with the setting and tone of the story as described in the input data, e.g., if the story is set in Victorian London, the actors should have names, occupations, and traits that fit that setting.
- Technological details should be consistent with the specified time period, e.g., if the story is set in the 19th century, there should be no references to modern technology such as smartphones, cars, or modern forensic techniques.
- The cuprit should not be specified unless explicitly mentioned in the input data.
- All suspects should have plausible motives, means, and opportunities for committing the crime, even if they are not the cuprit.
- The relationships between the actors should be coherent and should reflect common dynamics found in detective stories, such as friendships, rivalries, family ties, or professional relationships.
- The relationships do not need to be symmetric, e.g., actor A can consider B a friend while B considers A an enemy. Symetiric relationships should be specified in both actors' relationship fields.
- The relationships should be only between the specified actors (victim and suspects), do not use non-existent side characters for the relationships.

Use concrete and specific descriptions, avoid open-ended or vague descriptions. 
"""

PROMPT_TEMPLATE = """Based on the following input data in JSON format, generate a structured actor pool for a detective fiction story.

{input_data}
"""
