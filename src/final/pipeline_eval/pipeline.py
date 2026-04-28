from __future__ import annotations

from dataclasses import replace
import json
from pathlib import Path

from final.llm.llm import GenerationParams, GenerationResult, LLM
from final.utils.prompt_builder import build_prompt
from final.utils.serialization import StoryDirectory
from final.pipeline_eval.schemas.story_rubric_evaluation import (
    StoryRubricEvaluation,
    StoryRubricEvaluationWithoutOverall,
)
from final.pipeline_eval.schemas.story_pairwise_comparison import StoryPairwiseComparison


_PROMPT_DIR = Path(__file__).parent / "prompts"
_INCLUDE_THOUGHTS = False
_DEFAULT_THINKING_BUDGET = 24576
_DEFAULT_MAX_TOKENS = 6000
_LONG_STORY_FALLBACK_TRIGGER_CHARS = 90000
_LONG_STORY_EXCERPT_CHARS = 60000
_LONG_STORY_MAX_TOKENS = 4200
_PROMPT_SOURCE_MAX_CHARS = 8000
_PAIRWISE_STAGE_NAME = "story_pairwise_comparison"
_PAIRWISE_MAX_TOKENS = 4500
_PAIRWISE_LONG_MAX_TOKENS = 3600
_PAIRWISE_LONG_TRIGGER_TOTAL_CHARS = 140000


def _coerce_rubric_evaluation_output(output_candidate: object) -> StoryRubricEvaluation | None:
    if isinstance(output_candidate, StoryRubricEvaluationWithoutOverall):
        return StoryRubricEvaluation.from_without_overall(output_candidate)

    if isinstance(output_candidate, dict):
        try:
            raw = StoryRubricEvaluationWithoutOverall.model_validate(output_candidate)
        except Exception:
            return None
        return StoryRubricEvaluation.from_without_overall(raw)

    return None


def _extract_cached_evaluation(story_directory: StoryDirectory, stage_name: str) -> StoryRubricEvaluation | None:
    data, plain_data = story_directory.load_stage(stage_name)

    if isinstance(data, dict):
        generation_result = data.get("generation_result", {})
        output_candidate = generation_result.get("output")
        if isinstance(output_candidate, dict):
            coerced = _coerce_rubric_evaluation_output(output_candidate)
            if coerced is not None:
                return coerced

    if isinstance(plain_data, str) and plain_data.strip():
        try:
            return _coerce_rubric_evaluation_output(json.loads(plain_data))
        except Exception:
            return None

    return None


