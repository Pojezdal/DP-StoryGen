from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from final.pipeline_eval import story_rubric_evaluation, story_pairwise_comparison
from final.utils.serialization import StoryDirectory


PREFERRED_STORY_FILES = (
    "final_story_simple.txt",
    "full_story.txt",
    "final_story.txt",
    "story.txt",
)

FREE_OPENROUTER_MODELS = {
    "openrouter/elephant-alpha",
    "google/gemma-4-26b-a4b-it:free",
    "google/gemma-4-31b-it:free",
    "nvidia/nemotron-3-super-120b-a12b:free",
    "arcee-ai/trinity-large-preview:free",
    "qwen/qwen3-next-80b-a3b-instruct:free",
    "openai/gpt-oss-120b:free",
    "openai/gpt-oss-20b:free",
    "cognitivecomputations/dolphin-mistral-24b-venice-edition:free",
    "meta-llama/llama-3.3-70b-instruct:free",
    "nousresearch/hermes-3-llama-3.1-405b:free",
    
}


def _chapter_sort_key(path: Path) -> tuple[int, str]:
    match = re.search(r"chapter_(\d+)", path.stem.lower())
    if match:
        return (int(match.group(1)), path.name)
    return (10**9, path.name)


def _locate_story_file(story_path: Path) -> Path | None:
    for name in PREFERRED_STORY_FILES:
        candidate = story_path / name
        if candidate.exists() and candidate.is_file():
            return candidate

    txt_files = sorted(story_path.glob("*.txt"))
    if not txt_files:
        return None

    story_like = [p for p in txt_files if "story" in p.stem.lower()]
    return max(story_like or txt_files, key=lambda p: p.stat().st_size)


def _load_story_text(story_path: Path, explicit_story_file: str | None) -> tuple[str, str]:
    if explicit_story_file:
        candidate = Path(explicit_story_file)
        if not candidate.is_absolute():
            candidate = story_path / candidate
        if not candidate.exists() or not candidate.is_file():
            raise FileNotFoundError(f"Story file not found: {candidate}")

        text = candidate.read_text(encoding="utf-8").strip()
        if not text:
            raise ValueError(f"Story file is empty: {candidate}")
        return text, str(candidate)

    selected = _locate_story_file(story_path)
    if selected is not None:
        text = selected.read_text(encoding="utf-8").strip()
        if not text:
            raise ValueError(f"Detected story file is empty: {selected}")
        return text, str(selected)

    chapter_files = sorted(story_path.glob("chapter_*.txt"), key=_chapter_sort_key)
    if chapter_files:
        chunks = [p.read_text(encoding="utf-8").strip() for p in chapter_files]
        chunks = [c for c in chunks if c]
        if chunks:
            return "\n\n".join(chunks), f"compiled from {len(chunks)} chapter_*.txt files"

    raise FileNotFoundError(
        f"No story text found in {story_path}. Add final_story_simple.txt/full_story.txt/final_story.txt/story.txt, "
        "or chapter_*.txt files."
    )


