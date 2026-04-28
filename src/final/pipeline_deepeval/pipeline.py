from __future__ import annotations

import hashlib
import json
from statistics import mean
from pathlib import Path
from typing import Any

from deepeval import evaluate
from deepeval.evaluate.types import EvaluationResult
from deepeval.metrics import GEval
from deepeval.metrics.g_eval.utils import Rubric
from deepeval.models.base_model import DeepEvalBaseLLM
from deepeval.test_case import LLMTestCaseParams
from deepeval.test_case import LLMTestCase

from final.utils.serialization import StoryDirectory


# Keep these aligned with the rubric used in pipeline_eval.
_RUBRIC_CRITERIA: list[tuple[str, str]] = [
    (
        "creativity_and_originality",
        "Evaluate creativity and originality of the story. Reward fresh ideas, inventive setups, and non-generic execution while preserving internal consistency.",
    ),
    (
        "coherence_and_structure",
        "Evaluate coherence and structure. Reward clear narrative flow, logical progression, and scene-to-scene continuity without contradictions.",
    ),
    (
        "character_depth",
        "Evaluate character depth. Reward distinct motivations, believable behavior, and emotionally grounded choices for key characters.",
    ),
    (
        "pacing_and_tension",
        "Evaluate pacing and tension. Reward strong momentum, effective escalation, and well-timed reveals without unnecessary drag.",
    ),
    (
        "prose_clarity_and_voice",
        "Evaluate prose clarity and voice. Reward readable prose, stylistic consistency, and vivid language that supports the story rather than obscuring it.",
    ),
    (
        "clue_fairness_and_visibility",
        "Evaluate clue fairness and visibility in detective-fiction terms. Reward clues that are available to the reader and relevant to the final solution.",
    ),
    (
        "deduction_chain_logic",
        "Evaluate deduction chain logic. Reward reasoning that follows from evidence step-by-step and penalize unexplained leaps.",
    ),
    (
        "red_herring_quality",
        "Evaluate red herring quality. Reward misdirection that is plausible and fair, not arbitrary or deceptive in an unfair way.",
    ),
    (
        "suspect_motives_and_opportunity",
        "Evaluate suspect motives and opportunity. Reward believable motive/opportunity structure and penalize implausible or underdeveloped suspect logic.",
    ),
    (
        "reveal_and_resolution_payoff",
        "Evaluate reveal and resolution payoff. Reward endings that are earned by prior setup and deliver a satisfying, coherent resolution.",
    ),
    (
        "prompt_alignment",
        "Evaluate prompt alignment. Compare the story against the original generation prompt and reward faithful satisfaction of explicit constraints and key implied goals.",
    ),
]

_QUALITY_RUBRIC = [
    Rubric(score_range=(0, 2), expected_outcome="Very weak quality for this criterion."),
    Rubric(score_range=(3, 6), expected_outcome="Acceptable but clearly improvable quality for this criterion."),
    Rubric(score_range=(7, 9), expected_outcome="Strong quality with only minor weaknesses for this criterion."),
    Rubric(score_range=(10, 10), expected_outcome="Excellent quality for this criterion with no meaningful issues. Human level quality."),
]

_G_EVAL_STEPS_CACHE_FILENAME = ".deepeval_g_eval_steps.json"


def _steps_cache_path(story_dir: StoryDirectory) -> Path:
    # Keep one cache per stories base directory so steps can be reused across stories.
    return Path("stories") / _G_EVAL_STEPS_CACHE_FILENAME


def _load_steps_cache(cache_path: Path) -> dict[str, dict[str, Any]]:
    if not cache_path.exists() or not cache_path.is_file():
        return {}

    try:
        payload = json.loads(cache_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}

    metrics = payload.get("metrics") if isinstance(payload, dict) else None
    if not isinstance(metrics, dict):
        return {}

    normalized: dict[str, dict[str, Any]] = {}
    for metric_name, entry in metrics.items():
        if not isinstance(metric_name, str) or not isinstance(entry, dict):
            continue
        normalized[metric_name] = entry
    return normalized


def _save_steps_cache(cache_path: Path, metrics_cache: dict[str, dict[str, Any]]) -> None:
    payload = {
        "version": 1,
        "metrics": metrics_cache,
    }
    cache_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _metric_fingerprint(
    metric_name: str,
    criteria: str,
    evaluation_params: list[LLMTestCaseParams],
) -> str:
    payload = {
        "metric_name": metric_name,
        "criteria": criteria,
        "evaluation_params": [param.value for param in evaluation_params],
        "rubric": [
            {
                "score_range": list(rubric_item.score_range),
                "expected_outcome": rubric_item.expected_outcome,
            }
            for rubric_item in _QUALITY_RUBRIC
        ],
    }
    serialized = json.dumps(payload, ensure_ascii=True, sort_keys=True)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def _load_cached_steps(
    metrics_cache: dict[str, dict[str, Any]],
    metric_name: str,
    fingerprint: str,
) -> list[str] | None:
    cached_entry = metrics_cache.get(metric_name)
    if not isinstance(cached_entry, dict):
        return None

    if cached_entry.get("fingerprint") != fingerprint:
        return None

    cached_steps = cached_entry.get("evaluation_steps")
    if not isinstance(cached_steps, list) or not cached_steps:
        return None

    if not all(isinstance(step, str) and step.strip() for step in cached_steps):
        return None

    return cached_steps


