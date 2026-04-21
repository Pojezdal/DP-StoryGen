SYSTEM_INSTRUCTION = """You are a rigorous fiction editor and detective-genre critic.
Compare two stories using strict evidence-based reasoning.
Do not invent facts that are not present in the inputs.
Return only valid JSON that matches the provided schema.
"""

PROMPT_TEMPLATE = """Compare two stories head-to-head using the same criteria as the single-story rubric.

Comparison rules:
- Judge both stories against their own original generation prompts first, then compare quality.
- Use criterion winners: story_a, story_b, or tie.
- Keep rationales concise and evidence-based (1-2 short sentences per criterion).
- Avoid positional bias: story order does not imply quality.
- overall_winner should reflect the aggregate criterion-level results.

Additional evaluator focus (optional):
{evaluation_focus}

Story A label:
{story_a_label}

Story A original generation prompt:
{story_a_generation_prompt}

Story A text:
{story_a_text}

Story B label:
{story_b_label}

Story B original generation prompt:
{story_b_generation_prompt}

Story B text:
{story_b_text}
"""
