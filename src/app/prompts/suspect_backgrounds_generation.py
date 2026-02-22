SYSTEM_INSTRUCTION = """You are creating innocent background activity timelines for suspects in a detective story.
Your task is to generate believable, non-criminal activities for each INNOCENT suspect (not the culprit) that:
1. Overlap temporally with the crime
2. Leave traces that could be misinterpreted during investigation
3. Have legitimate, explainable motivations

Rules:
- Generate backgrounds ONLY for innocent suspects (culprit is excluded)
- Each suspect should have 2-4 background events around the time of the crime
- Events should have real motivations: seeking money/favor, hiding embarrassment, resolving conflicts, coincidental presence
- Traces should be realistic and could plausibly be discovered by investigators
- Make some traces potentially incriminating but ultimately explainable
- Consider the suspect's occupation, relationships, and stated motive/alibi from the actor pool
- Events can involve the victim or other suspects
- Use concrete, specific descriptions

Event types to consider:
- Confrontation: arguing with victim about non-murder issues (money, relationships, disputes)
- Concealment: hiding something embarrassing (affair, debt, addiction, failure)
- Opportunity seeking: trying to get something from victim (loan, favor, recommendation)
- Coincidence: being near crime scene for innocent reasons
- Preparation: planning something unrelated but suspicious-looking (surprise party, secret project)
- Reaction: responding to something the victim did (confronting, avoiding, appeasing)

Traces should include:
- Witness accounts (potentially misremembered or partial)
- Physical evidence (fingerprints, items left behind, signs of presence)
- Digital evidence (messages, calls, records)
- Behavioral patterns (seen arguing, acting nervous, lying about whereabouts)
"""

PROMPT_TEMPLATE = """Based on the input data, actor pool, and crime graph below, generate innocent background activities for each NON-CULPRIT suspect.

Input data:
{input_data}

Actor pool:
{actor_pool}

Crime graph (for temporal context and to avoid overlap):
{crime_graph}
"""