def _create_llm(model_provider: str, model_id: str, cred: dict):
    if model_provider == "google":
        api_keys = cred.get("google_api_keys", [])
        if not api_keys:
            raise ValueError("Missing 'google_api_keys' in cred.json")
        from final.llm.google_llm import GoogleLLM

        return GoogleLLM(model_id=model_id, api_keys=api_keys)

    openrouter_keys = cred.get("openrouter_api_key", [])
    if isinstance(openrouter_keys, str):
        openrouter_keys = [openrouter_keys]
    if not openrouter_keys:
        raise ValueError("Missing 'openrouter_api_key' in cred.json")

    from final.llm.openrouter_llm import OpenRouterLLM

    return OpenRouterLLM(model_id=model_id, api_keys=openrouter_keys)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Evaluate a generated story with the rubric-based pipeline_eval stage."
    )
    parser.add_argument(
        "--story-folder",
        type=str,
        required=True,
        help="Story folder name inside --stories-base-dir (for example 2026-04-13_144051).",
    )
    parser.add_argument(
        "--stories-base-dir",
        type=str,
        default="stories",
        help="Base directory containing story folders (for example stories or stories/simple).",
    )
    parser.add_argument(
        "--story-file",
        type=str,
        default=None,
        help="Optional specific text file (absolute path or relative to selected story folder).",
    )
    parser.add_argument(
        "--compare-story-folder",
        type=str,
        default=None,
        help="Optional second story folder for pairwise comparison.",
    )
    parser.add_argument(
        "--compare-stories-base-dir",
        type=str,
        default=None,
        help="Base directory for --compare-story-folder. Defaults to --stories-base-dir.",
    )
    parser.add_argument(
        "--compare-story-file",
        type=str,
        default=None,
        help="Optional specific text file for compared story (absolute path or relative to compared story folder).",
    )
    parser.add_argument(
        "--evaluation-focus",
        type=str,
        default="",
        help="Optional extra evaluator focus instructions.",
    )
    parser.add_argument(
        "--model-provider",
        type=str,
        choices=("openrouter", "google"),
        default="openrouter",
        help="LLM provider used for evaluation.",
    )
    parser.add_argument(
        "--model-id",
        type=str,
        default="openrouter/elephant-alpha",
        help="Model ID for selected provider.",
    )
    parser.add_argument(
        "--cred-file",
        type=str,
        default="cred.json",
        help="Path to credentials file.",
    )
    parser.add_argument(
        "--force-execute",
        action="store_true",
        help="Force a new evaluation instead of loading a cached result.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    with open(args.cred_file, "r", encoding="utf-8") as f:
        cred = json.load(f)

    llm = _create_llm(args.model_provider, args.model_id, cred)
    print(f"Model loaded successfully: provider={args.model_provider}, model={args.model_id}")

    story_directory = StoryDirectory.open(args.story_folder.strip(), args.stories_base_dir)
    story_path = story_directory.path

    story_text, story_source = _load_story_text(story_path, args.story_file)
    print(f"Using story source: {story_source}")

    if args.compare_story_folder:
        compare_base_dir = args.compare_stories_base_dir or args.stories_base_dir
        compare_story_directory = StoryDirectory.open(args.compare_story_folder.strip(), compare_base_dir)
        compare_story_path = compare_story_directory.path
        compare_story_text, compare_story_source = _load_story_text(compare_story_path, args.compare_story_file)
        print(f"Using compared story source: {compare_story_source}")

        comparison = story_pairwise_comparison(
            llm=llm,
            story_a_directory=story_directory,
            story_a_text=story_text,
            story_b_directory=compare_story_directory,
            story_b_text=compare_story_text,
            evaluation_focus=args.evaluation_focus,
            force_execute=args.force_execute,
        )

        winner_label = {
            "story_a": comparison.story_a_label,
            "story_b": comparison.story_b_label,
            "tie": "tie",
        }[comparison.overall_winner]

        print("Pairwise comparison complete.")
        print(f"Story A: {comparison.story_a_label}")
        print(f"Story B: {comparison.story_b_label}")
        print(f"Overall winner: {winner_label}")
        print(f"Confidence: {comparison.confidence:.2f}")
        print("Latest stage files: story_pairwise_comparison_XX.json and story_pairwise_comparison_XX.txt")
        return

    evaluation = story_rubric_evaluation(
        llm=llm,
        story_directory=story_directory,
        story_text=story_text,
        evaluation_focus=args.evaluation_focus,
        force_execute=args.force_execute,
    )

    print("Rubric evaluation complete.")
    print(f"Overall score: {evaluation.overall_score:.1f}/10")
    print(f"Prompt alignment: {evaluation.prompt_alignment.score}/10")
    print(f"Verdict: {evaluation.overall_verdict}")
    print("Latest stage files: story_rubric_evaluation_XX.json and story_rubric_evaluation_XX.txt")


if __name__ == "__main__":
    main()
