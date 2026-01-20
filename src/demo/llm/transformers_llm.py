from __future__ import annotations
import json

from .llm import LLM, GenerationParams, GenerationResult
from enum import Enum
from threading import Thread
from transformers import BitsAndBytesConfig, GenerationConfig, TextIteratorStreamer
from transformers import AutoModelForCausalLM, AutoTokenizer
from typing import Iterable, Iterator, List, Optional, Sequence, Union, Dict, Any
from huggingface_hub import login


class TransformersLLM(LLM):    
    """Adapter for Hugging Face Transformers.
    """

    def __init__(self, model_id: str, quantization_config: Optional[BitsAndBytesConfig] = None, login_token: Optional[str] = None):
        super().__init__(model_id)
        # Delay heavy imports to runtime so module import is cheap
        if login_token:
            login(login_token)

        self.tokenizer = AutoTokenizer.from_pretrained(model_id)
        self.model = AutoModelForCausalLM.from_pretrained(model_id,
            quantization_config=quantization_config,
            device_map="auto"
        )
                                                          


    def generate(self, prompt: str, system_instruction: Optional[str] = None, generation_params: Optional[GenerationParams] = None) -> GenerationResult:
        generation_params = generation_params or GenerationParams()
        inputs = self.tokenizer.apply_chat_template(
            [
                {"role": "system", "content": system_instruction or ""},
                {"role": "user", "content": prompt},
            ],
            tokenize=True,
            add_generation_prompt=True,
            return_dict=True,
            return_tensors="pt",
        ).to(self.model.device)
        gen_config = GenerationConfig(
            do_sample=generation_params.do_sample,
            max_new_tokens=generation_params.max_tokens,
            temperature=generation_params.temperature,
            top_p=generation_params.top_p,
            top_k=generation_params.top_k,
            repetition_penalty=generation_params.repetition_penalty,
        )
        outputs = self.model.generate(**inputs, generation_config=gen_config)
        text = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
        return GenerationResult(
            text=text,
            token_count=len(outputs[0]),
        )
        
    def generate_stream(self, prompt, system_instruction : Optional[str] = None, generation_params: Optional[GenerationParams] = None, print_output: bool = False) -> GenerationResult:
        generation_params = generation_params or GenerationParams()
        
        if generation_params.response_type == "application/json":
            prompt += "\n\nRespond by filling the following JSON schema:\n"
            prompt += json.dumps(generation_params.response_schema.model_json_schema()) + "\n\n"
        
        inputs = self.tokenizer.apply_chat_template(
            [
                {"role": "system", "content": system_instruction or ""},
                {"role": "user", "content": prompt},
            ],
            tokenize=True,
            add_generation_prompt=True,
            return_dict=True,
            return_tensors="pt",
        ).to(self.model.device)
        
        gen_config = GenerationConfig(
            do_sample=generation_params.do_sample,
            max_new_tokens=generation_params.max_tokens,
            temperature=generation_params.temperature,
            top_p=generation_params.top_p,
            top_k=generation_params.top_k,
            repetition_penalty=generation_params.repetition_penalty,
        )
        streamer = TextIteratorStreamer(self.tokenizer, skip_prompt=True, skip_special_tokens=True)

        thread = Thread(target=self.model.generate, kwargs=dict(
            **inputs,
            generation_config=gen_config,
            streamer=streamer,
        ))
        thread.start()

        text = ""
        for new_text in streamer:
            text += new_text
            if print_output:
                print(new_text, end="", flush=True)
        thread.join()
        return GenerationResult(
            text=text,
            token_count=len(self.tokenizer.encode(text)),
        )


    def tokenize(self, text: str) -> Dict[str, Any]:
        return self.tokenizer(text, return_tensors="pt").to(self.model.device)


    def detokenize(self, token_ids: Sequence[int]) -> str:
        return self.tokenizer.decode(list(token_ids), skip_special_tokens=True)
    

    def get_input_token_limit(self) -> int:
        if self.tokenizer.model_max_length is not None:
            return self.tokenizer.model_max_length
        elif hasattr(self.model.config, "max_position_embeddings"):
            return self.model.config.max_position_embeddings
        else:
            raise NotImplementedError()