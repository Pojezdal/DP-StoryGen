from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

from final.llm.llm import GenerationParams
from final.llm.openrouter_llm import OpenRouterLLM
from final.pipeline_deepeval.custom_llm import CustomLLMEvaluatior
from final.utils.serialization import StoryDirectory


PREFERRED_STORY_FILES = (
	"final_story_simple.txt",
	"full_story.txt",
	"final_story.txt",
	"story.txt",
)


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


def _load_openrouter_keys(cred_file: str) -> list[str]:
	with open(cred_file, "r", encoding="utf-8") as f:
		cred = json.load(f)

	keys = cred.get("openrouter_api_key")
	if isinstance(keys, str):
		keys = [keys]
	if isinstance(keys, list) and keys:
		return keys

	# Backward compatibility with older key name.
	keys = cred.get("openrouter_api_keys")
	if isinstance(keys, str):
		keys = [keys]
	if isinstance(keys, list) and keys:
		return keys

	raise ValueError("Missing 'openrouter_api_key' in cred file")


def _import_pipeline_functions():
	from final.pipeline_deepeval.pipeline import evaluate_story, summarize_evaluation

	return evaluate_story, summarize_evaluation


def _build_plain_summary(summary: dict[str, Any]) -> str:
	overall_score_10 = summary.get("overall_score_10")
	lines: list[str] = ["DEEPEVAL RESULT"]
	if overall_score_10 is not None:
		lines.append(f"Overall deepeval score: {overall_score_10:.2f}/10")

	criteria = summary.get("criteria", {})
	if isinstance(criteria, dict) and criteria:
		lines.append("")
		lines.append("Criteria:")
		for name, data in criteria.items():
			score_10 = data.get("score_10") if isinstance(data, dict) else None
			reason = (data.get("reason") or "") if isinstance(data, dict) else ""
			if score_10 is None:
				lines.append(f"- {name}: N/A")
			else:
				lines.append(f"- {name}: {score_10:.2f}/10")
			if reason:
				lines.append(f"  reason: {reason}")

	return "\n".join(lines)


def _serialize_result_for_stage(result: Any) -> dict[str, Any] | str:
	if hasattr(result, "model_dump"):
		try:
			return result.model_dump(mode="json")
		except Exception:
			pass

	if hasattr(result, "dict"):
		try:
			return result.dict()
		except Exception:
			pass

	return str(result)


def parse_args() -> argparse.Namespace:
	parser = argparse.ArgumentParser(description="Run quick deepeval-based story evaluation.")
	parser.add_argument("--story-folder", type=str, required=True, help="Story folder name to evaluate.")
	parser.add_argument(
		"--stories-base-dir",
		type=str,
		default="stories",
		help="Base directory containing story folders.",
	)
	parser.add_argument(
		"--story-file",
		type=str,
		default=None,
		help="Optional specific story file (absolute path or relative to selected story folder).",
	)
	parser.add_argument(
		"--story-prompt",
		type=str,
		default=None,
		help="Optional prompt text to store if story_generation_prompt.txt is missing.",
	)
	parser.add_argument(
		"--model-id",
		type=str,
		default="nvidia/nemotron-3-super-120b-a12b:free",
		help="OpenRouter model ID used by deepeval judge.",
	)
	parser.add_argument(
		"--cred-file",
		type=str,
		default="cred.json",
		help="Path to credentials file.",
	)
	return parser.parse_args()


def main() -> None:
	args = parse_args()

	story_directory = StoryDirectory.open(args.story_folder.strip(), args.stories_base_dir)
	story_path = story_directory.path

	story_text, story_source = _load_story_text(story_path, args.story_file)
	print(f"Using story source: {story_source}")

	# The deepeval pipeline currently loads stage 'final_story', so save a simple stage snapshot.
	story_directory.save_stage(
		"final_story",
		data={"model": "manual", "generation_result": {"output": story_text}},
		plain_data=story_text,
	)

	if not story_directory.load_story_generation_prompt():
		if args.story_prompt and args.story_prompt.strip():
			story_directory.save_story_generation_prompt(args.story_prompt.strip())
			print("Stored story_generation_prompt.txt from --story-prompt.")
		else:
			story_directory.save_story_generation_prompt("N/A: prompt not provided for deepeval test run.")
			print("story_generation_prompt.txt was missing; stored placeholder prompt.")

	api_keys = _load_openrouter_keys(args.cred_file)
	llm_openrouter = OpenRouterLLM(model_id=args.model_id, api_keys=api_keys)
	custom_llm = CustomLLMEvaluatior(
		model=llm_openrouter,
		GenerationParams=GenerationParams(max_tokens=2048, temperature=0.7),
	)
 
	evaluate_story, summarize_evaluation = _import_pipeline_functions()
	result = evaluate_story(custom_llm, story_directory)
	print(f"Evaluation completed. {result}")
	summary = summarize_evaluation(result)
	plain_summary = _build_plain_summary(summary)

	story_directory.save_stage(
		"deepeval_evaluation",
		data={
			"model": args.model_id,
			"story_source": story_source,
			"summary": summary,
			"raw_result": _serialize_result_for_stage(result),
		},
		plain_data=plain_summary,
	)

	print("Deepeval finished.")
	overall_score_10 = summary.get("overall_score_10")
	if overall_score_10 is not None:
		print(f"Overall deepeval score: {overall_score_10:.2f}/10")

	criteria = summary.get("criteria", {})
	for name, data in criteria.items():
		score_10 = data.get("score_10")
		reason = data.get("reason") or ""
		if score_10 is None:
			print(f"- {name}: N/A")
		else:
			print(f"- {name}: {score_10:.2f}/10")
		if reason:
			print(f"  reason: {reason}")

	print("Latest stage files: deepeval_evaluation_XX.json and deepeval_evaluation_XX.txt")


if __name__ == "__main__":
    main()