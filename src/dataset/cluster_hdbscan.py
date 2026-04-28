import argparse
import csv
import json
from pathlib import Path

import hdbscan
import numpy as np
from sklearn.metrics import pairwise_distances
from sklearn.preprocessing import normalize
from umap import UMAP


def parse_args() -> argparse.Namespace:
    root_dir = Path(__file__).resolve().parents[2]
    default_data_dir = root_dir / "datasets" / "wikidata" / "literary"

    parser = argparse.ArgumentParser(
        description="Run HDBSCAN clustering over mean story embeddings."
    )
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=default_data_dir,
        help="Directory containing embeddings_mean.npy and embedding_config.json.",
    )
    parser.add_argument(
        "--output-csv",
        type=Path,
        default=None,
        help="Output CSV for story-level cluster assignments.",
    )
    parser.add_argument(
        "--output-summary",
        type=Path,
        default=None,
        help="Output JSON file with clustering summary.",
    )
    parser.add_argument(
        "--input-clusters-summary",
        type=Path,
        default=None,
        help="Existing summary JSON produced by this script. Used for split mode.",
    )
    parser.add_argument(
        "--split-cluster-id",
        type=int,
        default=None,
        help="Cluster id from input CSV to split into subclusters.",
    )
    parser.add_argument(
        "--keep-split-noise-in-parent",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="In split mode, keep subcluster noise points in the original parent cluster.",
    )

    parser.add_argument(
        "--use-umap",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Apply UMAP dimensionality reduction before HDBSCAN.",
    )
    parser.add_argument(
        "--l2-normalize",
        action=argparse.BooleanOptionalAction,
        default=False,
        help="Apply row-wise L2 normalization to mean embeddings before clustering.",
    )
    parser.add_argument("--umap-n-components", type=int, default=15)
    parser.add_argument("--umap-n-neighbors", type=int, default=30)
    parser.add_argument("--umap-min-dist", type=float, default=0.0)
    parser.add_argument("--umap-metric", type=str, default="cosine")
    parser.add_argument("--random-state", type=int, default=42)

    parser.add_argument("--min-cluster-size", type=int, default=15)
    parser.add_argument("--min-samples", type=int, default=None)
    parser.add_argument(
        "--hdbscan-metric",
        type=str,
        default=None,
        help="Distance metric for HDBSCAN. Defaults to euclidean with UMAP, otherwise cosine.",
    )
    parser.add_argument(
        "--cluster-selection-method",
        type=str,
        default="eom",
        choices=["eom", "leaf"],
    )

    return parser.parse_args()


def load_qids_from_config(config_path: Path) -> list[str]:
    with config_path.open("r", encoding="utf-8") as handle:
        config = json.load(handle)

    stories = config.get("stories", {})
    ordered = sorted(stories.items(), key=lambda item: item[1]["index"])
    return [qid for qid, _ in ordered]


def load_story_metadata(data_path: Path) -> dict[str, dict]:
    metadata = {}
    with data_path.open("r", encoding="utf-8") as handle:
        for line in handle:
            row = json.loads(line)
            metadata[row["qid"]] = {
                "title": row.get("title", ""),
                "pubDate": row.get("pubDate", ""),
                "authors": row.get("authors", []),
                "plot": row.get("plot", ""),
            }
    return metadata


def load_existing_persistence(summary_path: Path) -> dict[str, float]:
    if not summary_path.exists():
        return {}

    with summary_path.open("r", encoding="utf-8") as handle:
        summary = json.load(handle)

    result = summary.get("result", {})
    persistence = result.get("cluster_persistence", {})
    if not isinstance(persistence, dict):
        return {}

    return {str(key): float(value) for key, value in persistence.items()}


def load_existing_summary(summary_path: Path) -> dict:
    with summary_path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def resolve_path(base_path: Path, candidate: str) -> Path:
    path = Path(candidate)
    return path


def load_existing_assignments(summary_path: Path) -> dict[str, dict]:
    summary = load_existing_summary(summary_path)
    output_csv_value = summary.get("outputs", {}).get("cluster_csv")
    if not output_csv_value:
        raise ValueError(f"Summary JSON does not contain outputs.cluster_csv: {summary_path}")

    input_csv = resolve_path(summary_path, output_csv_value)
    assignments = {}
    with input_csv.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        fieldnames = reader.fieldnames or []
        cluster_key = "cluster_id" if "cluster_id" in fieldnames else "cluster"
        has_path = "cluster_path" in fieldnames

        for row in reader:
            qid = row.get("qid", "")
            if not qid:
                continue
            cluster_id = int(row.get(cluster_key, -1))
            probability_raw = row.get("probability", "0.0")
            probability = float(probability_raw) if probability_raw else 0.0
            cluster_path = row.get("cluster_path", "") if has_path else ""
            if not cluster_path:
                cluster_path = str(cluster_id)

            assignments[qid] = {
                "cluster_id": cluster_id,
                "cluster_path": cluster_path,
                "probability": probability,
            }

    return assignments


