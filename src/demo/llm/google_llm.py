from __future__ import annotations

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

    def _call_with_retry(self, call_fn):
        max_attempts = 10
        for attempt in range(1, max_attempts + 1):
            try:
                return call_fn()
            except ServerError as exc:
                status = getattr(exc, "status", None)
                if status == "UNAVAILABLE":
                    # Back off for transient 503 load spikes.
                    print(f"Received UNAVAILABLE error from API, attempt {attempt}/{max_attempts}. Retrying...")
                    time.sleep(random.uniform(5, 10))
                else:
                    print(f"Server error from API: {exc}")
                    raise
                
            except ClientError as exc:
                status = getattr(exc, "status", None)
                if status == "RESOURCE_EXHAUSTED":
                    self.current_key_index += 1
                    if self.current_key_index >= len(self.api_keys):
                        print(f"All API keys exhausted.")
                        raise
                    else:
                        print(f"Received RESOURCE_EXHAUSTED error from API, switching to next API key {self.current_key_index + 1}/{len(self.api_keys)}. Retrying...")
                        self.client.close()
                        self.client = genai.Client(api_key=self.api_keys[self.current_key_index], http_options={"timeout": 1000 * 600})
                else:
                    print(f"Client error from API: {exc}")
                    raise
                
            

    def generate(self, prompt: str, system_instruction: Optional[str] = None, generation_params: Optional[GenerationParams] = None) -> GenerationResult:
        generation_params = generation_params or GenerationParams()
        gen_config = types.GenerateContentConfig(
            seed = generation_params.seed,
            system_instruction=system_instruction,
            max_output_tokens=generation_params.max_tokens,
            temperature=generation_params.temperature,
            top_p=generation_params.top_p,
            top_k=generation_params.top_k,
            response_mime_type=generation_params.response_type,
            response_json_schema=generation_params.response_schema.model_json_schema() if generation_params.response_schema else None,
            thinking_config=types.ThinkingConfig(thinking_budget=generation_params.thinking_budget, include_thoughts=generation_params.include_thoughts),
            tools=generation_params.tools,
        )

        start_time = time.perf_counter()
        response = self._call_with_retry(

            lambda: self.client.models.generate_content(
                model=self.model_id,
                contents=prompt,
                config=gen_config,
            )
        )
        generation_time_sec = time.perf_counter() - start_time
        
        
        thoughts = None
        output = None
        for part in response.parts:
            if part.thought:
                thoughts = part.text
            else:
                output = part.text
        
        if generation_params.response_schema:
            try:
                output = generation_params.response_schema.model_validate_json(output)
            except Exception as e:
                print("Error parsing LLM response with schema:", e)
                with open("llm_response_error_debug.txt", "w") as f:
                    f.write(f"Error parsing LLM response with schema: {e}\n")
                    f.write(f"Original output:\n{output}\n")

        usage = getattr(response, "usage_metadata", None)
        output_tokens = getattr(usage, "candidates_token_count", None) if usage else None
        prompt_tokens = getattr(usage, "prompt_token_count", None) if usage else None
        total_tokens = getattr(usage, "total_token_count", None) if usage else None

        if total_tokens is None and output_tokens is not None and prompt_tokens is not None:
            total_tokens = output_tokens + prompt_tokens

        time_per_output_token_sec = (
            generation_time_sec / output_tokens if output_tokens and output_tokens > 0 else None
        )
        time_per_total_token_sec = (
            generation_time_sec / total_tokens if total_tokens and total_tokens > 0 else None
        )

        return GenerationResult(
            output=output,
            token_count=output_tokens,
            prompt_token_count=prompt_tokens,
            total_token_count=total_tokens,
            generation_time_sec=generation_time_sec,
            time_per_output_token_sec=time_per_output_token_sec,
            time_per_total_token_sec=time_per_total_token_sec,
            finish_reason=response.candidates[0].finish_reason,
            thoughts=thoughts
        )

    def generate_stream(self, prompt: str, system_instruction: Optional[str] = None, generation_params: Optional[GenerationParams] = None, print_output: bool = False) -> GenerationResult:
        generation_params = generation_params or GenerationParams()
        gen_config = types.GenerateContentConfig(
            seed = generation_params.seed,
            system_instruction=system_instruction,
            max_output_tokens=generation_params.max_tokens,
            temperature=generation_params.temperature,
            top_p=generation_params.top_p,
            top_k=generation_params.top_k,
            response_mime_type=generation_params.response_type,
            response_json_schema=generation_params.response_schema.model_json_schema() if generation_params.response_schema else None,
        )

        start_time = time.perf_counter()
        text = ""
        last_chunk = None
        stream = self._call_with_retry(
            lambda: self.client.models.generate_content_stream(
                model=self.model_id,
                contents=prompt,
                config=gen_config
            )
        )
        for chunk in stream:
            text += chunk.text if chunk.text else ""
            last_chunk = chunk if chunk else last_chunk
            if chunk.text and print_output:
                print(chunk.text, end="")

        generation_time_sec = time.perf_counter() - start_time
                
        if generation_params.response_schema:
            try:
                output = generation_params.response_schema.model_validate_json(text)
            except Exception as e:
                print("Error parsing LLM response with schema:", e)
                output = text
        else:
            output = text

        usage = getattr(last_chunk, "usage_metadata", None) if last_chunk else None
        output_tokens = getattr(usage, "candidates_token_count", None) if usage else None
        prompt_tokens = getattr(usage, "prompt_token_count", None) if usage else None
        total_tokens = getattr(usage, "total_token_count", None) if usage else None

        if total_tokens is None and output_tokens is not None and prompt_tokens is not None:
            total_tokens = output_tokens + prompt_tokens

        time_per_output_token_sec = (
            generation_time_sec / output_tokens if output_tokens and output_tokens > 0 else None
        )
        time_per_total_token_sec = (
            generation_time_sec / total_tokens if total_tokens and total_tokens > 0 else None
        )

        finish_reason = None
        if last_chunk and getattr(last_chunk, "candidates", None):
            finish_reason = last_chunk.candidates[0].finish_reason
                
        return GenerationResult(
            output=output,
            token_count=output_tokens,
            prompt_token_count=prompt_tokens,
            total_token_count=total_tokens,
            generation_time_sec=generation_time_sec,
            time_per_output_token_sec=time_per_output_token_sec,
            time_per_total_token_sec=time_per_total_token_sec,
            finish_reason=finish_reason,
        )
    
    
    def get_input_token_limit(self):
        return self.client.models.get(model=self.model_id).input_token_limit


    def get_output_token_limit(self):
        return self.client.models.get(model=self.model_id).output_token_limit