def _build_metrics(
    model: DeepEvalBaseLLM,
    metrics_cache: dict[str, dict[str, Any]] | None = None,
) -> tuple[list[GEval], dict[str, str]]:
    metrics: list[GEval] = []
    metric_fingerprints: dict[str, str] = {}
    cache = metrics_cache or {}

    for metric_name, criteria in _RUBRIC_CRITERIA:
        evaluation_params = (
            [LLMTestCaseParams.INPUT, LLMTestCaseParams.ACTUAL_OUTPUT]
            if metric_name == "prompt_alignment"
            else [LLMTestCaseParams.ACTUAL_OUTPUT]
        )
        fingerprint = _metric_fingerprint(metric_name, criteria, evaluation_params)
        metric_fingerprints[metric_name] = fingerprint
        evaluation_steps = _load_cached_steps(cache, metric_name, fingerprint)

        metrics.append(
            GEval(
                name=metric_name,
                criteria=criteria if not evaluation_steps else None,
                evaluation_steps=evaluation_steps,
                evaluation_params=evaluation_params,
                rubric=_QUALITY_RUBRIC,
                model=model,
                threshold=0.5,
                async_mode=True,
                strict_mode=False,
            )
        )
    return metrics, metric_fingerprints


def _materialize_missing_steps(metrics: list[GEval]) -> None:
    """Generate missing GEval steps once so they can be cached and reused."""
    for metric in metrics:
        existing_steps = getattr(metric, "evaluation_steps", None)
        if isinstance(existing_steps, list) and existing_steps:
            continue

        generated_steps = metric._generate_evaluation_steps(multimodal=False)
        clean_steps = [
            step for step in generated_steps if isinstance(step, str) and step.strip()
        ]
        if not clean_steps:
            raise ValueError(f"Failed to generate evaluation steps for metric '{metric.name}'.")

        metric.evaluation_steps = clean_steps
        metric.criteria = None


def evaluate_story(model: DeepEvalBaseLLM, story_dir: StoryDirectory) -> EvaluationResult:
    _, text = story_dir.load_stage("full_story", filename="full_story")
    story_text = text if isinstance(text, str) else ""

    if not story_text.strip():
        raise ValueError("No story text available in stage 'full_story'.")

    prompt_text = story_dir.load_story_generation_prompt() or "N/A: original prompt not found."

    test_case = LLMTestCase(
        input=prompt_text,
        actual_output=story_text,
    )

    cache_path = _steps_cache_path(story_dir)
    metrics_cache = _load_steps_cache(cache_path)
    metrics, metric_fingerprints = _build_metrics(model, metrics_cache=metrics_cache)

    # Ensure steps are always present before evaluation so cache persistence is reliable.
    _materialize_missing_steps(metrics)

    updated_cache = dict(metrics_cache)
    for metric in metrics:
        steps = getattr(metric, "evaluation_steps", None)
        fingerprint = metric_fingerprints.get(metric.name)
        if not fingerprint or not isinstance(steps, list) or not steps:
            continue

        clean_steps = [step for step in steps if isinstance(step, str) and step.strip()]
        if not clean_steps:
            continue

        updated_cache[metric.name] = {
            "fingerprint": fingerprint,
            "evaluation_steps": clean_steps,
        }

    try:
        _save_steps_cache(cache_path, updated_cache)
    except OSError:
        # Evaluation should not fail if cache persistence fails.
        pass

    result = evaluate(test_cases=[test_case], metrics=metrics)

    return result


def summarize_evaluation(result: EvaluationResult) -> dict[str, Any]:
    metrics_summary: dict[str, dict[str, Any]] = {}

    if not result.test_results:
        return {
            "overall_score_10": None,
            "criteria": metrics_summary,
        }

    test_result = result.test_results[0]
    metrics_data = test_result.metrics_data or []

    numeric_scores_10: list[float] = []
    for metric in metrics_data:
        score_01 = metric.score if metric.score is not None else None
        score_10 = (score_01 * 10.0) if score_01 is not None else None
        if score_10 is not None:
            numeric_scores_10.append(score_10)

        metrics_summary[metric.name] = {
            "score_10": score_10,
            "success": metric.success,
            "reason": metric.reason,
            "error": metric.error,
        }

    overall_score_10 = mean(numeric_scores_10) if numeric_scores_10 else None

    return {
        "overall_score_10": overall_score_10,
        "criteria": metrics_summary,
    }