def run_clustering(
    embeddings: np.ndarray,
    args: argparse.Namespace,
) -> tuple[np.ndarray, hdbscan.HDBSCAN, np.ndarray, str, str]:
    features = np.asarray(embeddings, dtype=np.float64)
    if args.l2_normalize:
        features = normalize(features, norm="l2", axis=1)

    if args.use_umap:
        reducer = UMAP(
            n_components=args.umap_n_components,
            n_neighbors=args.umap_n_neighbors,
            min_dist=args.umap_min_dist,
            metric=args.umap_metric,
            random_state=args.random_state,
        )
        features = reducer.fit_transform(features)

    requested_metric = args.hdbscan_metric
    if requested_metric is None:
        requested_metric = "euclidean" if args.use_umap else "cosine"

    fit_data = features
    effective_metric = requested_metric
    clusterer_kwargs = {}

    if requested_metric.lower() == "cosine":
        fit_data = pairwise_distances(features, metric="cosine")
        effective_metric = "precomputed"
        clusterer_kwargs["algorithm"] = "generic"

    clusterer = hdbscan.HDBSCAN(
        min_cluster_size=args.min_cluster_size,
        min_samples=args.min_samples,
        metric=effective_metric,
        cluster_selection_method=args.cluster_selection_method,
        prediction_data=True,
        **clusterer_kwargs,
    )


    fit_data = np.asarray(fit_data, dtype=np.float64)
    labels = clusterer.fit_predict(fit_data)
    return features, clusterer, labels, requested_metric, effective_metric


def assignments_from_labels(
    qids: list[str],
    labels: np.ndarray,
    probabilities: np.ndarray,
) -> dict[str, dict]:
    assignments = {}
    for qid, label, prob in zip(qids, labels, probabilities):
        cluster_id = int(label)
        assignments[qid] = {
            "cluster_id": cluster_id,
            "cluster_path": str(cluster_id),
            "probability": float(prob),
        }
    return assignments


def split_cluster_assignments(
    qids: list[str],
    assignments: dict[str, dict],
    split_cluster_id: int,
    sublabels: np.ndarray,
    subprobabilities: np.ndarray,
    keep_split_noise_in_parent: bool,
) -> dict[str, dict]:
    target_qids = [qid for qid in qids if assignments[qid]["cluster_id"] == split_cluster_id]
    if len(target_qids) != len(sublabels):
        raise ValueError(
            "Mismatch between split target size and generated sublabels: "
            f"{len(target_qids)} vs {len(sublabels)}"
        )

    used_cluster_ids = [a["cluster_id"] for a in assignments.values() if a["cluster_id"] >= 0]
    next_cluster_id = (max(used_cluster_ids) + 1) if used_cluster_ids else 0

    local_labels = sorted(set(int(x) for x in sublabels if int(x) >= 0))
    local_to_global = {label: next_cluster_id + idx for idx, label in enumerate(local_labels)}

    for qid, local_label, local_prob in zip(target_qids, sublabels, subprobabilities):
        local_label = int(local_label)
        local_prob = float(local_prob)
        parent_path = assignments[qid]["cluster_path"]

        if local_label < 0:
            if keep_split_noise_in_parent:
                assignments[qid]["probability"] = local_prob
            else:
                assignments[qid] = {
                    "cluster_id": -1,
                    "cluster_path": "-1",
                    "probability": local_prob,
                }
            continue

        assignments[qid] = {
            "cluster_id": int(local_to_global[local_label]),
            "cluster_path": f"{parent_path}.{local_label}",
            "probability": local_prob,
        }

    return assignments


def summarize_hierarchical_clusters(assignments: dict[str, dict]) -> tuple[dict[str, int], int]:
    cluster_sizes: dict[str, int] = {}
    noise_count = 0

    for assignment in assignments.values():
        cluster_path = str(assignment["cluster_path"])
        cluster_sizes[cluster_path] = cluster_sizes.get(cluster_path, 0) + 1
        if int(assignment["cluster_id"]) == -1:
            noise_count += 1

    hierarchical_sizes = {
        cluster_path: size
        for cluster_path, size in sorted(cluster_sizes.items(), key=lambda item: item[0])
        if cluster_path != "-1"
    }

    return hierarchical_sizes, noise_count


