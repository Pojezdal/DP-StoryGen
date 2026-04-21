import json
import random
from pathlib import Path
from pydantic import BaseModel

from final.utils.prompt_builder import build_prompt
from final.utils.serialization import StoryDirectory
from final.llm.llm import LLM, GenerationParams, GenerationResult
from .schemas.story_data import StoryData
from .schemas.clue_graph import ClueGraph

_PROMPT_DIR = Path(__file__).parent / "prompts"
_INCLUDE_THOUGHTS = True
_DEFAULT_THINKING_BUDGET = 24576 # using maximum thinking budget for all stages in the pipeline, can be adjusted as needed


def execute_stage(stage_name: str, llm: LLM, story_directory: StoryDirectory, **data) -> BaseModel | str:
    func = globals().get(stage_name)
    if not func:
        raise ValueError(f"Stage function '{stage_name}' not found")
    result = func(llm, story_directory, **data)
    if result:
        print(f"Executed stage '{stage_name}'")
    return result


def load_stage_module(stage_name: str, story_directory: StoryDirectory, schema: BaseModel = None) -> BaseModel | dict | str | None:
    data, plain_data = story_directory.load_stage(stage_name)
    if plain_data and schema:
        try:
            plain_data = schema.model_validate(json.loads(plain_data))
        except Exception as e:
            plain_data = schema.model_validate(data["output"]) if data and "output" in data else plain_data
    result = plain_data or data or None
    if result:
        print(f"Loaded stage '{stage_name}'")
    return result


def load_or_execute_stage(stage_name: str, llm: LLM, story_directory: StoryDirectory, force_execute: bool = False, schema: BaseModel = None, **data) -> BaseModel | dict| str:
    if not force_execute:
        loaded_data = load_stage_module(stage_name, story_directory, schema)
        if loaded_data is not None:
            return loaded_data

    return execute_stage(stage_name, llm, story_directory, **data)


def _select_random_culprit(story_data: StoryData) -> StoryData:
    suspects = story_data.actor_pool.suspects
    culprit_index = random.randint(0, len(suspects) - 1)
    suspects[culprit_index].culprit = True
    print(f"No culprit identified by user. Randomly selected '{suspects[culprit_index].name}' as the culprit.")
    return story_data


def story_data_generation(llm: LLM, story_directory: StoryDirectory, user_input: str) -> StoryData:
    stage_name = "story_data_generation"
    story_directory.save_story_generation_prompt(user_input)
    system_instruction, prompt = build_prompt(stage_name, _PROMPT_DIR, {"user_input": user_input})    
    generation_params = GenerationParams(
        max_tokens=10000,
        temperature=0.5,
        top_p=0.9,
        top_k=5,
        response_type="application/json",
        response_json_schema=StoryData,
        include_thoughts=_INCLUDE_THOUGHTS,
        thinking_budget=_DEFAULT_THINKING_BUDGET,
    )
    
    response : GenerationResult = llm.generate(prompt, system_instruction, generation_params)
    
    output : StoryData = response.output
    if not any(suspect.culprit for suspect in output.actor_pool.suspects):
        output = _select_random_culprit(output)
        
    story_directory.save_stage_llm(stage_name,
        llm.model_id,
        prompt,
        system_instruction,
        generation_params,
        response,
    )
    
    return response.output

def crime_generation(llm: LLM, story_directory: StoryDirectory, story_data: StoryData) -> str:
    stage_name = "crime_generation"
    system_instruction, prompt = build_prompt(stage_name, _PROMPT_DIR, {"story_data": story_data})
    generation_params = GenerationParams(
        max_tokens=10000,
        temperature=0.8,
        top_p=0.9,
        top_k=20,
        response_type="text/plain",
        include_thoughts=_INCLUDE_THOUGHTS,
        thinking_budget=_DEFAULT_THINKING_BUDGET,
    )
    
    response : GenerationResult = llm.generate(prompt, system_instruction, generation_params)
    
    story_directory.save_stage_llm(stage_name,
        llm.model_id,
        prompt,
        system_instruction,
        generation_params,
        response,
    )
    
    return response.output


