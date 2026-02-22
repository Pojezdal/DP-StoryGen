SYSTEM_INSTRUCTION = """You are building the investigation layer for a detective story.
Your task is to create a three-stage reasoning chain: Clues → Inferences → Hypotheses.

You are provided with:
1. CrimeGraph: the actual crime events (ground truth)
2. SuspectBackgrounds: innocent activities by non-culprit suspects that left traces

Rules:
- Clues: create clues from BOTH crime traces AND suspect background traces.
  - Clues from crime traces should be marked with correct correctness (correct/partial/misleading).
  - Clues from suspect background traces are innocent activities that could be misinterpreted as crime-related.
  - One trace can lead to multiple clues if it can be observed or interpreted in different ways, but avoid duplicates.
  - Mark correctness as 'correct', 'partial', or 'misleading' relative to the ground-truth crime graph.
  - Mark reliability as 'low', 'medium', or 'high' based on how reliable the clue appears to the detective.
  
- Inferences: combine 2+ clues (or other inferences) to form logical conclusions.
  - Each inference must have clear reasoning that connects the source clues/inferences to the conclusion.
  - Inferences can chain: new inferences can build on previous inferences.
  - Inferences from background traces may seem to implicate innocent suspects.
  - Mark correctness as 'correct', 'partial', or 'misleading'.
  
- Hypotheses: form 3 to 5 possible complete suspect theories using clues and inferences.
  - Each hypothesis targets one suspect and explains how/why they committed the crime.
  - Innocent suspects can have plausible incorrect hypotheses based on  background traces or misinterpretations of crime traces.
  - The culprit's hypothesis should be supported by actual crime traces.
  - Can be supported or contradicted by both clues and inferences.
  - Mark correctness as 'correct', 'partial', or 'incorrect' based on whether it matches the actual culprit.
  - Hypotheses can refine previous hypotheses by listing them in 'derived_from_hypothesis_ids'.
  
- Use actor ids from the ActorPool when pointing to suspects or other actors.
- Ensure there are enough correct clues and inferences to allow the detective to solve the crime.
- Partial and misleading clues should be plausible and make sense within the story.
"""

PROMPT_TEMPLATE = """Based on the input data, actor pool, crime graph, and suspect backgrounds below, generate the investigation graph.

Input data:
{input_data}

Actor pool:
{actor_pool}

Crime graph (ground truth - actual crime events):
{crime_graph}

Suspect backgrounds (innocent activities that left traces):
{suspect_backgrounds}
"""