def write_outputs(
    qids: list[str],
    metadata: dict[str, dict],
    assignments: dict[str, dict],
    args: argparse.Namespace,
    feature_shape: tuple[int, int],
    requested_metric: str,
    effective_metric: str,
    mode: str,
    split_info: dict | None = None,
    cluster_persistence: dict | None = None,
    prior_cluster_persistence: dict | None = None,
) -> tuple[Path, Path]:
    data_dir = args.data_dir
    output_csv = args.output_csv or data_dir / "hdbscan_mean_clusters.csv"
    output_summary = args.output_summary or data_dir / "hdbscan_mean_summary.json"
    output_csv.parent.mkdir(parents=True, exist_ok=True)

    rows = []
    for qid in qids:
        record = metadata.get(qid, {})
        assign = assignments[qid]
        rows.append(
            {
                "qid": qid,
                "title": record.get("title", ""),
                "pubDate": record.get("pubDate", ""),
                "authors": record.get("authors", []),
                "plot": record.get("plot", ""),
                "cluster_id": int(assign["cluster_id"]),
                "cluster_path": assign["cluster_path"],
                "cluster": int(assign["cluster_id"]),
                "probability": float(assign["probability"]),
            }
        )

    rows.sort(key=lambda r: (r["cluster_id"], r["qid"]))

    with output_csv.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "index",
                "qid",
                "title",
                "pubDate",
                "authors",
                "plot",
                "cluster_id",
                "cluster_path",
                "cluster",
                "probability",
            ],
        )
        writer.writeheader()
        for idx, row in enumerate(rows):
            writer.writerow({"index": idx, **row})

    labels = np.array([assignments[qid]["cluster_id"] for qid in qids], dtype=int)
    cluster_sizes, noise_count = summarize_hierarchical_clusters(assignments)

    summary = {
        "mode": mode,
        "input": {
            "data_dir": str(data_dir),
            "num_samples": int(len(labels)),
            "feature_shape": [int(feature_shape[0]), int(feature_shape[1])],
        },
        "parameters": {
            "l2_normalize": args.l2_normalize,
            "use_umap": args.use_umap,
            "umap_n_components": args.umap_n_components,
            "umap_n_neighbors": args.umap_n_neighbors,
            "umap_min_dist": args.umap_min_dist,
            "umap_metric": args.umap_metric,
            "min_cluster_size": args.min_cluster_size,
            "min_samples": args.min_samples,
            "hdbscan_metric": requested_metric,
            "hdbscan_effective_metric": effective_metric,
            "cluster_selection_method": args.cluster_selection_method,
            "keep_split_noise_in_parent": args.keep_split_noise_in_parent,
        },
        "result": {
            "num_clusters": int(len(cluster_sizes)),
            "noise_count": noise_count,
            "noise_ratio": float(noise_count / len(labels)) if len(labels) else 0.0,
            "cluster_sizes": cluster_sizes,
            "cluster_persistence": {
                **(prior_cluster_persistence or {}),
                **(cluster_persistence or {}),
            },
        },
        "split": split_info or {},
        "outputs": {
            "cluster_csv": str(output_csv),
            "summary_json": str(output_summary),
        },
    }

    with output_summary.open("w", encoding="utf-8") as handle:
        json.dump(summary, handle, indent=2)

    return output_csv, output_summary