def side_stories_generation(
    llm: LLM,
    story_directory: StoryDirectory,
    story_data: StoryData,
    crime_narrative: str,
) -> str:
    stage_name = "side_stories_generation"
    system_instruction, prompt = build_prompt(
        stage_name,
        _PROMPT_DIR,
        {"story_data": story_data, "crime_narrative": crime_narrative},
    )
    generation_params = GenerationParams(
        max_tokens=10000,
        temperature=1.0,
        top_p=0.95,
        top_k=20,
        response_type="text/plain",
        include_thoughts=_INCLUDE_THOUGHTS,
        thinking_budget=_DEFAULT_THINKING_BUDGET,
    )

    response: GenerationResult = llm.generate(prompt, system_instruction, generation_params)

    story_directory.save_stage_llm(
        stage_name,
        llm.model_id,
        prompt,
        system_instruction,
        generation_params,
        response,
    )

    return response.output


def suspect_briefs_generation(
    llm: LLM,
    story_directory: StoryDirectory,
    story_data: StoryData,
    crime_narrative: str,
) -> str:
    stage_name = "suspect_briefs_generation"
    system_instruction, prompt = build_prompt(
        stage_name,
        _PROMPT_DIR,
        {"story_data": story_data, "crime_narrative": crime_narrative},
    )
    generation_params = GenerationParams(
        max_tokens=10000,
        temperature=0.9,
        top_p=0.90,
        top_k=20,
        response_type="text/plain",
        include_thoughts=_INCLUDE_THOUGHTS,
        thinking_budget=_DEFAULT_THINKING_BUDGET,
    )

    response: GenerationResult = llm.generate(prompt, system_instruction, generation_params)

    story_directory.save_stage_llm(
        stage_name,
        llm.model_id,
        prompt,
        system_instruction,
        generation_params,
        response,
    )

    return response.output


def surface_level_generation(
    llm: LLM,
    story_directory: StoryDirectory,
    story_data: StoryData,
    crime_narrative: str,
    side_stories: str,
) -> str:
    stage_name = "surface_level_generation"
    system_instruction, prompt = build_prompt(
        stage_name,
        _PROMPT_DIR,
        {
            "story_data": story_data,
            "crime_narrative": crime_narrative,
            "side_stories": side_stories,
        },
    )
    generation_params = GenerationParams(
        max_tokens=10000,
        temperature=1.0,
        top_p=0.95,
        top_k=20,
        response_type="text/plain",
        include_thoughts=_INCLUDE_THOUGHTS,
        thinking_budget=_DEFAULT_THINKING_BUDGET,
    )

    response: GenerationResult = llm.generate(prompt, system_instruction, generation_params)

    story_directory.save_stage_llm(
        stage_name,
        llm.model_id,
        prompt,
        system_instruction,
        generation_params,
        response,
    )

    return response.output


def agendas_generation(
    llm: LLM,
    story_directory: StoryDirectory,
    story_data: StoryData,
    crime_narrative: str,
    side_stories: str,
    surface_level: str,
) -> str:
    stage_name = "agendas_generation"
    system_instruction, prompt = build_prompt(
        stage_name,
        _PROMPT_DIR,
        {
            "story_data": story_data,
            "crime_narrative": crime_narrative,
            "side_stories": side_stories,
            "surface_level": surface_level,
        },
    )
    generation_params = GenerationParams(
        max_tokens=10000,
        temperature=1.0,
        top_p=0.95,
        top_k=20,
        response_type="text/plain",
        include_thoughts=_INCLUDE_THOUGHTS,
        thinking_budget=_DEFAULT_THINKING_BUDGET,
    )

    response: GenerationResult = llm.generate(prompt, system_instruction, generation_params)

    story_directory.save_stage_llm(
        stage_name,
        llm.model_id,
        prompt,
        system_instruction,
        generation_params,
        response,
    )

    return response.output


def investigation_generation(
    llm: LLM,
    story_directory: StoryDirectory,
    story_data: StoryData,
    crime_narrative: str,
    suspect_briefs: str,
) -> str:
    stage_name = "investigation_generation"
    system_instruction, prompt = build_prompt(
        stage_name,
        _PROMPT_DIR,
        {
            "story_data": story_data,
            "crime_narrative": crime_narrative,
            "suspect_briefs": suspect_briefs,
        },
    )
    generation_params = GenerationParams(
        max_tokens=10000,
        temperature=0.9,
        top_p=0.90,
        top_k=20,
        response_type="text/plain",
        include_thoughts=_INCLUDE_THOUGHTS,
        thinking_budget=_DEFAULT_THINKING_BUDGET,
    )

    response: GenerationResult = llm.generate(prompt, system_instruction, generation_params)

    story_directory.save_stage_llm(
        stage_name,
        llm.model_id,
        prompt,
        system_instruction,
        generation_params,
        response,
    )

    return response.output


