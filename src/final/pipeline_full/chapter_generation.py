from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from final.utils.prompt_builder import build_prompt
from final.utils.serialization import StoryDirectory
from final.llm.llm import LLM, GenerationParams, GenerationResult
from .detail_triple_store import DetailTripleStore
from .schemas.story_data import StoryData

_PROMPT_DIR = Path(__file__).parent / "prompts"
_INCLUDE_THOUGHTS = True
_DEFAULT_THINKING_BUDGET = 24576 # using maximum thinking budget for all stages in the pipeline, can be adjusted as needed


_SECTION_HEADER_RE = re.compile(
    r"^\s*(?:#{1,6}\s*)?(?:[-*]\s*)?(?:\*\*)?\s*SECTION\s+([123])\s*[:\-]\s*(.+?)\s*(?:\*\*)?\s*$",
    re.IGNORECASE | re.MULTILINE,
)


def _extract_last_paragraph(text: str) -> str:
    parts = [p.strip() for p in re.split(r"\n\s*\n", text or "") if p.strip()]
    if not parts:
        return ""
    
    text = parts.pop()
    while len(text) < 250 and len(parts) > 0:
        text = parts.pop() + "\n\n" + text
    
    if len(text) > 2000:
        sentences = re.split(r"(?<=[.!?])\s+", text)
        result = sentences.pop()
        while len(result) < 2000 and len(sentences) > 0:
            result = sentences.pop() + " " + result
    else:
        result = text
    
    return result.strip()


def _split_sections(raw_text: str) -> Tuple[str, str]:
    """Return (chapter_text, handoff_text)."""
    if not raw_text:
        return "", ""

    matches = list(_SECTION_HEADER_RE.finditer(raw_text))
    if not matches:
        return raw_text.strip(), ""

    sections = {"1": "", "2": ""}
    for idx, match in enumerate(matches):
        section_num = match.group(1)
        start = match.end()
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(raw_text)
        sections[section_num] = raw_text[start:end].strip()

    return sections.get("1", raw_text.strip()), sections.get("2", "")


def  _build_previous_context(previous_chapter_text: str, previous_context: str) -> str:
    if not previous_chapter_text and not previous_context:
        return ""

    last_paragraph = _extract_last_paragraph(previous_chapter_text)

    context = ""
    if last_paragraph:
        context += f"Last paragraph from previous chapter:\n{last_paragraph}\n\n"

    if previous_context:
        context += f"Context notes from the previous chapters:\n{previous_context}\n\n"

    return context.strip()


def _load_previous_context_from_story(
    story_directory: StoryDirectory,
    previous_chapter_number: int,
) -> Tuple[str, str]:
    chapter_text = ""
    handoff_text = ""

    _, chapter = story_directory.load_stage(f"chapter_generation_{previous_chapter_number:02d}")
    if chapter:
        chapter_text, handoff_text = _split_sections(chapter)

    return chapter_text, handoff_text


def _load_existing_generated_chapter(
    story_directory: StoryDirectory,
    chapter_number: int,
) -> Optional[Dict[str, Any]]:
    stage_name = f"chapter_generation_{chapter_number:02d}"
    _, raw_output = story_directory.load_stage(stage_name)

    if raw_output:
        chapter_text, handoff_text = _split_sections(raw_output)
        return {
            "chapter_number": chapter_number,
            "raw_output": raw_output,
            "chapter_text": chapter_text,
            "handoff_text": handoff_text,
            "stage_name": stage_name,
        }

    return None


def _save_triples_context_log(
    story_directory: StoryDirectory,
    chapter_number: int,
    selected_triples: List[Dict[str, Any]],
) -> None:
    stage_name = f"chapter_generation_triples_context_{chapter_number:02d}"
    payload = {
        "chapter_number": chapter_number,
        "selected_triples_count": len(selected_triples),
        "selected_triples": selected_triples,
    }
    story_directory.save_stage(
        stage=stage_name,
        data=payload,
    )


