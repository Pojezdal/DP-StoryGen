from __future__ import annotations

import json

from final.llm.google_llm import GoogleLLM
from final.pipeline_simple import run_simple_pipeline
from final.utils.serialization import StoryDirectory


MODEL_ID = "gemini-2.5-flash"
STORY_TITLE = "simple_story"
STORY_DIR_TO_OPEN = ""  # set to an existing folder under stories/ to resume
FORCE_EXECUTE_STAGES = False
FORCE_REGENERATE_CHAPTERS = False

USER_INPUT = (
    "I want to write a detective story set in a small English town at the turn of the "
    "20th and 21st century. The atmosphere should be lighter with occasional humor, but "
    "the central crime should still feel intriguing and high-stakes. The protagonist is an "
    "older retired detective planning a quiet holiday who gets pulled into solving a complex "
    "murder. The story should include the local church, and an item in an old local newspaper "
    "should play an important role in the case."
)


def main() -> None:
    with open("cred.json", "r", encoding="utf-8") as f:
        cred = json.load(f)
    api_keys = cred.get("google_api_keys", [])
    if not api_keys:
        raise ValueError("Missing 'google_api_keys' in cred.json")

    llm = GoogleLLM(model_id=MODEL_ID, api_keys=api_keys)
    print(f"Model loaded successfully: {MODEL_ID}")

    if STORY_DIR_TO_OPEN.strip():
        story_directory = StoryDirectory.open(STORY_DIR_TO_OPEN.strip())
    else:
        story_directory = StoryDirectory.new(title=STORY_TITLE)

    result = run_simple_pipeline(
        llm=llm,
        story_directory=story_directory,
        user_input=USER_INPUT,
        force_execute_stages=FORCE_EXECUTE_STAGES,
        force_regenerate_chapters=FORCE_REGENERATE_CHAPTERS,
    )

    chapter_count = len(result["chapter_texts"])
    print(f"Simple pipeline finished. Story directory: {result['story_directory']}")
    print("Stage outputs are plain text only.")
    print(f"Generated chapters: {chapter_count}")
    print("Compiled manuscript: final_story_simple.txt")


if __name__ == "__main__":
    main()