def clue_graph_generation(
    llm: LLM,
    story_directory: StoryDirectory,
    story_data: StoryData,
    crime_narrative: str,
    suspect_briefs: str,
) -> ClueGraph:
    stage_name = "clue_graph_generation"
    system_instruction, prompt = build_prompt(
        stage_name,
        _PROMPT_DIR,
        {
            "story_data": story_data,
            "crime_narrative": crime_narrative,
            "suspect_briefs": suspect_briefs,
        },
    )
    generation_params = GenerationParams(
        max_tokens=20000,
        temperature=0.7,
        top_p=0.9,
        top_k=20,
        response_type="application/json",
        response_json_schema=ClueGraph,
        include_thoughts=_INCLUDE_THOUGHTS,
        thinking_budget=_DEFAULT_THINKING_BUDGET,
    )

    response: GenerationResult = llm.generate(prompt, system_instruction, generation_params)

    story_directory.save_stage_llm(
        stage_name,
        llm.model_id,
        prompt,
        system_instruction,
        generation_params,
        response,
    )

    return response.output


def architecture_generation(
    llm: LLM,
    story_directory: StoryDirectory,
    story_data: StoryData,
    crime_narrative: str,
    suspect_briefs: str,
    clue_graph: ClueGraph | dict | str,
) -> str:
    stage_name = "architecture_generation"

    clue_graph_payload = clue_graph
    if isinstance(clue_graph, BaseModel):
        clue_graph_payload = clue_graph.model_dump_json(indent=2)

    system_instruction, prompt = build_prompt(
        stage_name,
        _PROMPT_DIR,
        {
            "story_data": story_data,
            "crime_narrative": crime_narrative,
            "suspect_briefs": suspect_briefs,
            "clue_graph": clue_graph_payload,
        },
    )
    generation_params = GenerationParams(
        max_tokens=50000,
        temperature=1.0,
        top_p=0.95,
        top_k=20,
        response_type="text/plain",
        include_thoughts=_INCLUDE_THOUGHTS,
        thinking_budget=_DEFAULT_THINKING_BUDGET,
    )

    response: GenerationResult = llm.generate(prompt, system_instruction, generation_params)

    story_directory.save_stage_llm(
        stage_name,
        llm.model_id,
        prompt,
        system_instruction,
        generation_params,
        response,
    )

    return response.output


def chapter_outline_generation(
    llm: LLM,
    story_directory: StoryDirectory,
    story_data: StoryData,
    crime_narrative: str,
    suspect_briefs: str,
    architecture: str,
    clue_graph: ClueGraph | dict | str | None = None,
) -> str:
    stage_name = "chapter_outline_generation"

    clue_graph_payload = (
        "[OPTIONAL INPUT NOT PROVIDED]\n"
        "No clue graph was supplied for this run. Use architecture as the canonical backbone and "
        "derive detailed clue placement from crime_narrative + suspect_briefs without introducing "
        "new contradictions."
    )
    if isinstance(clue_graph, BaseModel):
        clue_graph_payload = clue_graph.model_dump_json(indent=2)
    elif isinstance(clue_graph, dict):
        clue_graph_payload = json.dumps(clue_graph, indent=2, ensure_ascii=False)
    elif isinstance(clue_graph, str) and clue_graph.strip():
        clue_graph_payload = clue_graph

    system_instruction, prompt = build_prompt(
        stage_name,
        _PROMPT_DIR,
        {
            "story_data": story_data,
            "crime_narrative": crime_narrative,
            "suspect_briefs": suspect_briefs,
            "clue_graph": clue_graph_payload,
            "architecture": architecture,
        },
    )
    generation_params = GenerationParams(
        max_tokens=50000,
        temperature=1.0,
        top_p=0.95,
        top_k=20,
        response_type="text/plain",
        include_thoughts=_INCLUDE_THOUGHTS,
        thinking_budget=_DEFAULT_THINKING_BUDGET,
    )

    response: GenerationResult = llm.generate(prompt, system_instruction, generation_params)

    story_directory.save_stage_llm(
        stage_name,
        llm.model_id,
        prompt,
        system_instruction,
        generation_params,
        response,
    )

    return response.output