from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Iterable, Iterator, List, Optional, Sequence, Union, Dict, Any

from pydantic import BaseModel


@dataclass
class GenerationParams:
    temperature: float = 0.7
    do_sample: bool = True
    top_p: float = 1.0
    top_k: int = 0
    max_tokens: int = 128
    repetition_penalty: float = 1.0
    response_type: str = "text/plain"
    response_schema: Optional[BaseModel] = None
    # allow passthrough extras
    extras: Dict[str, Any] = None


@dataclass
class GenerationResult:
    output: Union[str, BaseModel]
    token_count: Optional[int] = None
    prompt_token_count: Optional[int] = None
    finish_reason: Optional[str] = None


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
        system_instruction: Optional[str] = None,
        generation_params: Optional[GenerationParams] = None,
    ) -> GenerationResult:
        pass


    def generate_stream(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        generation_params: Optional[GenerationParams] = None,
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