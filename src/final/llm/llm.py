from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
import random
import re
from typing import Iterable, Iterator, List, Optional, Sequence, Union, Dict, Any

from pydantic import BaseModel


@dataclass
class GenerationParams:
    seed: Optional[int] = random.randint(0, 1_000_000_000)  # default to random seed if not provided
    temperature: float = 0.7
    do_sample: bool = True
    top_p: float = 1.0
    top_k: int = 0
    max_tokens: int = 1024
    repetition_penalty: float = 0.0
    response_type: str = "text/plain"
    response_json_schema: Optional[BaseModel] = None
    include_thoughts: bool = False
    thinking_budget: Optional[int] = -1 # -1 for dynamic according to the gemini docs
    # allow passthrough extras
    extras: Dict[str, Any] = None


@dataclass
class GenerationResult:
    output: Union[str, BaseModel]
    token_count: Optional[int] = None
    prompt_token_count: Optional[int] = None
    total_token_count: Optional[int] = None
    generation_time_sec: Optional[float] = None
    time_per_output_token_sec: Optional[float] = None
    time_per_total_token_sec: Optional[float] = None
    finish_reason: Optional[str] = None
    thoughts: Optional[str] = None
    char_count: Optional[int] = None
    word_count: Optional[int] = None
    sentence_count: Optional[int] = None


class LLM(ABC):
    """Abstract LLM adapter interface.

    Implementations should provide synchronous `generate` and an optional streaming
    `stream_generate` generator. The interface aims to cover both local models
    (transformers, vllm) and remote API models (OpenAI, HF inference, etc.).
    """

    def __init__(self, model_id: str):
        self.model_id = model_id

    @abstractmethod
    def generate(
        self,
        prompt: str,
        system_instruction: Optional[str],
        generation_params: Optional[GenerationParams],
    ) -> GenerationResult:
        pass


    def generate_stream(
        self,
        prompt: str,
        system_instruction: Optional[str],
        generation_params: Optional[GenerationParams],
    ) -> Iterator[str]:
        raise NotImplementedError()


    def tokenize(self, text: str) -> List[int]:
        raise NotImplementedError()

    def detokenize(self, token_ids: Sequence[int]) -> str:
        raise NotImplementedError()

    def get_input_token_limit(self) -> int:
        raise NotImplementedError()
    
    def get_output_token_limit(self) -> int:
        raise NotImplementedError()

    def close(self) -> None:
        return None
    
    @staticmethod
    def _text_stats(text: str | None) -> dict:
        if not text:
            return {
                "char_count": 0,
                "word_count": 0,
                "sentence_count": 0,
            }

        word_count = len(re.findall(r"\S+", text))
        sentence_count = len(re.findall(r"[^.!?\n]+[.!?]", text))
        if sentence_count == 0 and text.strip():
            sentence_count = 1

        return {
            "char_count": len(text),
            "word_count": word_count,
            "sentence_count": sentence_count,
        }
        
    @staticmethod    
    def _validate_schema(text: str, schema: BaseModel) -> BaseModel | None:
        try:
            validated = schema.model_validate_json(text)
            return validated
        except Exception as e:
            print("Error parsing LLM response with json schema:", e)
            with open("llm_response_error_debug.txt", "w") as f:
                f.write(f"Error parsing LLM response with json schema: {e}\n")
                f.write(f"Original output:\n{text}\n")
            return None