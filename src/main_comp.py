"""Folder-level story evaluator entrypoint.

Run examples:
  python src/main_comp.py --story-dir src/stories/test
  python src/main_comp.py --story-dir src/stories/2026-03-29_202547_story --story-file final_story.txt
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

import numpy as np
import torch
from sentence_transformers import SentenceTransformer

from dataset.evaluate_test_story import _load_jsonl_by_qid, evaluate_story


PREFERRED_STORY_FILES = (
    "final_story.txt",
    "full_story.txt",
    "alt_final_story_compiled.txt",
)


def _chapter_sort_key(path: Path) -> tuple[int, str]:
    match = re.search(r"chapter_(\d+)", path.stem.lower())
    if match:
        return (int(match.group(1)), path.name)
    return (10**9, path.name)


def _resolve_story_file(story_dir: Path, story_file_arg: str | None) -> Path | None:
    if story_file_arg:
        candidate = Path(story_file_arg)
        if not candidate.is_absolute():
            candidate = story_dir / candidate
        if not candidate.exists() or not candidate.is_file():
            raise FileNotFoundError(f"Requested story file does not exist: {candidate}")
        return candidate

    for name in PREFERRED_STORY_FILES:
        candidate = story_dir / name
        if candidate.exists() and candidate.is_file():
            return candidate

    return None


def _load_story_text(story_dir: Path, story_file: Path | None) -> tuple[str, dict[str, Any]]:
    if story_file is not None:
        text = story_file.read_text(encoding="utf-8")
        if not text.strip():
            raise ValueError(f"Story file is empty: {story_file}")
        return text, {"story_path": str(story_file), "story_source": "single_file"}

    chapter_files = sorted(story_dir.glob("chapter_*.txt"), key=_chapter_sort_key)
    if not chapter_files:
        txt_files = sorted(story_dir.glob("*.txt"))
        if not txt_files:
            raise FileNotFoundError(
                f"No story text found in {story_dir}. Provide --story-file or include final_story.txt/chapter_*.txt."
            )

        story_like = [p for p in txt_files if "story" in p.stem.lower()]
        chosen = max(story_like or txt_files, key=lambda p: p.stat().st_size)
        text = chosen.read_text(encoding="utf-8")
        if not text.strip():
            raise ValueError(f"Detected story file is empty: {chosen}")
        return text, {"story_path": str(chosen), "story_source": "auto_detected_single_file"}

    chapter_texts: list[str] = []
    chapter_names: list[str] = []
    for chapter_path in chapter_files:
        content = chapter_path.read_text(encoding="utf-8").strip()
        if content:
            chapter_texts.append(content)
            chapter_names.append(chapter_path.name)

    if not chapter_texts:
        raise ValueError(f"Detected chapter files in {story_dir}, but all are empty.")

    merged_text = "\n\n".join(chapter_texts)
    return merged_text, {
        "story_path": None,
        "story_source": "compiled_chapters",
        "chapter_files": chapter_names,
    }


def parse_args() -> argparse.Namespace:
    repo_root = Path(__file__).resolve().parents[1]

    parser = argparse.ArgumentParser(
        description="Evaluate generated story outputs in an arbitrary story folder against Wikipedia dataset embeddings."
    )
    parser.add_argument(
        "--story-dir",
        type=Path,
        required=True,
        help="Folder containing generated story outputs (for example src/stories/test).",
    )
    parser.add_argument(
        "--story-file",
        type=str,
        default=None,
        help="Specific story text file path (absolute or relative to --story-dir).",
    )
    parser.add_argument(
        "--dataset-dir",
        type=Path,
        default=repo_root / "datasets" / "wikidata" / "literary",
        help="Directory with embedding_config.json, embeddings_mean.npy, embeddings_all.npy, and data.jsonl.",
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=10,
        help="How many nearest reference stories to include.",
    )
    parser.add_argument(
        "--output-name",
        type=str,
        default="evaluation_wikipedia.json",
        help="Output file name to be written into --story-dir.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    if args.top_k < 1:
        raise ValueError("--top-k must be >= 1")

    story_dir = args.story_dir.resolve()
    dataset_dir = args.dataset_dir.resolve()

    if not story_dir.exists() or not story_dir.is_dir():
        raise NotADirectoryError(f"Story directory does not exist or is not a directory: {story_dir}")

    config_path = dataset_dir / "embedding_config.json"
    embeddings_mean_path = dataset_dir / "embeddings_mean.npy"
    embeddings_all_path = dataset_dir / "embeddings_all.npy"
    data_jsonl_path = dataset_dir / "data.jsonl"

    for required in [config_path, embeddings_mean_path, embeddings_all_path, data_jsonl_path]:
        if not required.exists():
            raise FileNotFoundError(f"Required dataset file does not exist: {required}")

    story_file = _resolve_story_file(story_dir, args.story_file)
    story_text, story_meta = _load_story_text(story_dir, story_file)

    with config_path.open("r", encoding="utf-8") as handle:
        config = json.load(handle)

    model_name = config.get("model_name", "intfloat/multilingual-e5-large-instruct")
    max_seq_length = int(config.get("max_seq_length", 512))
    stories_cfg = config.get("stories", {})
    if not isinstance(stories_cfg, dict) or not stories_cfg:
        raise ValueError("Invalid or empty 'stories' section in embedding_config.json")

    metadata_by_qid = _load_jsonl_by_qid(data_jsonl_path)
    embeddings_mean = torch.from_numpy(np.load(embeddings_mean_path)).float()
    embeddings_all = torch.from_numpy(np.load(embeddings_all_path)).float()

    model = SentenceTransformer(model_name)

    result = evaluate_story(
        model=model,
        story_text=story_text,
        embeddings_mean=embeddings_mean,
        embeddings_all=embeddings_all,
        stories_cfg=stories_cfg,
        metadata_by_qid=metadata_by_qid,
        max_seq_length=max_seq_length,
        top_k=args.top_k,
    )

    report = {
        "story_dir": str(story_dir),
        "dataset_dir": str(dataset_dir),
        "model_name": model_name,
        "max_seq_length": max_seq_length,
        **story_meta,
        **result,
    }

    output_path = story_dir / args.output_name
    output_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"Evaluation report saved to: {output_path}")
    print(f"Story source: {report['story_source']}")
    print(f"Top reference story (mean): {report['nearest_by_mean_embedding'][0]['title']}")
    print(
        "Percentile vs dataset (top-10 mean): "
        f"{report['metrics']['percentile_vs_dataset_top10_mean']:.2f}%"
    )


if __name__ == "__main__":
    main()
