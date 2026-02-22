import json
import random
from demo.llm.llm import LLM, GenerationParams, GenerationResult
from demo.serialization import StoryDirectory
from app.schemas.user_input import InputData
from app.schemas.crime_graph import ActorPool, CrimeGraph
from app.schemas.investigation_graph import InvestigationGraph
from app.schemas.suspect_backgrounds import SuspectBackgrounds
from app.prompts import builder

def generate_actor_pool(llm: LLM, input_data: InputData, story_directory: StoryDirectory) -> ActorPool:
    system_instruction, prompt = builder.build_prompt("actor_generation", {"input_data": input_data})    
    generation_params = GenerationParams(
        max_tokens=10000,
        temperature=1.0,
        top_p=0.9,
        top_k=5,
        repetition_penalty=0,
        response_type="application/json",
        response_schema=ActorPool,
        include_thoughts=True,
        thinking_budget=24576, # using maximum thinking budget
    )
    response = llm.generate(prompt, system_instruction=system_instruction, generation_params=generation_params)
    
    culprit_was_selected = any(suspect.culprit for suspect in response.output.suspects)
    if not culprit_was_selected:
        random_culprit = random.choice(response.output.suspects)
        random_culprit.culprit = True
        print(f"Random culprit selected: {random_culprit.id}")
        
    story_directory.save_stage("actor_generation", prompt=prompt, response=response.output, model=llm.model_id, system_instruction=system_instruction, generation_params=generation_params, thoughts=response.thoughts)
    return response.output

def generate_crime_graph(llm: LLM, input_data: InputData, actor_pool: ActorPool, story_directory: StoryDirectory) -> CrimeGraph:
    system_instruction, prompt = builder.build_prompt("crime_generation", {"input_data": input_data, "actor_pool": actor_pool})    
    generation_params = GenerationParams(
        max_tokens=10000,
        temperature=1.0,
        top_p=0.9,
        top_k=5,
        repetition_penalty=0,
        response_type="application/json",
        response_schema=CrimeGraph,
        include_thoughts=True,
        thinking_budget=24576, # using maximum thinking budget
    )
    response = llm.generate(prompt, system_instruction=system_instruction, generation_params=generation_params)
        
    story_directory.save_stage("crime_generation", prompt=prompt, response=response.output, model=llm.model_id, system_instruction=system_instruction, generation_params=generation_params, thoughts=response.thoughts)
    return response.output

def generate_suspect_backgrounds(llm: LLM, input_data: InputData, actor_pool: ActorPool, crime_graph: CrimeGraph, story_directory: StoryDirectory) -> SuspectBackgrounds:
    system_instruction, prompt = builder.build_prompt("suspect_backgrounds_generation", {"input_data": input_data, "actor_pool": actor_pool, "crime_graph": crime_graph})    
    generation_params = GenerationParams(
        max_tokens=20000,
        temperature=1.0,
        top_p=0.9,
        top_k=5,
        repetition_penalty=0,
        response_type="application/json",
        response_schema=SuspectBackgrounds,
        include_thoughts=True,
        thinking_budget=24576, # using maximum thinking budget
    )
    response = llm.generate(prompt, system_instruction=system_instruction, generation_params=generation_params)
        
    story_directory.save_stage("suspect_backgrounds_generation", prompt=prompt, response=response.output, model=llm.model_id, system_instruction=system_instruction, generation_params=generation_params, thoughts=response.thoughts)
    return response.output

def generate_investigation_graph(llm: LLM, input_data: InputData, actor_pool: ActorPool, crime_graph: CrimeGraph, suspect_backgrounds: SuspectBackgrounds, story_directory: StoryDirectory) -> InvestigationGraph:
    system_instruction, prompt = builder.build_prompt("investigation_generation", {"input_data": input_data, "actor_pool": actor_pool, "crime_graph": crime_graph, "suspect_backgrounds": suspect_backgrounds})    
    generation_params = GenerationParams(
        max_tokens=40000,
        temperature=1.0,
        top_p=0.9,
        top_k=5,
        repetition_penalty=0,
        response_type="application/json",
        response_schema=InvestigationGraph,
        include_thoughts=True,
        thinking_budget=24576, # using maximum thinking budget
    )
    response = llm.generate(prompt, system_instruction=system_instruction, generation_params=generation_params)
        
    story_directory.save_stage("investigation_generation", prompt=prompt, response=response.output, model=llm.model_id, system_instruction=system_instruction, generation_params=generation_params, thoughts=response.thoughts)
    return response.output