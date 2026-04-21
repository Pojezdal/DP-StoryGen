from __future__ import annotations

from dataclasses import replace
import hashlib
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from final.llm.llm import LLM, GenerationParams, GenerationResult
from final.utils.prompt_builder import build_prompt
from final.utils.serialization import StoryDirectory

from .schemas.detail_triples import DetailTripleExtraction


_PROMPT_DIR = Path(__file__).parent / "prompts"
_INCLUDE_THOUGHTS = True
_DEFAULT_THINKING_BUDGET = -1 # auto


def _serialize_actors_context(actors_context: Optional[Any]) -> str:
    if actors_context is None:
        return "[]"

    if isinstance(actors_context, str):
        normalized = actors_context.strip()
        return normalized if normalized else "[]"

    try:
        return json.dumps(actors_context, ensure_ascii=False, indent=2)
    except TypeError:
        return json.dumps(str(actors_context), ensure_ascii=False)


def _compute_chapter_text_hash(chapter_text: str) -> str:
    normalized = (chapter_text or "").strip()
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def extract_detail_triples(
    llm: LLM,
    story_directory: StoryDirectory,
    chapter_text: str,
    chapter_number: Optional[int] = None,
    actors_context: Optional[Any] = None,
    stage_prefix: str = "detail_triple_extraction",
) -> Dict[str, Any]:
    if not chapter_text or not chapter_text.strip():
        return {
            "chapter_text_hash": "",            
            "records": [],
        }

    chapter_text_hash = _compute_chapter_text_hash(chapter_text)
    
    _, existing_records = story_directory.load_stage(f"{stage_prefix}_{chapter_number:02d}")
    existing_records = json.loads(existing_records) if existing_records else None
    if existing_records is not None and existing_records.get("chapter_text_hash", "") == chapter_text_hash:
        print(f"Detail triples for Chapter {chapter_number:02d} already extracted and up-to-date. Skipping extraction.")
        return existing_records
    

    prompt_data = {
        "chapter_text": chapter_text.strip(),
        "actors_context_json": _serialize_actors_context(actors_context),
    }
    system_instruction, prompt = build_prompt("detail_triple_extraction", _PROMPT_DIR, prompt_data)

    generation_params = GenerationParams(
        max_tokens=12000,
        temperature=0.2,
        top_p=0.9,
        top_k=10,
        response_type="application/json",
        response_json_schema=DetailTripleExtraction,
        include_thoughts=_INCLUDE_THOUGHTS,
        thinking_budget=_DEFAULT_THINKING_BUDGET,
    )

    response = llm.generate(prompt, system_instruction, generation_params)
    parsed = response.output if isinstance(response.output, DetailTripleExtraction) else None
    if parsed is None:
        parsed = DetailTripleExtraction(triples=[])

    quadruples = []
    for triple in parsed.triples:
        triple_dict = triple.model_dump()
        triple_dict["chapter"] = chapter_number
        quadruples.append(triple_dict)
    
    wrapped_output = {
        "chapter_text_hash": chapter_text_hash,
        "records": quadruples,
    }
    wrapped_response: GenerationResult = replace(response, output=wrapped_output)

    stage_name = stage_prefix
    if chapter_number is not None and chapter_number > 0:
        stage_name = f"{stage_prefix}_{chapter_number:02d}"

    story_directory.save_stage_llm(
        stage=stage_name,
        model=llm.model_id,
        prompt=prompt,
        system_instruction=system_instruction,
        generation_params=generation_params,
        generation_result=wrapped_response,
    )

    return wrapped_output
