from __future__ import annotations

import json
import httpx
from pydantic import BaseModel

from .llm import LLM, GenerationParams, GenerationResult
import random
import time
from openrouter import OpenRouter, components, errors


_REQUEST_TIMEOUT_MS = 1000 * 600  # 10 minutes
_MAX_RETRIES = 5


class OpenRouterLLM(LLM):
    def __init__(self, model_id: str, api_keys: list[str]):
        super().__init__(model_id)
        self.api_keys = api_keys
        self.current_key_index = 0
        self.client = self._create_client(self.api_keys[self.current_key_index])
        self.model_info = self._load_model_info()

    def _create_client(self, api_key: str) -> OpenRouter:
        return OpenRouter(api_key=api_key, timeout_ms=_REQUEST_TIMEOUT_MS)

    def _load_model_info(self):
        models = self.client.models.list().data
        for model in models:
            if model.id == self.model_id:
                return model

        raise ValueError(f"Model '{self.model_id}' was not found in OpenRouter model list.")

    @staticmethod
    def _build_json_schema_config(
        schema_model: BaseModel | type[BaseModel],
    ) -> components.ChatFormatJSONSchemaConfig:
        if isinstance(schema_model, type):
            schema_type = schema_model
        else:
            schema_type = schema_model.__class__

        schema_name = schema_type.__name__
        return components.ChatFormatJSONSchemaConfig(
            type="json_schema",
            json_schema=components.ChatJSONSchemaConfig(
                name=schema_name,
                description=f"Structured JSON output for {schema_name}",
                schema=schema_type.model_json_schema(),
                strict=True,
            ),
        )

    def _switch_to_next_key(self) -> bool:
        next_index = self.current_key_index + 1
        if next_index >= len(self.api_keys):
            return False

        self.current_key_index = next_index
        self.client = self._create_client(self.api_keys[self.current_key_index])
        print(
            f"Switching to next OpenRouter API key "
            f"{self.current_key_index + 1}/{len(self.api_keys)}."
        )
        return True

    @staticmethod
    def _is_retryable_validation_error(exc: errors.ResponseValidationError) -> bool:
        # OpenRouter can return an error payload (for example code 524) that fails
        # completion schema validation in the SDK.
        status_code = getattr(exc, "status_code", None)
        if status_code in {408, 429, 500, 502, 503, 504, 524}:
            return True

        body = getattr(exc, "body", "") or ""
        try:
            payload = json.loads(body)
            error_data = payload.get("error", {}) if isinstance(payload, dict) else {}
            code = error_data.get("code") if isinstance(error_data, dict) else None
            if code in {408, 429, 500, 502, 503, 504, 524}:
                return True
        except Exception:
            pass

        lowered = str(exc).lower()
        return any(token in lowered for token in ("timeout", "overload", "unavailable", "provider"))

    @staticmethod
    def _sleep_for_retry(attempt: int) -> None:
        delay = random.uniform(3.0, 6.0) * attempt
        time.sleep(delay)

    def _call_with_retry(self, call_fn, max_retries: int = _MAX_RETRIES):
        for attempt in range(1, max_retries + 1):
            try:
                return call_fn()

            except errors.PaymentRequiredResponseError as exc:
                # Usually indicates depleted credits/quota for the current key.
                if self._switch_to_next_key():
                    continue
                print(f"OpenRouter quota/credits exhausted and no additional key is available: {exc}")
                raise

            except errors.UnauthorizedResponseError as exc:
                # Invalid/revoked key: fail over when multiple keys are configured.
                if self._switch_to_next_key():
                    continue
                print(f"OpenRouter unauthorized and no additional key is available: {exc}")
                raise

            except errors.TooManyRequestsResponseError as exc:
                print(f"OpenRouter rate limit hit (attempt {attempt}/{max_retries}): {exc}")
                if attempt == max_retries:
                    raise
                self._sleep_for_retry(attempt)

            except (
                errors.RequestTimeoutResponseError,
                errors.EdgeNetworkTimeoutResponseError,
                errors.ProviderOverloadedResponseError,
                errors.ServiceUnavailableResponseError,
                errors.BadGatewayResponseError,
                errors.InternalServerResponseError,
            ) as exc:
                print(f"Transient OpenRouter error (attempt {attempt}/{max_retries}): {exc}")
                if attempt == max_retries:
                    raise
                self._sleep_for_retry(attempt)

            except errors.ResponseValidationError as exc:
                if not self._is_retryable_validation_error(exc):
                    raise
                print(
                    f"OpenRouter returned an error payload that failed response validation "
                    f"(attempt {attempt}/{max_retries}). Retrying..."
                )
                if attempt == max_retries:
                    raise
                self._sleep_for_retry(attempt)

            except (errors.NoResponseError, httpx.TimeoutException, httpx.NetworkError) as exc:
                print(f"Network/transport error calling OpenRouter (attempt {attempt}/{max_retries}): {exc}")
                if attempt == max_retries:
                    raise
                self._sleep_for_retry(attempt)

        raise RuntimeError(f"Failed to call OpenRouter after {max_retries} attempts.")
        
    
    def generate(self, prompt: str, system_instruction: str, generation_params: GenerationParams) -> GenerationResult:
        start_time = time.perf_counter()
        response = self._call_with_retry(
            lambda: self.client.chat.send(
                model=self.model_id,
                messages=[
                    {"role": "system", "content": system_instruction},
                    {"role": "user", "content": prompt}
                ],
                frequency_penalty=generation_params.repetition_penalty,
                max_completion_tokens=generation_params.max_tokens,
                reasoning=components.Reasoning(effort="medium") if generation_params.include_thoughts else None,
                response_format=self._build_json_schema_config(generation_params.response_json_schema)
                if generation_params.response_json_schema
                else None,
                seed=generation_params.seed,
                temperature=generation_params.temperature,
                top_p=generation_params.top_p,
            )
        )
        generation_time_sec = time.perf_counter() - start_time
        
        if response is None:
            print("Received empty response from API.")
            exit(1)
    
        
        thoughts = response.choices[0].message.reasoning
        raw_output = response.choices[0].message.content
        
        if generation_params.response_json_schema:
            output = self._validate_schema(raw_output, generation_params.response_json_schema)
        else:
            output = raw_output
            
        usage = response.usage
        output_tokens = usage.completion_tokens if usage else None
        prompt_tokens = usage.prompt_tokens if usage else None
        total_tokens = usage.total_tokens if usage else None

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
            finish_reason=response.choices[0].finish_reason,
            thoughts=thoughts,
            char_count=text_stats["char_count"],
            word_count=text_stats["word_count"],
            sentence_count=text_stats["sentence_count"]
        )
    
    def generate_stream(self, prompt: str, system_instruction: str, generation_params: GenerationParams, print_output: bool = False) -> GenerationResult:
        pass
    
    def get_input_token_limit(self):
        return self.model_info.top_provider.context_length

    def get_output_token_limit(self):
        return self.model_info.top_provider.max_completion_tokens


