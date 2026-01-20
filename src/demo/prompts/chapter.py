
PROMPT_TEMPLATE = """
Write chapter {index} of a detective novel based on the provided outlines.

Rough outline:
{rough_outline}

Previous chapter outline:
{previous_chapter}

Next chapter outline:
{next_chapter}

This chapter outline:
{current_chapter}

Write the **complete text of this chapter** (around 600 to 900 words), based strictly on the above outlines. Follow these principles:
1. Stay **consistent** with the overall mystery, characters, and tone of the rough outline.
2. Use **the detailed outline** as a blueprint — make it vivid and specific in prose form.
3. Preserve **continuity** with the previous and next chapters:
- Reflect any open emotional or investigative threads.
- Avoid resolving future revelations prematurely.
4. Keep the pacing appropriate — **develop the chapter's own tension and closure**, while smoothly linking to the next one.
5. Avoid meta commentary or referring to "chapters" or "outlines".
6. Maintain a **detective fiction tone** — intelligent dialogue, psychological depth, and logical progression of clues.
"""