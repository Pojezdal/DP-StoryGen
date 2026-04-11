from __future__ import annotations

from enum import Enum
import os
from datetime import datetime
import re
import json
from pydantic import BaseModel

from demo.llm.llm import GenerationParams, GenerationResult

class StoryDirectory:
    def __init__(self, path: str):
        self.path = path
    
    
    @classmethod
    def new(cls, title : str, base_dir: str = "Stories") -> StoryDirectory:
        timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
        title_sanitized = re.sub(r'[\\/*?:"<>|]', "", title)[:120].strip().replace(" ", "_").lower()
        path = os.path.join(base_dir, f"{timestamp}_{title_sanitized}")
        os.makedirs(path, exist_ok=True)
        return cls(path)
    
    
    @classmethod
    def open(cls, title: str, base_dir: str = "Stories") -> StoryDirectory:
        path = os.path.join(base_dir, title)
        if os.path.exists(path):
            return cls(path)
        else:
            norm = os.path.normpath(path)
            parent = os.path.dirname(norm)
            name = os.path.basename(norm)
            if not os.path.isdir(parent):
                raise FileNotFoundError(f"No such directory: {path}")
            title_sanitized = re.sub(r'[\\/*?:"<>|]', "", name)[:120].strip().replace(" ", "_").lower()
            pattern = re.compile(rf'^\d{{4}}-\d{{2}}-\d{{2}}_\d{{6}}_{re.escape(title_sanitized)}$')
            candidates = [
                d for d in os.listdir(parent)
                if os.path.isdir(os.path.join(parent, d)) and pattern.match(d)
            ]
            if not candidates:
                raise FileNotFoundError(f"No such directory: {path}")
            candidates.sort()
            chosen = candidates[-1] # most recent
            return cls(os.path.join(parent, chosen))
    
     
    def save_stage(self, stage: str, model: str, prompt: str, system_instruction: str, generation_params: GenerationParams, generation_result: GenerationResult):
        serialized_generation_result = StoryDirectory.to_serializable(generation_result)
        response = generation_result.output if isinstance(generation_result.output, str) else None
        response_stats = StoryDirectory._text_stats(response)

        # Keep stats inside generation_result where token stats already live.
        if isinstance(serialized_generation_result, dict):
            serialized_generation_result.update(response_stats)

        output_dict = dict(
            model=model,
            prompt=prompt,
            system_instruction=system_instruction,
            generation_result=serialized_generation_result,
            generation_params=StoryDirectory.to_serializable(generation_params) if generation_params else None,
            response_stats=response_stats,
        )

        base_stage, index = self._next_stage_index(stage)
        filename = os.path.join(self.path, f"{base_stage}.json")
        with open(filename, "w", encoding="utf-8") as file:
            json.dump(output_dict, file, ensure_ascii=False, indent=4)
        
        # If the response is plain text, also save a readable .txt file
        if isinstance(response, str):
            self.save_plain_text(base_stage, response)
    
    
    def load_stage(self, stage: str, index: int | None = None, filename: str | None = None):
        if filename:
            json_path = os.path.join(self.path, filename)
        else:
            json_path = self._select_stage_file(stage, index)

        if json_path and os.path.exists(json_path):
            with open(json_path, "r", encoding="utf-8") as file:
                data = json.load(file)
                if "output" in data: # backward compatibility
                    data["response"] = data.pop("output")
                if "generation_config" in data: # backward compatibility
                    data["generation_params"] = data.pop("generation_config")
                if not "response" in data and "generation_result" in data and "output" in data["generation_result"]:
                    data["response"] = data["generation_result"]["output"]

                # Backward compatibility: older outputs may miss text-length stats.
                response_text = data.get("response") if isinstance(data.get("response"), str) else None
                stats = StoryDirectory._text_stats(response_text)
                if "response_stats" not in data:
                    data["response_stats"] = stats
                if isinstance(data.get("generation_result"), dict):
                    result_obj = data["generation_result"]
                    result_obj.setdefault("character_count", stats["character_count"])
                    result_obj.setdefault("word_count", stats["word_count"])
                    result_obj.setdefault("sentence_count", stats["sentence_count"])
                return data

        if filename:
            alternative_filename = os.path.join(self.path, filename)
        else:
            alternative_filename = self._select_stage_file(stage, index, extension=".txt")

        if alternative_filename and os.path.exists(alternative_filename):
            with open(alternative_filename, "r", encoding="utf-8") as file:
                text = file.read()
            return {
                "response": text,
                "response_stats": StoryDirectory._text_stats(text),
            }
    
    
    def save_plain_text(self, stage: str, text: str):
        filename = os.path.join(self.path, f"{stage}.txt")
        with open(filename, "w", encoding="utf-8") as file:
            file.write(text)


    def _next_stage_index(self, stage: str):
        existing = self._list_stage_indices(stage)
        if not existing:
            return stage, 0
        next_index = max(existing) + 1
        return f"{stage}_{next_index}", next_index


    def _select_stage_file(self, stage: str, index: int | None, extension: str = ".json"):
        if index is None:
            existing = self._list_stage_indices(stage, extension=extension)
            if not existing:
                return os.path.join(self.path, f"{stage}{extension}")
            chosen = max(existing)
        else:
            chosen = index

        suffix = "" if chosen == 0 else f"_{chosen}"
        return os.path.join(self.path, f"{stage}{suffix}{extension}")


    def _list_stage_indices(self, stage: str, extension: str = ".json"):
        pattern = re.compile(rf"^{re.escape(stage)}(?:_(\d+))?{re.escape(extension)}$")
        indices = []
        for name in os.listdir(self.path):
            match = pattern.match(name)
            if not match:
                continue
            idx = match.group(1)
            indices.append(int(idx) if idx is not None else 0)
        return indices
    
    
    @staticmethod
    def _text_stats(text: str | None) -> dict:
        if not text:
            return {
                "character_count": 0,
                "word_count": 0,
                "sentence_count": 0,
            }

        word_count = len(re.findall(r"\S+", text))
        sentence_count = len(re.findall(r"[^.!?\n]+[.!?]", text))
        if sentence_count == 0 and text.strip():
            sentence_count = 1

        return {
            "character_count": len(text),
            "word_count": word_count,
            "sentence_count": sentence_count,
        }

    @staticmethod
    def to_serializable(obj):
        if isinstance(obj, dict):
            return {k: StoryDirectory.to_serializable(v) for k, v in obj.items()}
        elif isinstance(obj, (list, tuple)):
            return [StoryDirectory.to_serializable(v) for v in obj]
        elif isinstance(obj, type) and issubclass(obj, BaseModel):
            return obj.model_json_schema()
        elif isinstance(obj, Enum):
            return obj.value
        elif hasattr(obj, "__dict__"):
            return {k: StoryDirectory.to_serializable(v) for k, v in obj.__dict__.items()}
        else:
            return obj