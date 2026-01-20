SYSTEM_INSTRUCTION = """You are a professional editor and critic specializing in detective fiction, murder mysteries, and logical narrative construction."""

PROMPT_TEMPLATE = """
Here are TWO CHAPTERS of a detective novel. Your job is to extract structured information AND evaluate 
the chapters according to detective-genre requirements.

Fill ALL fields of the JSON schema strictly and faithfully.

Focus especially on:
- clues (physical, behavioral, testimony, timeline)
- foreshadowing
- character motivations & actions
- mini-mysteries introduced
- contradictions or logic errors
- fairness of clue placement
- pacing & engagement

Do NOT invent new details. Use ONLY what the chapters explicitly contain or imply. Be as strict as possible, pointing out every inconsistency and flaw.
Score the story on a scale from 0 to 5 for each of the following: clue fairness, pacing, tension curve, red herring quality, and overall mystery engagement,
with 3 being average, and 5 being excellent.

{chapter1}

{chapter2}
"""