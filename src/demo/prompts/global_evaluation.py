
SYSTEM_INSTRUCTION = """You are a professional editor and critic specializing in detective fiction, murder mysteries, and logical narrative construction."""

PROMPT_TEMPLATE = """
Here is a list of partial summaries and evaluations of pairs of chapters of a detective novel.
Aggregate the results and evaluate the story on the global scope
Fill ALL fields of the JSON schema strictly and faithfully
Focus especially on:
- plot holes and incosistencies across the whole story
- logical flaws and deus-ex machina situations
- loose or dropped threads
- overall pacing and engagement
- originality and creativity of the stor
Do NOT invent new details. Use ONLY what the summaries explicitly contain or imply. Be as strict and precise as possible.
Score the story on a scale from 0 to 5 for each of the following: overall coherence, detective logic strength, twist originality, 
clue payoff quality, suspect motivation strength, fair play rule respect, final resolution strength, with 3 being average, and 5 being excellent.

Summaries:
{summaries}
"""