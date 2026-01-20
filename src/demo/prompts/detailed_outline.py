
PROMPT_TEMPLATE = """
Expand the following rough outline into a detailed, chapter-by-chapter outline for a full-length detective novel.

Rough outline:
{rough_outline}

The outline should:
- Include 10 to 14 chapters, unless the mystery resolves naturally earlier.
- Describe what exactly happens — not just the purpose of the chapter.
- Resolve any vague terms in the rough outline (e.g., "family secret," "hidden room") into specific, concrete ideas that connect logically to the investigation.
- Include who does what, how they discover things, and what changes in the investigation or characters as a result.
- Ensure continuity — evidence or clues mentioned in one chapter should reappear or influence later ones.
- Stop once the mystery and character arcs are resolved.

Avoid:
- Summarizing or describing "what should happen" — instead, write what does happen.
- Generic filler chapters or repeated beats.

Format:
[Chapter number]. [Title]
[5-8 sentences describing the specific events, discoveries, or interactions in this chapter.]

Finish the outline with [END] tag and stop immediately after the [END] tag.
"""