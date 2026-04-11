from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

import numpy as np
import torch
from sentence_transformers import SentenceTransformer


INSTRUCTION = (
    "Given a detective story, retrieve other stories with similar plot structure, "
    "events, and character roles."
)


def _token_length(model: SentenceTransformer, text: str) -> int:
    tokens = model.tokenize([text])
    return int(tokens["input_ids"].shape[1])


def _split_text_for_chunks(text: str) -> list[str]:
    compact = re.sub(r"\s+", " ", text).strip()
    if not compact:
        return []
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+", compact) if s.strip()]


def split_text_into_chunks(text: str, max_chunk_size: int, model: SentenceTransformer) -> list[str]:
    units = _split_text_for_chunks(text)
    if not units:
        return []

    chunks: list[str] = []
    current: list[str] = []
    current_size = 0

    for unit in units:
        unit_size = _token_length(model, unit)

        if unit_size > max_chunk_size:
            words = unit.split()
            partial: list[str] = []
            for word in words:
                candidate = " ".join(partial + [word])
                candidate_size = _token_length(model, candidate)
                if candidate_size <= max_chunk_size:
                    partial.append(word)
                else:
                    if partial:
                        if current:
                            chunks.append(" ".join(current))
                            current = []
                            current_size = 0
                        chunks.append(" ".join(partial))
                        partial = [word]
                    else:
                        if current:
                            chunks.append(" ".join(current))
                            current = []
                            current_size = 0
                        chunks.append(word)
                        partial = []
            if partial:
                if current:
                    chunks.append(" ".join(current))
                    current = []
                    current_size = 0
                chunks.append(" ".join(partial))
            continue

        if current_size + unit_size <= max_chunk_size:
            current.append(unit)
            current_size += unit_size
        else:
            if current:
                chunks.append(" ".join(current))
            current = [unit]
            current_size = unit_size

    if current:
        chunks.append(" ".join(current))

    return chunks


def _load_jsonl_by_qid(path: Path) -> dict[str, dict[str, Any]]:
    records: dict[str, dict[str, Any]] = {}
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            item = json.loads(line)
            qid = item.get("qid")
            if qid:
                records[qid] = item
    return records


def _build_qid_index(stories_cfg: dict[str, dict[str, int]]) -> dict[int, str]:
    by_index: dict[int, str] = {}
    for qid, info in stories_cfg.items():
        idx = int(info["index"])
        by_index[idx] = qid
    return by_index


def evaluate_story(
    model: SentenceTransformer,
    story_text: str,
    embeddings_mean: torch.Tensor,
    embeddings_all: torch.Tensor,
    stories_cfg: dict[str, dict[str, int]],
    metadata_by_qid: dict[str, dict[str, Any]],
    max_seq_length: int,
    top_k: int,
) -> dict[str, Any]:
    chunks = split_text_into_chunks(story_text, max_seq_length, model)
    if not chunks:
        raise ValueError("Story text is empty after preprocessing.")

    chunk_queries = [f"Instruct: {INSTRUCTION}\nQuery: {chunk}" for chunk in chunks]
    story_embeddings_np = model.encode(chunk_queries, normalize_embeddings=True, convert_to_numpy=True)
    story_embeddings = torch.from_numpy(story_embeddings_np).float()
    story_mean_embedding = story_embeddings.mean(dim=0, keepdim=True)

    mean_similarity = model.similarity(story_mean_embedding, embeddings_mean).squeeze(0)
    k_mean = min(top_k, int(mean_similarity.shape[0]))
    top_mean_values, top_mean_indices = torch.topk(mean_similarity, k=k_mean)

    intra_similarity = model.similarity(embeddings_mean, embeddings_mean)
    intra_similarity.fill_diagonal_(0)

    k_percentile = min(10, max(1, int(intra_similarity.shape[1] - 1)))
    intra_topk_mean = intra_similarity.topk(k=k_percentile, dim=1).values.mean(dim=1)
    story_topk_mean = top_mean_values[:k_percentile].mean().item()
    percentile_vs_dataset = float((intra_topk_mean <= story_topk_mean).float().mean().item() * 100.0)

    chunk_to_dataset = model.similarity(story_embeddings, embeddings_all).max(dim=1).values

    qid_by_index = _build_qid_index(stories_cfg)
    nearest_mean: list[dict[str, Any]] = []
    for rank, (score, idx_tensor) in enumerate(zip(top_mean_values.tolist(), top_mean_indices.tolist()), start=1):
        qid = qid_by_index.get(int(idx_tensor), "")
        meta = metadata_by_qid.get(qid, {})
        nearest_mean.append(
            {
                "rank": rank,
                "qid": qid,
                "title": meta.get("title", "Unknown"),
                "article": meta.get("article", ""),
                "similarity": float(score),
            }
        )

    all_story_scores: list[tuple[str, float]] = []
    for qid, info in stories_cfg.items():
        offset = int(info["chunk_offset"])
        count = int(info["chunk_count"])
        candidate_chunks = embeddings_all[offset : offset + count]
        sim = model.similarity(story_embeddings, candidate_chunks).max(dim=1).values
        k_local = min(3, int(sim.shape[0]))
        score = float(sim.topk(k=k_local).values.mean().item())
        all_story_scores.append((qid, score))

    all_story_scores.sort(key=lambda x: x[1], reverse=True)
    nearest_all = []
    for rank, (qid, score) in enumerate(all_story_scores[:k_mean], start=1):
        meta = metadata_by_qid.get(qid, {})
        nearest_all.append(
            {
                "rank": rank,
                "qid": qid,
                "title": meta.get("title", "Unknown"),
                "article": meta.get("article", ""),
                "similarity": float(score),
            }
        )

    return {
        "metrics": {
            "chunk_count": len(chunks),
            "mean_similarity_max": float(mean_similarity.max().item()),
            "mean_similarity_mean": float(mean_similarity.mean().item()),
            "mean_similarity_top_k_mean": float(top_mean_values.mean().item()),
            "chunk_coverage_mean": float(chunk_to_dataset.mean().item()),
            "chunk_coverage_min": float(chunk_to_dataset.min().item()),
            "chunk_coverage_max": float(chunk_to_dataset.max().item()),
            "percentile_vs_dataset_top10_mean": percentile_vs_dataset,
        },
        "nearest_by_mean_embedding": nearest_mean,
        "nearest_by_chunk_alignment": nearest_all,
    }