def _build_center_excerpt(text: str, target_chars: int) -> str:
    if len(text) <= target_chars:
        return text

    segment = max(target_chars // 3, 1)
    head = text[:segment]
    mid_start = max((len(text) // 2) - (segment // 2), 0)
    middle = text[mid_start : mid_start + segment]
    tail = text[-segment:]

    return (
        f"{head}\n\n"
        "[... middle sections omitted for runtime stability on very long inputs ...]\n\n"
        f"{middle}\n\n"
        "[... additional sections omitted ...]\n\n"
        f"{tail}"
    )


def _extract_story_generation_prompt(story_directory: StoryDirectory) -> str:
    source_prompt = story_directory.load_story_generation_prompt()
    if source_prompt:
        if len(source_prompt) > _PROMPT_SOURCE_MAX_CHARS:
            return source_prompt[:_PROMPT_SOURCE_MAX_CHARS].rstrip() + "\n...[truncated]..."
        return source_prompt

    return "N/A: story_generation_prompt.txt was not found. Re-run stage 1 to persist the original prompt."


def _generate_story_evaluation(
    llm: LLM,
    story_text: str,
    story_generation_prompt: str,
    evaluation_focus: str,
    max_tokens: int,
) -> tuple[GenerationResult, str, str, GenerationParams]:
    system_instruction, prompt = build_prompt(
        "story_rubric_evaluation",
        _PROMPT_DIR,
        {
            "story_text": story_text,
            "story_generation_prompt": story_generation_prompt,
            "evaluation_focus": evaluation_focus,
        },
    )

    generation_params = GenerationParams(
        max_tokens=max_tokens,
        temperature=0.3,
        top_p=0.9,
        top_k=10,
        response_type="application/json",
        response_json_schema=StoryRubricEvaluationWithoutOverall,
        include_thoughts=_INCLUDE_THOUGHTS,
        thinking_budget=_DEFAULT_THINKING_BUDGET,
    )

    response = llm.generate(prompt, system_instruction, generation_params)
    return response, prompt, system_instruction, generation_params


def _generate_pairwise_comparison(
    llm: LLM,
    story_a_label: str,
    story_b_label: str,
    story_a_text: str,
    story_b_text: str,
    story_a_generation_prompt: str,
    story_b_generation_prompt: str,
    evaluation_focus: str,
    max_tokens: int,
) -> tuple[GenerationResult, str, str, GenerationParams]:
    system_instruction, prompt = build_prompt(
        "story_pairwise_comparison",
        _PROMPT_DIR,
        {
            "story_a_label": story_a_label,
            "story_b_label": story_b_label,
            "story_a_text": story_a_text,
            "story_b_text": story_b_text,
            "story_a_generation_prompt": story_a_generation_prompt,
            "story_b_generation_prompt": story_b_generation_prompt,
            "evaluation_focus": evaluation_focus,
        },
    )

    generation_params = GenerationParams(
        max_tokens=max_tokens,
        temperature=0.2,
        top_p=0.9,
        top_k=10,
        response_type="application/json",
        response_json_schema=StoryPairwiseComparison,
        include_thoughts=_INCLUDE_THOUGHTS,
        thinking_budget=_DEFAULT_THINKING_BUDGET,
    )

    response = llm.generate(prompt, system_instruction, generation_params)
    return response, prompt, system_instruction, generation_params


def story_pairwise_comparison(
    llm: LLM,
    story_a_directory: StoryDirectory,
    story_a_text: str,
    story_b_directory: StoryDirectory,
    story_b_text: str,
    evaluation_focus: str = "",
    force_execute: bool = False,
) -> StoryPairwiseComparison:
    stage_name = _PAIRWISE_STAGE_NAME
    story_a_label = story_a_directory.path.name
    story_b_label = story_b_directory.path.name


    story_a_generation_prompt = _extract_story_generation_prompt(story_a_directory)
    story_b_generation_prompt = _extract_story_generation_prompt(story_b_directory)

    response: GenerationResult | None = None
    prompt = ""
    system_instruction = ""
    generation_params: GenerationParams | None = None

    total_story_chars = len(story_a_text) + len(story_b_text)
    use_excerpt_mode = total_story_chars >= _PAIRWISE_LONG_TRIGGER_TOTAL_CHARS

    if use_excerpt_mode:
        story_a_input = _build_center_excerpt(story_a_text, _LONG_STORY_EXCERPT_CHARS)
        story_b_input = _build_center_excerpt(story_b_text, _LONG_STORY_EXCERPT_CHARS)
        pairwise_focus = (
            "Long-story pairwise mode: compare based on provided excerpts. "
            "If omitted sections reduce certainty, reflect it in rationales."
        )
        if evaluation_focus:
            pairwise_focus = f"{pairwise_focus}\n\n{evaluation_focus}"
        max_tokens = _PAIRWISE_LONG_MAX_TOKENS
    else:
        story_a_input = story_a_text
        story_b_input = story_b_text
        pairwise_focus = evaluation_focus
        max_tokens = _PAIRWISE_MAX_TOKENS

    response, prompt, system_instruction, generation_params = _generate_pairwise_comparison(
        llm=llm,
        story_a_label=story_a_label,
        story_b_label=story_b_label,
        story_a_text=story_a_input,
        story_b_text=story_b_input,
        story_a_generation_prompt=story_a_generation_prompt,
        story_b_generation_prompt=story_b_generation_prompt,
        evaluation_focus=pairwise_focus,
        max_tokens=max_tokens,
    )

    output: StoryPairwiseComparison | None = response.output
    if output is None:
        raise ValueError("LLM response could not be validated against StoryPairwiseComparison schema")

    story_a_directory.save_stage_llm(
        stage_name,
        llm.model_id,
        prompt,
        system_instruction,
        generation_params,
        response,
    )
    print(f"Executed stage '{stage_name}'")

    return output


def story_rubric_evaluation(
    llm: LLM,
    story_directory: StoryDirectory,
    story_text: str,
    evaluation_focus: str = "",
    force_execute: bool = False,
) -> StoryRubricEvaluation:
    stage_name = "story_rubric_evaluation"

    if not force_execute:
        cached = _extract_cached_evaluation(story_directory, stage_name)
        if cached is not None:
            print(f"Loaded stage '{stage_name}'")
            return cached

    story_generation_prompt = _extract_story_generation_prompt(story_directory)

    response: GenerationResult | None = None
    prompt = ""
    system_instruction = ""
    generation_params: GenerationParams | None = None
    used_fallback = False
    fallback_focus_prefix = (
        "Long-story fallback mode: evaluate based on the provided excerpts and stay concise. "
        "If confidence is lower due to omitted sections, reflect that in rationales."
    )

    try:
        response, prompt, system_instruction, generation_params = _generate_story_evaluation(
            llm=llm,
            story_text=story_text,
            story_generation_prompt=story_generation_prompt,
            evaluation_focus=evaluation_focus,
            max_tokens=_DEFAULT_MAX_TOKENS,
        )
    except Exception as exc:
        if len(story_text) < _LONG_STORY_FALLBACK_TRIGGER_CHARS:
            raise

        print(
            "Full-story evaluation failed on a long input. "
            "Retrying with a condensed excerpt for runtime stability..."
        )
        excerpt = _build_center_excerpt(story_text, _LONG_STORY_EXCERPT_CHARS)
        fallback_focus = (
            f"{fallback_focus_prefix}\n\n{evaluation_focus}".strip()
            if evaluation_focus
            else fallback_focus_prefix
        )
        response, prompt, system_instruction, generation_params = _generate_story_evaluation(
            llm=llm,
            story_text=excerpt,
            story_generation_prompt=story_generation_prompt,
            evaluation_focus=fallback_focus,
            max_tokens=_LONG_STORY_MAX_TOKENS,
        )
        used_fallback = True

        print(f"Fallback retry succeeded after initial error: {exc}")

    output = _coerce_rubric_evaluation_output(response.output)
    if output is None and len(story_text) >= _LONG_STORY_FALLBACK_TRIGGER_CHARS and not used_fallback:
        print(
            "Structured output validation failed on full long-story input. "
            "Retrying with a condensed excerpt..."
        )
        excerpt = _build_center_excerpt(story_text, _LONG_STORY_EXCERPT_CHARS)
        fallback_focus = (
            f"{fallback_focus_prefix}\n\n{evaluation_focus}".strip()
            if evaluation_focus
            else fallback_focus_prefix
        )
        response, prompt, system_instruction, generation_params = _generate_story_evaluation(
            llm=llm,
            story_text=excerpt,
            story_generation_prompt=story_generation_prompt,
            evaluation_focus=fallback_focus,
            max_tokens=_LONG_STORY_MAX_TOKENS,
        )
        output = _coerce_rubric_evaluation_output(response.output)
        used_fallback = True

    if output is None:
        raise ValueError("LLM response could not be validated against StoryRubricEvaluation schema")

    response = replace(response, output=output)

    if used_fallback:
        print("Long-story fallback mode was used for rubric evaluation.")

    story_directory.save_stage_llm(
        stage_name,
        llm.model_id,
        prompt,
        system_instruction,
        generation_params,
        response,
    )
    print(f"Executed stage '{stage_name}'")

    return output
