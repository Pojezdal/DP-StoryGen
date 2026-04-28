import argparse
import csv
import itertools
import json
from pathlib import Path
from types import SimpleNamespace

import numpy as np

from cluster_hdbscan import run_clustering


def parse_int_list(text: str) -> list[int]:
    return [int(x.strip()) for x in text.split(",") if x.strip()]


def parse_float_list(text: str) -> list[float]:
    return [float(x.strip()) for x in text.split(",") if x.strip()]


def parse_str_list(text: str) -> list[str]:
    return [x.strip() for x in text.split(",") if x.strip()]


def build_parser() -> argparse.ArgumentParser:
    root_dir = Path(__file__).resolve().parents[2]
    default_data_dir = root_dir / "datasets" / "wikidata" / "literary"

    parser = argparse.ArgumentParser(
        description="Short grid search for UMAP + HDBSCAN settings."
    )
    parser.add_argument("--data-dir", type=Path, default=default_data_dir)
    parser.add_argument(
        "--output-csv",
        type=Path,
        default=None,
        help="Leaderboard CSV output path.",
    )
    parser.add_argument(
        "--output-json",
        type=Path,
        default=None,
        help="Full results JSON output path.",
    )

    parser.add_argument(
        "--l2-normalize",
        action=argparse.BooleanOptionalAction,
        default=True,
    )
    parser.add_argument(
        "--use-umap",
        action=argparse.BooleanOptionalAction,
        default=True,
    )
    parser.add_argument("--umap-metric", type=str, default="cosine")
    parser.add_argument("--hdbscan-metric", type=str, default=None)
    parser.add_argument("--random-state", type=int, default=42)

    parser.add_argument("--umap-n-components-grid", type=parse_int_list, default=[10, 15])
    parser.add_argument("--umap-n-neighbors-grid", type=parse_int_list, default=[10, 15, 25])
    parser.add_argument("--umap-min-dist-grid", type=parse_float_list, default=[0.0, 0.1])
    parser.add_argument("--min-cluster-size-grid", type=parse_int_list, default=[10, 15, 25])
    parser.add_argument("--min-samples-grid", type=parse_int_list, default=[3, 5, 8])
    parser.add_argument(
        "--cluster-selection-method-grid",
        type=parse_str_list,
        default=["leaf", "eom"],
    )

    parser.add_argument(
        "--min-clusters",
        type=int,
        default=8,
        help="Runs below this cluster count are penalized in ranking.",
    )
    parser.add_argument(
        "--target-clusters",
        type=int,
        default=12,
        help="Cluster count where cluster-score saturates.",
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=10,
        help="How many top-ranked runs to print.",
    )

    return parser


