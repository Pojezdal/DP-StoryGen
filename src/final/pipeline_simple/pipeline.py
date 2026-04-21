from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from final.llm.llm import GenerationParams, GenerationResult, LLM
from final.utils.prompt_builder import build_prompt
from final.utils.serialization import StoryDirectory


_PROMPT_DIR = Path(__file__).parent / "prompts"
_INCLUDE_THOUGHTS = True
_DEFAULT_THINKING_BUDGET = 24576


def execute_stage(stage_name: str, llm: LLM, story_directory: StoryDirectory, **data) -> str:
    func = globals().get(stage_name)
    if not func:
        raise ValueError(f"Stage function '{stage_name}' not found")
    result = func(llm, story_directory, **data)
    if result:
        print(f"Executed stage '{stage_name}'")
    return str(result)


def load_stage_module(
    stage_name: str,
    story_directory: StoryDirectory,
    schema: Any | None = None,
) -> str | None:
    data, plain_data = story_directory.load_stage(stage_name)
    candidate = plain_data or (data.get("output") if isinstance(data, dict) and "output" in data else None)
    loaded = str(candidate) if candidate is not None else None

    if loaded is not None:
        print(f"Loaded stage '{stage_name}'")
    return loaded


def load_or_execute_stage(
    stage_name: str,
    llm: LLM,
    story_directory: StoryDirectory,
    force_execute: bool = False,
    schema: Any | None = None,
    **data,
) -> str:
    if not force_execute:
        loaded_data = load_stage_module(stage_name, story_directory, schema)
        if loaded_data is not None:
            return loaded_data

    return execute_stage(stage_name, llm, story_directory, **data)


def _tail_sentences(text: str, count: int = 3) -> str:
    if not text:
        return ""
    sentences = re.split(r"(?<=[.!?])\s+", text.strip())
    return " ".join([s.strip() for s in sentences if s.strip()][-count:])


def _format_previous_context(previous_chapter_text: str) -> str:
    if not previous_chapter_text:
        return ""

    tail = _tail_sentences(previous_chapter_text, count=3)
    if not tail:
        return ""

    return "\n".join([
        "Tail summary of previous chapter:",
        tail,
    ]).strip()


def _extract_chapter_outline_blocks(chapter_outlines_text: str) -> list[dict[str, Any]]:
    header_re = re.compile(r"(?m)^(?:###\s*)?CHAPTER\s+(\d+)\s*:\s*(.+?)\s*$")
    headers = list(header_re.finditer(chapter_outlines_text))
    if not headers:
        raise ValueError(
            "No chapter headers found in stage 2 output. "
            "Expected lines in format: '### CHAPTER <number>: <title>'"
        )

    chapters: list[dict[str, Any]] = []
    for idx, match in enumerate(headers):
        chapter_number = int(match.group(1))
        chapter_title = match.group(2).strip()
        start = match.start()
        end = headers[idx + 1].start() if idx + 1 < len(headers) else len(chapter_outlines_text)
        chapter_block = chapter_outlines_text[start:end].strip()
        chapters.append(
            {
                "chapter_number": chapter_number,
                "chapter_title": chapter_title,
                "chapter_outline": chapter_block,
            }
        )

    chapters.sort(key=lambda item: item["chapter_number"])
    return chapters


def _extract_arc_overview(chapter_outlines_text: str) -> str:
    header_re = re.compile(r"(?m)^(?:###\s*)?CHAPTER\s+\d+\s*:\s*.+?\s*$")
    first = header_re.search(chapter_outlines_text)
    if not first:
        return ""
    return chapter_outlines_text[: first.start()].strip()


def _compile_story(chapters: list[dict[str, Any]]) -> str:
    merged: list[str] = []
    for chapter in sorted(chapters, key=lambda c: c["chapter_number"]):
        header = f"CHAPTER {chapter['chapter_number']:02d}: {chapter['chapter_title']}"
        merged.append(f"{header}\n{'=' * len(header)}\n\n{chapter['text'].strip()}")
    return "\n\n".join(merged).strip()


def _save_compiled_stage(story_directory: StoryDirectory, compiled_story: str) -> None:
    story_directory.save_stage(
        "simple_story_compilation",
        data={
            "model": "chapter-compiler",
            "prompt": "Compile generated simple chapter files into one manuscript.",
            "system_instruction": "Deterministic merge stage without LLM generation.",
            "generation_params": {
                "temperature": 0.0,
                "do_sample": False,
                "response_type": "text/plain",
            },
            "generation_result": {
                "output": compiled_story,
                "finish_reason": "compiled",
            },
        },
        plain_data=compiled_story,
    )


