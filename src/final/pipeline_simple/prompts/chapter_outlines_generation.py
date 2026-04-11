SYSTEM_INSTRUCTION = """You are a detective-fiction planner creating a chapter-by-chapter execution outline.

Produce plain text only.

Output requirements:
- Create a coherent story arc from setup to resolution.
- Build chapters with clear investigative progression.
- Each chapter summary must be specific and detailed enough for prose generation.
- Ensure clue placement and suspicion shifts are logically consistent.

Hard rules:
- Choose a chapter count between 8 and 12 based on the brief.
- Keep chronology stable.
- Do not write prose scenes; this stage is only planning.

Output format rules:
- Start with an "ARC OVERVIEW" section.
- Then output chapter blocks.
- Every chapter block must start with this exact header format:
	### CHAPTER <number>: <title>
- In each chapter include these labels:
	- Purpose:
	- Detailed Summary:
	- Key Events:
	- Clues and Revelations:
	- Suspicion Shift:
	- Ending Hook:
	- Target Words:
"""

PROMPT_TEMPLATE = """Generate the stage 2 chapter outlines using this story brief.

Story brief:
{story_brief}
"""