def score_run(noise_ratio: float, num_clusters: int, min_clusters: int, target_clusters: int) -> float:
    coverage_score = 1.0 - noise_ratio
    cluster_score = min(float(num_clusters) / float(target_clusters), 1.0)
    score = 0.65 * coverage_score + 0.35 * cluster_score
    if num_clusters < min_clusters:
        score -= 0.25
    return score


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    data_dir = args.data_dir
    embeddings_mean = np.load(data_dir / "embeddings_mean.npy")

    rows = []
    combinations = list(
        itertools.product(
            args.umap_n_components_grid,
            args.umap_n_neighbors_grid,
            args.umap_min_dist_grid,
            args.min_cluster_size_grid,
            args.min_samples_grid,
            args.cluster_selection_method_grid,
        )
    )

    for (
        umap_n_components,
        umap_n_neighbors,
        umap_min_dist,
        min_cluster_size,
        min_samples,
        cluster_selection_method,
    ) in combinations:
        run_args = SimpleNamespace(
            l2_normalize=args.l2_normalize,
            use_umap=args.use_umap,
            umap_n_components=umap_n_components,
            umap_n_neighbors=umap_n_neighbors,
            umap_min_dist=umap_min_dist,
            umap_metric=args.umap_metric,
            random_state=args.random_state,
            min_cluster_size=min_cluster_size,
            min_samples=min_samples,
            hdbscan_metric=args.hdbscan_metric,
            cluster_selection_method=cluster_selection_method,
        )

        try:
            _, clusterer, labels, requested_metric, effective_metric = run_clustering(
                embeddings_mean, run_args
            )
            num_samples = int(len(labels))
            noise_count = int(np.sum(labels == -1))
            noise_ratio = float(noise_count / num_samples) if num_samples else 1.0
            num_clusters = int(len(np.unique(labels[labels >= 0])))
            largest_cluster = 0
            if num_clusters > 0:
                _, counts = np.unique(labels[labels >= 0], return_counts=True)
                largest_cluster = int(np.max(counts))
            largest_cluster_ratio = (
                float(largest_cluster / (num_samples - noise_count)) if (num_samples - noise_count) > 0 else 0.0
            )
            persistence = getattr(clusterer, "cluster_persistence_", np.array([]))
            median_persistence = float(np.median(persistence)) if len(persistence) else 0.0

            score = score_run(
                noise_ratio=noise_ratio,
                num_clusters=num_clusters,
                min_clusters=args.min_clusters,
                target_clusters=args.target_clusters,
            )
            rows.append(
                {
                    "score": score,
                    "num_clusters": num_clusters,
                    "noise_ratio": noise_ratio,
                    "largest_cluster_ratio": largest_cluster_ratio,
                    "median_persistence": median_persistence,
                    "umap_n_components": umap_n_components,
                    "umap_n_neighbors": umap_n_neighbors,
                    "umap_min_dist": umap_min_dist,
                    "min_cluster_size": min_cluster_size,
                    "min_samples": min_samples,
                    "cluster_selection_method": cluster_selection_method,
                    "l2_normalize": args.l2_normalize,
                    "use_umap": args.use_umap,
                    "umap_metric": args.umap_metric,
                    "hdbscan_metric": requested_metric,
                    "hdbscan_effective_metric": effective_metric,
                    "error": "",
                }
            )
        except Exception as exc:  # noqa: BLE001
            rows.append(
                {
                    "score": -1.0,
                    "num_clusters": 0,
                    "noise_ratio": 1.0,
                    "largest_cluster_ratio": 0.0,
                    "median_persistence": 0.0,
                    "umap_n_components": umap_n_components,
                    "umap_n_neighbors": umap_n_neighbors,
                    "umap_min_dist": umap_min_dist,
                    "min_cluster_size": min_cluster_size,
                    "min_samples": min_samples,
                    "cluster_selection_method": cluster_selection_method,
                    "l2_normalize": args.l2_normalize,
                    "use_umap": args.use_umap,
                    "umap_metric": args.umap_metric,
                    "hdbscan_metric": args.hdbscan_metric,
                    "hdbscan_effective_metric": "",
                    "error": str(exc),
                }
            )

    ranked = sorted(
        rows,
        key=lambda x: (
            x["score"],
            x["num_clusters"],
            -x["noise_ratio"],
            -x["largest_cluster_ratio"],
            x["median_persistence"],
        ),
        reverse=True,
    )

    output_csv = args.output_csv or data_dir / "hdbscan_grid_results.csv"
    output_json = args.output_json or data_dir / "hdbscan_grid_results.json"
    output_csv.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        "score",
        "num_clusters",
        "noise_ratio",
        "largest_cluster_ratio",
        "median_persistence",
        "umap_n_components",
        "umap_n_neighbors",
        "umap_min_dist",
        "min_cluster_size",
        "min_samples",
        "cluster_selection_method",
        "l2_normalize",
        "use_umap",
        "umap_metric",
        "hdbscan_metric",
        "hdbscan_effective_metric",
        "error",
    ]

    with output_csv.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in ranked:
            writer.writerow(row)

    payload = {
        "num_runs": len(combinations),
        "num_successful": int(sum(1 for r in ranked if not r["error"])),
        "ranking_params": {
            "min_clusters": args.min_clusters,
            "target_clusters": args.target_clusters,
        },
        "top_results": ranked[: args.top_k],
        "all_results": ranked,
    }
    with output_json.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)

    print(f"Completed {len(combinations)} runs")
    print(f"Saved CSV: {output_csv}")
    print(f"Saved JSON: {output_json}")
    print("Top configurations:")
    for idx, row in enumerate(ranked[: args.top_k], start=1):
        print(
            f"{idx:02d} | score={row['score']:.4f} | clusters={row['num_clusters']} | "
            f"noise={row['noise_ratio']:.3f} | largest={row['largest_cluster_ratio']:.3f} | "
            f"cfg=(comp={row['umap_n_components']}, neigh={row['umap_n_neighbors']}, "
            f"dist={row['umap_min_dist']}, mcs={row['min_cluster_size']}, ms={row['min_samples']}, "
            f"sel={row['cluster_selection_method']})"
        )


if __name__ == "__main__":
    main()
