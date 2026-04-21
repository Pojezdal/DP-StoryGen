from __future__ import annotations

from statistics import mean
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
    Rubric(score_range=(10, 10), expected_outcome="Excellent quality for this criterion with no meaningful issues."),
]


def _build_metrics(model: DeepEvalBaseLLM) -> list[GEval]:
    metrics: list[GEval] = []
    for metric_name, criteria in _RUBRIC_CRITERIA:
        evaluation_params = (
            [LLMTestCaseParams.INPUT, LLMTestCaseParams.ACTUAL_OUTPUT]
            if metric_name == "prompt_alignment"
            else [LLMTestCaseParams.ACTUAL_OUTPUT]
        )
        metrics.append(
            GEval(
                name=metric_name,
                criteria=criteria,
                evaluation_params=evaluation_params,
                rubric=_QUALITY_RUBRIC,
                model=model,
                threshold=0.5,
                async_mode=True,
                strict_mode=False,
            )
        )
    return metrics


def evaluate_story(model: DeepEvalBaseLLM, story_dir: StoryDirectory) -> EvaluationResult:
    _, text = story_dir.load_stage("final_story")
    story_text = text if isinstance(text, str) else ""

    if not story_text.strip():
        raise ValueError("No story text available in stage 'final_story'.")

    prompt_text = story_dir.load_story_generation_prompt() or "N/A: original prompt not found."

    test_case = LLMTestCase(
        input=prompt_text,
        actual_output=story_text,
    )

    return evaluate(test_cases=[test_case], metrics=_build_metrics(model))


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