def generate_chapter(
    llm: LLM,
    story_directory: StoryDirectory,
    story_overview: Dict[str, Any],
    actors: Dict[str, Dict[str, Any]] | List[Dict[str, Any]],
    chapter_package: Dict[str, Any],
    previous_chapter_text: str = "",
    previous_context: str = "",
    detail_triple_context: Optional[List[Dict[str, Any]]] = None,
    word_min: int = 1500,
    word_max: int = 2500,
) -> Dict[str, Any]:
    chapter_meta = chapter_package.get("chapter_meta", {})
    chapter_number = int(chapter_meta.get("chapter_number", 0))
    if chapter_number <= 0:
        raise ValueError("Invalid chapter package: missing positive chapter number.")

    prompt_data = {
        "chapter_number": chapter_number,
        "overview_text": story_overview.get("overview_text", ""),
        "story_outline": story_overview.get("story_outline", ""),
        "architecture_beat_map": story_overview.get("architecture_beat_map", ""),
        "breakthrough_design": story_overview.get("breakthrough_design", ""),
        "clue_graph_context": json.dumps(
            story_overview.get("clue_graph_context", {}),
            ensure_ascii=False,
            indent=2,
        ),
        "detail_triple_context_json": json.dumps(
            detail_triple_context or [],
            ensure_ascii=False,
            indent=2,
        ),
        "global_clue_distribution": story_overview.get("global_clue_distribution", ""),
        "pacing_notes": story_overview.get("pacing_notes", ""),
        "actors": json.dumps(actors, ensure_ascii=False, indent=2),
        "current_chapter_package_json": json.dumps(chapter_package, ensure_ascii=False, indent=2),
        "previous_chapter_ending_context": _build_previous_context(
            previous_chapter_text=previous_chapter_text,
            previous_context=previous_context,
        ),
        "word_min": word_min,
        "word_max": word_max,
    }

    system_instruction, prompt = build_prompt("chapter_generation", _PROMPT_DIR, prompt_data)

    generation_params = GenerationParams(
        max_tokens=20000,
        temperature=1.0,
        top_p=0.95,
        top_k=20,
        repetition_penalty=0.2,
        include_thoughts=_INCLUDE_THOUGHTS,
        thinking_budget=_DEFAULT_THINKING_BUDGET,
    )

    response = llm.generate(
        prompt,
        system_instruction=system_instruction,
        generation_params=generation_params,
    )

    story_directory.save_stage_llm(
        f"chapter_generation_{chapter_number:02d}",
        model=llm.model_id,
        prompt=prompt,
        system_instruction=system_instruction,
        generation_params=generation_params,
        generation_result=response,
    )

    raw_text = response.output if isinstance(response.output, str) else str(response.output)
    chapter_text, handoff_text = _split_sections(raw_text)

    story_directory.save_plain(f"chapter_{chapter_number:02d}.txt", chapter_text)

    print(f"Generated Chapter {chapter_number:02d} with {len(chapter_text.split())} words.")
    
    return {
        "chapter_number": chapter_number,
        "raw_output": raw_text,
        "chapter_text": chapter_text,
        "handoff_text": handoff_text,
        "stage_name": f"chapter_generation_{chapter_number:02d}",
    }


def generate_chapters(
    llm: LLM,
    story_directory: StoryDirectory,
    package_data: Dict[str, Any],
    start_chapter: int = 1,
    end_chapter: Optional[int] = None,
    word_min: int = 1500,
    word_max: int = 2500,
    force_regenerate_chapters: bool = False,
    extract_detail_triples_enabled: bool = False,
    triple_extraction_llm: Optional[LLM] = None,
    triple_extraction_actors_context: Optional[Any] = None,
) -> List[Dict[str, Any]]:

    chapter_packages = package_data.get("chapter_packages", [])

    chapter_packages.sort(key=lambda x: int(x.get("chapter_meta", {}).get("chapter_number", 0)))

    if end_chapter is None:
        end_chapter = len(chapter_packages)

    outputs: List[Dict[str, Any]] = []
    prev_chapter_text = ""
    previous_context = ""

    triple_store: DetailTripleStore | None = None
    extraction_runtime_llm: Optional[LLM] = None
    if extract_detail_triples_enabled:
        triple_store = DetailTripleStore(story_directory=story_directory)
        extraction_runtime_llm = triple_extraction_llm or llm
        if start_chapter > 1:
            triple_store.load(
                start_chapter=1,
                end_chapter=start_chapter - 1,
                extract_if_missing=True,
                extraction_llm=extraction_runtime_llm,
                actors_context=triple_extraction_actors_context,
            )

    for index in range(1, start_chapter):
        prev_chapter_text, prev_handoff_text = _load_previous_context_from_story(
            story_directory,
            previous_chapter_number=index,
        )
        previous_context += f"Chapter {index:02d} context:\n{prev_handoff_text}\n\n"

    for package in chapter_packages:
        chapter_number = int(package.get("chapter_meta", {}).get("chapter_number", 0))
        if chapter_number < start_chapter or chapter_number > end_chapter:
            continue

        selected_detail_triples: List[Dict[str, Any]] = []
        if triple_store is not None:
            selected_detail_triples = triple_store.select_for_next_chapter(package)

        _save_triples_context_log(
            story_directory=story_directory,
            chapter_number=chapter_number,
            selected_triples=selected_detail_triples,
        )

        result = None
        if not force_regenerate_chapters:
            result = _load_existing_generated_chapter(story_directory, chapter_number)
            if result is not None:
                print(f"Loaded Chapter {chapter_number:02d} from existing artifacts.")

        if result is None:
            result = generate_chapter(
                llm=llm,
                story_directory=story_directory,
                story_overview=package_data.get("overview", {}),
                actors=package_data.get("actors", []),
                chapter_package=package,
                previous_chapter_text=prev_chapter_text,
                previous_context=previous_context,
                detail_triple_context=selected_detail_triples,
                word_min=word_min,
                word_max=word_max,
            )

        outputs.append(result)

        if triple_store is not None and extraction_runtime_llm is not None:
            triple_store.load(
                start_chapter=chapter_number,
                end_chapter=chapter_number,
                extract_if_missing=True,
                extraction_llm=extraction_runtime_llm,
                actors_context=triple_extraction_actors_context,
            )

        prev_chapter_text = result.get("chapter_text", "")
        previous_context += f"Chapter {chapter_number:02d} context:\n{result.get('handoff_text', '')}\n\n"

    return outputs


def merge_chapters(story_directory: StoryDirectory) -> str:
    parts: List[str] = []
    index = 1
    while True:
        _, chapter_body = story_directory.load_stage("chapter", filename=f"chapter_{index:02d}")
        if not chapter_body:
            break
        parts.append(f"Chapter {index:02d}:\n\n{chapter_body}\n\n")
        index += 1
    
    full_story = "\n\n".join(parts).strip()
    
    story_directory.save_plain("full_story.txt", full_story)
    
    return full_story
