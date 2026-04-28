from __future__ import annotations

import json
import time
from threading import Thread
from typing import Any, Dict, Optional, Sequence, List

from huggingface_hub import login
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig, GenerationConfig, TextIteratorStreamer

from .llm import LLM, GenerationParams, GenerationResult


class TransformersLLM(LLM):
    def __init__(
        self,
        model_id: str,
        quantization_config: Optional[BitsAndBytesConfig] = None,
        login_token: Optional[str] = None,
        device_map: Optional[str] = "auto",
        tokenizer_kwargs: Optional[Dict[str, Any]] = None,
        model_kwargs: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(model_id)
        if login_token:
            login(login_token)

        tokenizer_kwargs = tokenizer_kwargs or {}
        model_kwargs = model_kwargs or {}

        if quantization_config is not None:
            model_kwargs["quantization_config"] = quantization_config
        if device_map is not None and "device_map" not in model_kwargs:
            model_kwargs["device_map"] = device_map

        self.tokenizer = AutoTokenizer.from_pretrained(model_id, **tokenizer_kwargs)
        self.model = AutoModelForCausalLM.from_pretrained(model_id, **model_kwargs)

        if self.tokenizer.pad_token_id is None and self.tokenizer.eos_token_id is not None:
            self.tokenizer.pad_token_id = self.tokenizer.eos_token_id

    def _apply_json_schema_instruction(self, prompt: str, generation_params: GenerationParams) -> str:
        if generation_params.response_json_schema and generation_params.response_type == "application/json":
            schema = generation_params.response_json_schema.model_json_schema()
            return (
                prompt
                + "\n\nRespond by filling the following JSON schema:\n"
                + json.dumps(schema)
                + "\n"
            )
        return prompt

    def _build_inputs(self, prompt: str, system_instruction: Optional[str], generation_params: GenerationParams):
        prompt = self._apply_json_schema_instruction(prompt, generation_params)

        if hasattr(self.tokenizer, "apply_chat_template"):
            messages = [
                {"role": "system", "content": system_instruction or ""},
                {"role": "user", "content": prompt},
            ]
            inputs = self.tokenizer.apply_chat_template(
                messages,
                tokenize=True,
                add_generation_prompt=True,
                return_dict=True,
                return_tensors="pt",
            )
        else:
            if system_instruction:
                prompt = f"{system_instruction}\n\n{prompt}"
            inputs = self.tokenizer(prompt, return_tensors="pt")

        return inputs.to(self.model.device)

    def _build_generation_config(self, generation_params: GenerationParams) -> GenerationConfig:
        config_kwargs: Dict[str, Any] = {
            "do_sample": generation_params.do_sample,
            "max_new_tokens": generation_params.max_tokens,
            "temperature": generation_params.temperature,
            "top_p": generation_params.top_p,
            "top_k": generation_params.top_k,
        }

        if generation_params.repetition_penalty and generation_params.repetition_penalty > 0:
            config_kwargs["repetition_penalty"] = generation_params.repetition_penalty

        if self.tokenizer.pad_token_id is not None:
            config_kwargs["pad_token_id"] = self.tokenizer.pad_token_id

        if generation_params.extras:
            config_kwargs.update(generation_params.extras)

        return GenerationConfig(**config_kwargs)

    def _decode_generation(self, outputs, prompt_token_count: int) -> str:
        output_ids = outputs.sequences[0] if hasattr(outputs, "sequences") else outputs[0]
        completion_ids = output_ids[prompt_token_count:]
        return self.tokenizer.decode(completion_ids, skip_special_tokens=True)

    def generate(
        self,
        prompt: str,
        system_instruction: Optional[str],
        generation_params: Optional[GenerationParams],
    ) -> GenerationResult:
        generation_params = generation_params or GenerationParams()
        inputs = self._build_inputs(prompt, system_instruction, generation_params)
        gen_config = self._build_generation_config(generation_params)

        prompt_token_count = inputs["input_ids"].shape[-1]
        start_time = time.perf_counter()
        outputs = self.model.generate(**inputs, generation_config=gen_config)
        generation_time_sec = time.perf_counter() - start_time

        raw_output = self._decode_generation(outputs, prompt_token_count)

        if generation_params.response_json_schema:
            output = self._validate_schema(raw_output, generation_params.response_json_schema)
        else:
            output = raw_output

        output_tokens = len(self.tokenizer.encode(raw_output, add_special_tokens=False))
        total_tokens = prompt_token_count + output_tokens

        time_per_output_token_sec = (
            generation_time_sec / output_tokens if output_tokens and output_tokens > 0 else None
        )
        time_per_total_token_sec = (
            generation_time_sec / total_tokens if total_tokens and total_tokens > 0 else None
        )

        text_stats = self._text_stats(raw_output)

        return GenerationResult(
            output=output,
            token_count=output_tokens,
            prompt_token_count=prompt_token_count,
            total_token_count=total_tokens,
            generation_time_sec=generation_time_sec,
            time_per_output_token_sec=time_per_output_token_sec,
            time_per_total_token_sec=time_per_total_token_sec,
            finish_reason=None,
            thoughts=None,
            char_count=text_stats["char_count"],
            word_count=text_stats["word_count"],
            sentence_count=text_stats["sentence_count"],
        )

    def generate_stream(
        self,
        prompt: str,
        system_instruction: Optional[str],
        generation_params: Optional[GenerationParams],
        print_output: bool = False,
    ) -> GenerationResult:
        generation_params = generation_params or GenerationParams()
        inputs = self._build_inputs(prompt, system_instruction, generation_params)
        gen_config = self._build_generation_config(generation_params)

        prompt_token_count = inputs["input_ids"].shape[-1]
        streamer = TextIteratorStreamer(self.tokenizer, skip_prompt=True, skip_special_tokens=True)

        start_time = time.perf_counter()
        thread = Thread(
            target=self.model.generate,
            kwargs={
                **inputs,
                "generation_config": gen_config,
                "streamer": streamer,
            },
        )
        thread.start()

        raw_output = ""
        for chunk in streamer:
            raw_output += chunk
            if print_output:
                print(chunk, end="", flush=True)

        thread.join()
        generation_time_sec = time.perf_counter() - start_time

        if generation_params.response_json_schema:
            output = self._validate_schema(raw_output, generation_params.response_json_schema)
        else:
            output = raw_output

        output_tokens = len(self.tokenizer.encode(raw_output, add_special_tokens=False))
        total_tokens = prompt_token_count + output_tokens

        time_per_output_token_sec = (
            generation_time_sec / output_tokens if output_tokens and output_tokens > 0 else None
        )
        time_per_total_token_sec = (
            generation_time_sec / total_tokens if total_tokens and total_tokens > 0 else None
        )

        text_stats = self._text_stats(raw_output)

        return GenerationResult(
            output=output,
            token_count=output_tokens,
            prompt_token_count=prompt_token_count,
            total_token_count=total_tokens,
            generation_time_sec=generation_time_sec,
            time_per_output_token_sec=time_per_output_token_sec,
            time_per_total_token_sec=time_per_total_token_sec,
            finish_reason=None,
            thoughts=None,
            char_count=text_stats["char_count"],
            word_count=text_stats["word_count"],
            sentence_count=text_stats["sentence_count"],
        )

    def tokenize(self, text: str) -> List[int]:
        return self.tokenizer.encode(text, add_special_tokens=False)

    def detokenize(self, token_ids: Sequence[int]) -> str:
        return self.tokenizer.decode(list(token_ids), skip_special_tokens=True)

    def get_input_token_limit(self) -> int:
        if self.tokenizer.model_max_length is not None:
            return self.tokenizer.model_max_length
        if hasattr(self.model.config, "max_position_embeddings"):
            return self.model.config.max_position_embeddings
        raise NotImplementedError()

    def get_output_token_limit(self) -> int:
        max_new_tokens = getattr(self.model.config, "max_new_tokens", None)
        if max_new_tokens is not None:
            return max_new_tokens
        max_length = getattr(self.model.config, "max_length", None)
        if max_length is not None:
            return max_length
        return self.get_input_token_limit()
