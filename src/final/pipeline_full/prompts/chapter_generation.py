SYSTEM_INSTRUCTION = """You are a novelist specializing in detective fiction with strong continuity, clue discipline, and fair-play plotting."""

PROMPT_TEMPLATE = """You are writing Chapter {chapter_number} of a detective novel.

You must use the provided chapter data package as the source of truth for this chapter.

GLOBAL STORY CONTEXT
- Total chapters and pacing: {overview_text}
- Story outline anchor: {story_outline}
- Architecture beat map (investigation chronology): {architecture_beat_map}
- Breakthrough design (late proof path): {breakthrough_design}
- Clue graph context (optional metadata): {clue_graph_context}
- Global clue distribution: {global_clue_distribution}
- Pacing and fair-play notes: {pacing_notes}
- Actors: {actors}

CURRENT CHAPTER PACKAGE
{current_chapter_package_json}

PREVIOUS CHAPTER ENDING CONTEXT
Use this for chapter continuity and seamless transitions.
If this is Chapter 1, this section is intentionally empty.

{previous_chapter_ending_context}

Your tasks:
1. Write full prose for this chapter, not an outline.
2. Follow the chapter package strictly:
   - Respect chapter purpose, start state, scene plan, revealed_clues, previously_revealed_clues, forbidden_clues, clue_state_ledger, continuity, and end_state.
   - Keep detective reasoning consistent with currently wrongly framed beliefs.
   - Treat story_constraints as canonical truth bounds.
   - Use suspect behavior texture from actors[*].suspect_brief where available.
3. Respect chapter clue scope strictly:
   - Introduce only clues listed in revealed_clues for this chapter.
   - Clues in previously_revealed_clues can be referenced and built upon, but do not re-describe them in detail as if new.
   - Do not reference or describe forbidden_clues in any way, as they are meant to be hidden from the reader until future chapters.
   - Do not introduce decisive new evidence or major clue resolutions that are not grounded in this package.
   - If prior clues are referenced for continuity, treat them as already-known context unless this package explicitly advances them.
4. Continuity requirement for Chapter 2 and later:
   - In the first 1-2 paragraphs, naturally connect to the emotional and investigative momentum from PREVIOUS CHAPTER ENDING CONTEXT.
   - Do not repeat prior text verbatim.
5. Style and quality:
   - Detective fiction tone, concrete actions, grounded dialogue, sensory detail.
   - No meta comments about outlines, packages, prompts, or chapters as artifacts.
   - No contradictions with story_constraints (culprit truth, hidden premise, and final proof), but do not prematurely expose hidden premise.
6. End the chapter by landing on the intended chapter hook from the package as a semantic target, not a quoted line.
   - Integrate the end_state.chapter_hook idea naturally into the final paragraph.
   - Do not copy the chapter_hook text verbatim.
   - Avoid adding a standalone final sentence that simply restates the hook.

Length target:
- {word_min} to {word_max} words.

Optional clue-graph behavior:
- If clue_graph_context.enabled is true, keep chapter-level reasoning aligned with clue_graph_proof_chain_node_ids progression in story_constraints.
- If clue_graph_context.enabled is false, rely on revealed/previously_revealed/forbidden clues and continuity as the authoritative gate.

Output format:
SECTION 1: CHAPTER_TEXT
- Full chapter prose only.

SECTION 2: NEXT_CHAPTER_HANDOFF
Provide exactly:
A) 5-10 sentence summary (used as context for the next chapter) focused on:
   - key events and revelations in this chapter
   - emotional state
   - active investigation theory
B) Open threads list (3-6 bullet points)


Format stability note:
- Keep SECTION headers exactly as plain text shown above.
- Do not add decorators around SECTION headers (for example: no leading ###, bullets, or bold wrappers on the header line).
"""
