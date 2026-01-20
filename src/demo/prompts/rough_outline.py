
class DataDict(dict):
    def __missing__(self, key):
        return "not specified"


PROMPT_TEMPLATE = """
Create a **rough outline** for a unique **detective mystery**.
The story should be intelligent, suspenseful, and emotionally engaging, while avoiding clichés and predictable tropes.

Here are some preferences to guide your outline:

User preferences:
- **Setting / Time period:** {setting}
- **Detective / Protagonist type:** {detective}
- **Themes or Tropes to include:** {tropes}
- **Tone / Mood:** {tone}
- **Special Constraints or Requests:** {constraints}

If a field is blank or not provided, you must **decide creatively** what fits best for a coherent, compelling story.

Focus on a **single, self-contained mystery** suitable for a novel-length story.
Ensure that the clues, twists, and resolution are **logically consistent** with prior events and character motives.

If you invent details, ensure they are consistent with any provided information (for example, tone, setting, or protagonist type).

Structure the output using these labeled sections:

1. **Title**
2. **Main Characters** — detective, sidekick, suspects, and their motivations
3. **Setting** — time, place, and atmosphere
4. **Central Mystery** — the core crime or enigma
5. **Key Plot Points and Twists** — major developments and discoveries
6. **Conclusion / Resolution** — how the mystery is solved and how it ends
7. **Unique Element** — what makes this story stand out from typical mysteries
"""