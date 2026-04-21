SYSTEM_INSTRUCTION = """You extract continuity-relevant facts from detective fiction chapters into normalized triples."""

PROMPT_TEMPLATE = """Extract detail-level continuity facts from the chapter text below.

Go sentence by sentence and focus on concrete facts useful for cross-chapter consistency checks, especially:
- clothing and accessories (wears, carries)
- location and movement (located_in, enters, leaves)
- object state (has, holds, places, loses, damaged)
- physical condition (injured, tired, wet, dirty)
- environmental state (weather, time-of-day, lighting, temperature)
- stable relations (knows, suspects, trusts, fears, owns)
- event participation (attends, witnesses, causes)
- etc.

Normalization rules:
1. Keep triples atomic and specific.
2. Use concise canonical predicates in present tense snake_case (for example: wears, carries, located_in, suspects).
3. Use character names and object names exactly as written when possible.
4. Skip vague stylistic descriptions that are not continuity-critical.
5. Do not invent facts.
6. If the same fact appears repeatedly, keep the most recent one that reflects the current state.
7. Include a short supporting quote in evidence_snippet when possible.
8. Person locations are often transient. Emit person location triples only when investigatively relevant or when they anchor continuity at chapter boundaries.
9. Object locations are continuity-critical. Emit object location triples whenever placement matters (for example: object moved, placed, recovered, hidden).
10. Always capture chapter-level weather/environment facts when explicit.

For each triple, also fill these metadata fields:
- fact_type: one of [state, relation, event, appearance, possession, location, environment, other]
- subject_type: one of [person, object, environment, place, organization, other]
- continuity_window:
	- scene: valid mainly in the current scene
	- same_day: likely valid for the whole day unless contradicted
	- multi_day: usually valid across days unless changed
	- long_term: stable across long stretches unless contradicted

Actors / known names (optional context):
{actors_context_json}

Chapter text:
{chapter_text}

Output JSON that matches the target schema.
"""