def story_brief_generation(llm: LLM, story_directory: StoryDirectory, user_input: str) -> str:
    stage_name = "story_brief_generation"
    story_directory.save_story_generation_prompt(user_input)
    system_instruction, prompt = build_prompt(stage_name, _PROMPT_DIR, {"user_input": user_input})

    generation_params = GenerationParams(
        max_tokens=10000,
        temperature=0.9,
        top_p=0.9,
        top_k=10,
        response_type="text/plain",
        include_thoughts=_INCLUDE_THOUGHTS,
        thinking_budget=_DEFAULT_THINKING_BUDGET,
    )

    response: GenerationResult = llm.generate(prompt, system_instruction, generation_params)
    output = str(response.output)

    story_directory.save_stage_llm(
        stage_name,
        llm.model_id,
        prompt,
        system_instruction,
        generation_params,
        response,
    )
    return output


def chapter_outlines_generation(
    llm: LLM,
    story_directory: StoryDirectory,
    story_brief: str,
) -> str:
    stage_name = "chapter_outlines_generation"
    system_instruction, prompt = build_prompt(
        stage_name,
        _PROMPT_DIR,
        {"story_brief": story_brief},
    )

    generation_params = GenerationParams(
        max_tokens=25000,
        temperature=1.0,
        top_p=0.95,
        top_k=20,
        response_type="text/plain",
        include_thoughts=_INCLUDE_THOUGHTS,
        thinking_budget=_DEFAULT_THINKING_BUDGET,
    )

    response: GenerationResult = llm.generate(prompt, system_instruction, generation_params)
    output = str(response.output)

    story_directory.save_stage_llm(
        stage_name,
        llm.model_id,
        prompt,
        system_instruction,
        generation_params,
        response,
    )
    return output


def chapter_text_generation(
    llm: LLM,
    story_directory: StoryDirectory,
    story_brief: str,
    arc_overview: str,
    chapter_number: int,
    chapter_title: str,
    chapter_outline: str,
    previous_chapter_context: str,
) -> str:
    stage_name = f"simple_chapter_text_{chapter_number:02d}"
    system_instruction, prompt = build_prompt(
        "chapter_text_generation",
        _PROMPT_DIR,
        {
            "story_brief": story_brief,
            "arc_overview": arc_overview,
            "chapter_number": chapter_number,
            "chapter_title": chapter_title,
            "chapter_outline": chapter_outline,
            "previous_chapter_context": previous_chapter_context,
        },
    )

    generation_params = GenerationParams(
        max_tokens=18000,
        temperature=0.95,
        top_p=0.95,
        top_k=20,
        response_type="text/plain",
        include_thoughts=_INCLUDE_THOUGHTS,
        thinking_budget=_DEFAULT_THINKING_BUDGET,
    )

    response: GenerationResult = llm.generate(prompt, system_instruction, generation_params)
    output = str(response.output)

    story_directory.save_stage_llm(
        stage_name,
        llm.model_id,
        prompt,
        system_instruction,
        generation_params,
        response,
    )
    return output


def run_simple_pipeline(
    llm: LLM,
    story_directory: StoryDirectory,
    user_input: str,
    force_execute_stages: bool = False,
    force_regenerate_chapters: bool = False,
) -> dict[str, Any]:
    story_brief = load_or_execute_stage(
        "story_brief_generation",
        llm,
        story_directory,
        force_execute=force_execute_stages,
        user_input=user_input,
    )

    chapter_outlines = load_or_execute_stage(
        "chapter_outlines_generation",
        llm,
        story_directory,
        force_execute=force_execute_stages,
        story_brief=story_brief,
    )
    chapter_blocks = _extract_chapter_outline_blocks(chapter_outlines)
    arc_overview = _extract_arc_overview(chapter_outlines)

    chapter_texts: list[dict[str, Any]] = []
    for chapter in chapter_blocks:
        chapter_number = chapter["chapter_number"]
        stage_name = f"simple_chapter_text_{chapter_number:02d}"

        loaded_chapter = None
        if not force_execute_stages and not force_regenerate_chapters:
            loaded_chapter = load_stage_module(stage_name, story_directory)

        if loaded_chapter is not None:
            chapter_text = loaded_chapter
        else:
            prev_chapter_text = chapter_texts[-1]["text"] if chapter_texts else ""
            previous_context = _format_previous_context(prev_chapter_text)

            chapter_text = chapter_text_generation(
                llm=llm,
                story_directory=story_directory,
                story_brief=story_brief,
                arc_overview=arc_overview,
                chapter_number=chapter_number,
                chapter_title=chapter["chapter_title"],
                chapter_outline=chapter["chapter_outline"],
                previous_chapter_context=previous_context,
            )

        chapter_texts.append(
            {
                "chapter_number": chapter_number,
                "chapter_title": chapter["chapter_title"],
                "text": chapter_text,
            }
        )

    compiled_story = _compile_story(chapter_texts)
    story_directory.save_plain("final_story_simple.txt", compiled_story)
    _save_compiled_stage(story_directory, compiled_story)

    return {
        "story_brief": story_brief,
        "chapter_outlines": chapter_outlines,
        "chapter_texts": chapter_texts,
        "compiled_story": compiled_story,
        "story_directory": story_directory.path,
    }