def parse_args() -> argparse.Namespace:
    repo_root = Path(__file__).resolve().parents[2]

    parser = argparse.ArgumentParser(
        description="Evaluate a generated story against the Wikipedia literary dataset embeddings."
    )
    parser.add_argument(
        "--story",
        type=Path,
        default=repo_root / "src" / "stories" / "test" / "final_story.txt",
        help="Path to generated story text file.",
    )
    parser.add_argument(
        "--dataset-dir",
        type=Path,
        default=repo_root / "datasets" / "wikidata" / "literary",
        help="Directory containing data.jsonl, embedding_config.json, embeddings_mean.npy and embeddings_all.npy.",
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=10,
        help="How many nearest reference stories to include.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Output JSON path. Default: alongside story as evaluation_wikipedia.json.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    if args.top_k < 1:
        raise ValueError("--top-k must be >= 1")

    story_path = args.story.resolve()
    dataset_dir = args.dataset_dir.resolve()

    config_path = dataset_dir / "embedding_config.json"
    embeddings_mean_path = dataset_dir / "embeddings_mean.npy"
    embeddings_all_path = dataset_dir / "embeddings_all.npy"
    data_jsonl_path = dataset_dir / "data.jsonl"

    for required in [story_path, config_path, embeddings_mean_path, embeddings_all_path, data_jsonl_path]:
        if not required.exists():
            raise FileNotFoundError(f"Required file does not exist: {required}")

    with config_path.open("r", encoding="utf-8") as handle:
        config = json.load(handle)

    model_name = config.get("model_name", "intfloat/multilingual-e5-large-instruct")
    max_seq_length = int(config.get("max_seq_length", 512))
    stories_cfg = config.get("stories", {})
    if not isinstance(stories_cfg, dict) or not stories_cfg:
        raise ValueError("Invalid or empty 'stories' section in embedding_config.json")

    story_text = story_path.read_text(encoding="utf-8")
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
        "story_path": str(story_path),
        "dataset_dir": str(dataset_dir),
        "model_name": model_name,
        "max_seq_length": max_seq_length,
        **result,
    }

    output_path = args.output.resolve() if args.output else story_path.with_name("evaluation_wikipedia.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"Evaluation report saved to: {output_path}")
    print(f"Top reference story (mean): {report['nearest_by_mean_embedding'][0]['title']}")
    print(
        "Percentile vs dataset (top-10 mean): "
        f"{report['metrics']['percentile_vs_dataset_top10_mean']:.2f}%"
    )


if __name__ == "__main__":
    main()