def main() -> None:
    args = parse_args()

    split_mode = args.input_clusters_summary is not None or args.split_cluster_id is not None
    if split_mode and (args.input_clusters_summary is None or args.split_cluster_id is None):
        raise ValueError(
            "Split mode requires both --input-clusters-summary and --split-cluster-id."
        )

    if split_mode:
        input_summary = load_existing_summary(args.input_clusters_summary)
        data_dir_value = input_summary.get("input", {}).get("data_dir")
        if not data_dir_value:
            raise ValueError(
                f"Summary JSON does not contain input.data_dir: {args.input_clusters_summary}"
            )
        data_dir = Path(data_dir_value)
    else:
        data_dir = args.data_dir

    mean_path = data_dir / "embeddings_mean.npy"
    config_path = data_dir / "embedding_config.json"
    data_jsonl_path = data_dir / "data.jsonl"

    embeddings_mean = np.load(mean_path)
    qids = load_qids_from_config(config_path)
    metadata = load_story_metadata(data_jsonl_path)

    if len(qids) != embeddings_mean.shape[0]:
        raise ValueError(
            "Mismatch between embeddings_mean rows and embedding_config story indexes: "
            f"{embeddings_mean.shape[0]} vs {len(qids)}"
        )

    if not split_mode:
        prior_persistence = load_existing_persistence(
            args.output_summary or (data_dir / "hdbscan_mean_summary.json")
        )
        features, clusterer, labels, requested_metric, effective_metric = run_clustering(
            embeddings_mean, args
        )
        probabilities = clusterer.probabilities_
        assignments = assignments_from_labels(qids, labels, probabilities)

        cluster_ids = np.unique(labels[labels >= 0])
        persistence_values = getattr(clusterer, "cluster_persistence_", [])
        persistence = {}
        for cluster_id, value in zip(cluster_ids, persistence_values):
            cluster_path = next(
                assignments[qid]["cluster_path"]
                for qid in qids
                if assignments[qid]["cluster_id"] == int(cluster_id)
            )
            persistence[cluster_path] = float(value)

        output_csv, output_summary = write_outputs(
            qids=qids,
            metadata=metadata,
            assignments=assignments,
            args=args,
            feature_shape=features.shape,
            requested_metric=requested_metric,
            effective_metric=effective_metric,
            mode="initial",
            split_info=None,
            cluster_persistence=persistence,
            prior_cluster_persistence=prior_persistence,
        )
        final_labels = np.array([assignments[qid]["cluster_id"] for qid in qids], dtype=int)
    else:
        prior_persistence = load_existing_persistence(args.input_clusters_summary)
        existing_assignments = load_existing_assignments(args.input_clusters_summary)
        assignments = {
            qid: existing_assignments.get(
                qid,
                {
                    "cluster_id": -1,
                    "cluster_path": "-1",
                    "probability": 0.0,
                },
            )
            for qid in qids
        }

        split_cluster_id = int(args.split_cluster_id)
        split_indices = [
            idx for idx, qid in enumerate(qids) if assignments[qid]["cluster_id"] == split_cluster_id
        ]
        if not split_indices:
            raise ValueError(
                f"Cluster id {split_cluster_id} not found in input assignments."
            )

        split_embeddings = embeddings_mean[split_indices]
        features, clusterer, sublabels, requested_metric, effective_metric = run_clustering(
            split_embeddings, args
        )
        subprobabilities = clusterer.probabilities_

        local_cluster_ids = np.unique(sublabels[sublabels >= 0])
        local_persistence_values = getattr(clusterer, "cluster_persistence_", [])
        split_parent_path = assignments[qids[split_indices[0]]]["cluster_path"]
        split_persistence = {
            f"{split_parent_path}.{int(local_cluster_id)}": float(value)
            for local_cluster_id, value in zip(local_cluster_ids, local_persistence_values)
        }

        assignments = split_cluster_assignments(
            qids=qids,
            assignments=assignments,
            split_cluster_id=split_cluster_id,
            sublabels=sublabels,
            subprobabilities=subprobabilities,
            keep_split_noise_in_parent=args.keep_split_noise_in_parent,
        )

        split_info = {
            "input_clusters_summary": str(args.input_clusters_summary),
            "split_cluster_id": split_cluster_id,
            "split_cluster_size": len(split_indices),
            "subclusters_found": int(len(np.unique(sublabels[sublabels >= 0]))),
            "subcluster_noise": int(np.sum(sublabels == -1)),
        }

        output_csv, output_summary = write_outputs(
            qids=qids,
            metadata=metadata,
            assignments=assignments,
            args=args,
            feature_shape=features.shape,
            requested_metric=requested_metric,
            effective_metric=effective_metric,
            mode="split",
            split_info=split_info,
            cluster_persistence=split_persistence,
            prior_cluster_persistence=prior_persistence,
        )
        final_labels = np.array([assignments[qid]["cluster_id"] for qid in qids], dtype=int)

    num_clusters = len(np.unique(final_labels[final_labels >= 0]))
    noise_count = int(np.sum(final_labels == -1))
    print(
        f"Done. Found {num_clusters} clusters with {noise_count} noise samples out of {len(final_labels)} stories."
    )
    print(f"Cluster assignments: {output_csv}")
    print(f"Summary: {output_summary}")


if __name__ == "__main__":
    main()
