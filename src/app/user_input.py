import json
from demo.llm.llm import LLM, GenerationParams, GenerationResult
from demo.serialization import StoryDirectory
from app.schemas.user_input import InputData
from app.prompts import builder

def extract_input_data(llm: LLM, user_input: str, story_directory: StoryDirectory) -> InputData:
    system_instruction, prompt = builder.build_prompt("input_extraction", {"user_input": user_input})    
    generation_params = GenerationParams(
        max_tokens=10000,
        temperature=0.5,
        top_p=0.9,
        top_k=5,
        repetition_penalty=0,
        response_type="application/json",
        response_schema=InputData,
    )
    response = llm.generate(prompt, system_instruction=system_instruction, generation_params=generation_params)
        
    story_directory.save_stage("input_extraction", prompt=prompt, response=response.output, model=llm.model_id, system_instruction=system_instruction, generation_params=generation_params)
    return response.output


def fill_missing_data(llm: LLM, input_data: InputData, story_directory: StoryDirectory) -> InputData:
    system_instruction, prompt = builder.build_prompt("input_filling", {"input_data": input_data.model_dump_json(indent=2)})
    generation_params = GenerationParams(
        max_tokens=10000,
        temperature=0.7,
        top_p=0.9,
        top_k=5,
        response_type="application/json",
        response_schema=InputData,
    )
    response = llm.generate(prompt, system_instruction=system_instruction, generation_params=generation_params)

    story_directory.save_stage("data_filling", prompt=prompt, response=response.output, model=llm.model_id, system_instruction=system_instruction, generation_params=generation_params)
    return response.output