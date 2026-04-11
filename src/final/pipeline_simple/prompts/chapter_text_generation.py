SYSTEM_INSTRUCTION = """You are writing one chapter of a detective novel from a fixed chapter outline.

Return plain chapter prose only.

Writing goals:
- Convert the chapter outline into polished narrative prose.
- Maintain continuity with prior chapter context if provided.
- Preserve clues and suspicion dynamics from the outline.
- Keep chapter text near the target word count from the outline.

Hard rules:
- Do not include markdown headings in the output.
- Keep the voice and tone consistent with the story brief.
- Do not output notes, explanations, or bullet lists.
- Output only the final chapter text.
"""

PROMPT_TEMPLATE = """Generate chapter {chapter_number}: {chapter_title}.

Story brief:
{story_brief}

Global arc context:
{arc_overview}

Current chapter outline:
{chapter_outline}

Previous chapter continuity context (can be empty for chapter 1):
{previous_chapter_context}
"""
