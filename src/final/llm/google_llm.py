from __future__ import annotations

from pydantic import BaseModel

from .llm import LLM, GenerationParams, GenerationResult
import random
import time
from google import genai
from google.genai import types
from google.genai.errors import ServerError, ClientError
from typing import Iterable, Iterator, List, Optional, Sequence, Union, Dict, Any


class GoogleLLM(LLM):
    def __init__(self, model_id: str, api_keys: list[str]):
        super().__init__(model_id)
        self.api_keys = api_keys
        self.current_key_index = 0
        self.client = genai.Client(api_key=api_keys[self.current_key_index], http_options={"timeout": 1000 * 600}) # timeout is in miliseconds, setting for 10 minutes to allow for long generations
            

    def generate(self, prompt: str, system_instruction: str, generation_params: GenerationParams) -> GenerationResult:
        gen_config = types.GenerateContentConfig(
            seed = generation_params.seed,
            system_instruction=system_instruction,
            max_output_tokens=generation_params.max_tokens,
            temperature=generation_params.temperature,
            top_p=generation_params.top_p,
            top_k=generation_params.top_k,
            response_mime_type=generation_params.response_type,
            response_json_schema=generation_params.response_json_schema.model_json_schema() if generation_params.response_json_schema else None,
            thinking_config=types.ThinkingConfig(
                thinking_budget=generation_params.thinking_budget, 
                include_thoughts=generation_params.include_thoughts
            ),
        )

        start_time = time.perf_counter()
        response : types.GenerateContentResponse = self._call_with_retry(
            lambda: self.client.models.generate_content(
                model=self.model_id,
                contents=prompt,
                config=gen_config,
            )
        )
        generation_time_sec = time.perf_counter() - start_time
        
        if response is None:
            print("Received empty response from API.")
            exit(1)
        
        thoughts = None
        raw_output = None
        for part in response.parts:
            if part.thought:
                thoughts = part.text
            else:
                raw_output = part.text
        
        if generation_params.response_json_schema:
            output = self._validate_schema(raw_output, generation_params.response_json_schema)
        else:
            output = raw_output

        usage = response.usage_metadata
        output_tokens = usage.candidates_token_count if usage else None
        prompt_tokens = usage.prompt_token_count if usage else None
        total_tokens = usage.total_token_count if usage else None

        time_per_output_token_sec = generation_time_sec / output_tokens if output_tokens and output_tokens > 0 else None
        time_per_total_token_sec = generation_time_sec / total_tokens if total_tokens and total_tokens > 0 else None
        
        text_stats = self._text_stats(raw_output) 

        return GenerationResult(
            output=output,
            token_count=output_tokens,
            prompt_token_count=prompt_tokens,
            total_token_count=total_tokens,
            generation_time_sec=generation_time_sec,
            time_per_output_token_sec=time_per_output_token_sec,
            time_per_total_token_sec=time_per_total_token_sec,
            finish_reason=response.candidates[0].finish_reason,
            thoughts=thoughts,
            char_count=text_stats["char_count"],
            word_count=text_stats["word_count"],
            sentence_count=text_stats["sentence_count"]

        )



    def generate_stream(self, prompt: str, system_instruction: str, generation_params: GenerationParams, print_output: bool = False) -> GenerationResult:
        gen_config = types.GenerateContentConfig(
            seed = generation_params.seed,
            system_instruction=system_instruction,
            max_output_tokens=generation_params.max_tokens,
            temperature=generation_params.temperature,
            top_p=generation_params.top_p,
            top_k=generation_params.top_k,
            response_mime_type=generation_params.response_type,
            response_json_schema=generation_params.response_json_schema.model_json_schema() if generation_params.response_json_schema else None,
        )

        start_time = time.perf_counter()
        raw_output = ""
        last_chunk = None
        stream : Iterator[types.GenerateContentResponse] = self._call_with_retry(
            lambda: self.client.models.generate_content_stream(
                model=self.model_id,
                contents=prompt,
                config=gen_config
            )
        )
        for chunk in stream:
            raw_output += chunk.text if chunk.text else ""
            last_chunk = chunk if chunk else last_chunk
            if chunk.text and print_output:
                print(chunk.text, end="")

        generation_time_sec = time.perf_counter() - start_time
                
        if generation_params.response_json_schema:
            output = self._validate_schema(raw_output, generation_params.response_json_schema)
        else:
            output = raw_output

        usage = last_chunk.usage_metadata if last_chunk else None
        output_tokens = usage.candidates_token_count if usage else None
        prompt_tokens = usage.prompt_token_count if usage else None
        total_tokens = usage.total_token_count if usage else None

        time_per_output_token_sec = (
            generation_time_sec / output_tokens if output_tokens and output_tokens > 0 else None
        )
        time_per_total_token_sec = (
            generation_time_sec / total_tokens if total_tokens and total_tokens > 0 else None
        )

        finish_reason = None
        if last_chunk and last_chunk.candidates and len(last_chunk.candidates) > 0:
            finish_reason = last_chunk.candidates[0].finish_reason
            
        text_stats = self._text_stats(raw_output)
                
        return GenerationResult(
            output=output,
            token_count=output_tokens,
            prompt_token_count=prompt_tokens,
            total_token_count=total_tokens,
            generation_time_sec=generation_time_sec,
            time_per_output_token_sec=time_per_output_token_sec,
            time_per_total_token_sec=time_per_total_token_sec,
            finish_reason=finish_reason,
            thoughts=None, # currently the API does not return thoughts in streaming mode, if this changes in the future we can update this to capture them
            char_count=text_stats["char_count"],
            word_count=text_stats["word_count"],
            sentence_count=text_stats["sentence_count"]
        )
    
    
    def get_input_token_limit(self):
        return self.client.models.get(model=self.model_id).input_token_limit


    def get_output_token_limit(self):
        return self.client.models.get(model=self.model_id).output_token_limit
    
    
    def _call_with_retry(self, call_fn, max_retries=5):
        for attempt in range(1, max_retries + 1):
            try:
                return call_fn()
            
            except ServerError as exc:
                status = getattr(exc, "status", None)
                if status == "UNAVAILABLE": # this can happen when the model is overloaded, retrying after a short wait can help
                    print(f"Received UNAVAILABLE error from API, attempt {attempt}/{max_retries}. Retrying in a few seconds...")
                    time.sleep(random.uniform(5, 10))
                else:   # unexpected server error, not likely to be resolved by retrying
                    print(f"Received server error from API: {exc}")
                    raise
            
            except ClientError as exc:
                status = getattr(exc, "status", None)
                if status == "RESOURCE_EXHAUSTED":  # this can happen when the current API key has hit its quota limits, switching to the next key if possible
                    self.current_key_index += 1
                    if self.current_key_index >= len(self.api_keys):
                        print(f"Received RESOURCE_EXHAUSTED error from API and no more API keys to switch to.")
                        raise
                    else:
                        print(f"Received RESOURCE_EXHAUSTED error from API, switching to next API key {self.current_key_index + 1}/{len(self.api_keys)}. Retrying...")
                        self.client.close()
                        self.client = genai.Client(api_key=self.api_keys[self.current_key_index], http_options={"timeout": 1000 * 600})
                else:
                    print(f"Received client error from API: {exc}")
                    raise
                    
        print(f"Failed to call API after {max_retries} attempts.")
        
        
    def _validate_schema(self, text: str, schema: BaseModel) -> BaseModel | None:
        try:
            validated = schema.model_validate_json(text)
            return validated
        except Exception as e:
            print("Error parsing LLM response with json schema:", e)
            with open("llm_response_error_debug.txt", "w") as f:
                f.write(f"Error parsing LLM response with json schema: {e}\n")
                f.write(f"Original output:\n{text}\n")
            return None