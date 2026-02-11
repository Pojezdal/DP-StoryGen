from __future__ import annotations

from .llm import LLM, GenerationParams, GenerationResult
from google import genai
from google.genai import types
from typing import Iterable, Iterator, List, Optional, Sequence, Union, Dict, Any


class GoogleLLM(LLM):
    def __init__(self, model_id: str, api_key: str):
        super().__init__(model_id)
        self.client = genai.Client(api_key=api_key)


    def generate(self, prompt: str, system_instruction: Optional[str] = None, generation_params: Optional[GenerationParams] = None) -> GenerationResult:
        generation_params = generation_params or GenerationParams()
        gen_config = types.GenerateContentConfig(
            system_instruction=system_instruction,
            max_output_tokens=generation_params.max_tokens,
            temperature=generation_params.temperature,
            top_p=generation_params.top_p,
            top_k=generation_params.top_k,
            response_mime_type=generation_params.response_type,
            response_schema=generation_params.response_schema.model_json_schema() if generation_params.response_schema else None,
        )

        response = self.client.models.generate_content(
            model=self.model_id,
            contents=prompt,
            config=gen_config,
        )
        
        if generation_params.response_schema:
            try:
                output = generation_params.response_schema.model_validate_json(response.text)
            except Exception as e:
                print("Error parsing LLM response with schema:", e)
                output = response.text
        else:
            output = response.text

        return GenerationResult(
            output=output,
            token_count=response.usage_metadata.candidates_token_count,
            prompt_token_count=response.usage_metadata.prompt_token_count,
            finish_reason=response.candidates[0].finish_reason
        )

    def generate_stream(self, prompt: str, system_instruction: Optional[str] = None, generation_params: Optional[GenerationParams] = None, print_output: bool = False) -> GenerationResult:
        generation_params = generation_params or GenerationParams()
        gen_config = types.GenerateContentConfig(
            system_instruction=system_instruction,
            max_output_tokens=generation_params.max_tokens,
            temperature=generation_params.temperature,
            top_p=generation_params.top_p,
            top_k=generation_params.top_k,
            response_mime_type=generation_params.response_type,
            response_schema=generation_params.response_schema.model_json_schema() if generation_params.response_schema else None,
        )
    
        text = ""
        last_chunk = None
        for chunk in self.client.models.generate_content_stream(
			model=self.model_id,
			contents=prompt,
			config=gen_config
		):
            text += chunk.text if chunk.text else ""
            last_chunk = chunk if chunk else last_chunk
            if chunk.text and print_output:
                print(chunk.text, end="")
                
        if generation_params.response_schema:
            try:
                output = generation_params.response_schema.model_validate_json(text)
            except Exception as e:
                print("Error parsing LLM response with schema:", e)
                output = text
        else:
            output = text
                
        return GenerationResult(
            output=output,
            token_count=last_chunk.usage_metadata.candidates_token_count,
            prompt_token_count=last_chunk.usage_metadata.prompt_token_count,
            finish_reason=last_chunk.candidates[0].finish_reason
        )
    
    
    def get_input_token_limit(self):
        return self.client.models.get(model=self.model_id).input_token_limit


    def get_output_token_limit(self):
        return self.client.models.get(model=self.model_id).output_token_limit