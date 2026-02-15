import json
from demo.llm.llm import LLM, GenerationParams, GenerationResult
from demo.serialization import StoryDirectory
from app.schemas.user_input import InputData
from app.schemas.crime_graph import ActorPool, CrimeGraph
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
    )
    response = llm.generate(prompt, system_instruction=system_instruction, generation_params=generation_params)
        
    story_directory.save_stage("actor_generation", prompt=prompt, response=response.output, model=llm.model_id, system_instruction=system_instruction, generation_params=generation_params)
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
    )
    response = llm.generate(prompt, system_instruction=system_instruction, generation_params=generation_params)
        
    story_directory.save_stage("crime_generation", prompt=prompt, response=response.output, model=llm.model_id, system_instruction=system_instruction, generation_params=generation_params)
    return response.output