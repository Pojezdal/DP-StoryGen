from __future__ import annotations

from pathlib import Path
from enum import Enum
import os
from datetime import datetime
import re
import json
from pydantic import BaseModel

from final.llm.llm import GenerationParams, GenerationResult


class StoryDirectory:
    def __init__(self, path: Path):
        self.path = path
    
    
    @classmethod
    def new(cls, title : str = "", base_dir: str = "stories") -> StoryDirectory:
        timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
        if title:
            title_sanitized = re.sub(r'[\\/*?:"<>|]', "", title)[:120].strip().replace(" ", "_").lower()
            path = Path(base_dir) / f"{timestamp}_{title_sanitized}"
        else:
            path = Path(base_dir) / timestamp
        os.makedirs(path, exist_ok=True)
        return cls(path)
    
    
    @classmethod
    def open(cls, title: str, base_dir: str = "stories") -> StoryDirectory:
        path = Path(base_dir) / title
        if os.path.exists(path):
            return cls(path)
        else:
            return cls.new(title=title, base_dir=base_dir)
        
    
    def save_json(self, filename: str, data: dict):
        filepath = self.path / filename
        with open(filepath, "w", encoding="utf-8") as file:
            json.dump(data, file, ensure_ascii=False, indent=4)
    
    
    def save_plain(self, filename: str, text: str):
        filepath = self.path / filename
        with open(filepath, "w", encoding="utf-8") as file:
            file.write(text)
    
    
    def save_stage(self, stage: str, data: dict, plain_data : str | None = None):
        if plain_data is not None:
            data["output"] = plain_data
        
        index = self._next_stage_index(stage)
        self.save_json(f"{stage}_{index:02d}.json", data)
        
        if plain_data:
            self.save_plain(f"{stage}_{index:02d}.txt", plain_data)
    
    
    def save_stage_llm(self, stage: str, model: str, prompt: str, system_instruction: str, generation_params: GenerationParams, generation_result: GenerationResult, save_plain_text: bool = True):
        serializable_output = self._to_serializable(generation_result.output)

        plain_text: str | None = None
        if save_plain_text and generation_result.output is not None:
            if isinstance(serializable_output, (dict, list)):
                plain_text = json.dumps(serializable_output, ensure_ascii=False, indent=2)
            elif isinstance(serializable_output, str):
                plain_text = serializable_output
            else:
                plain_text = str(serializable_output)

        data = dict(
            model=model,
            prompt=prompt,
            system_instruction=system_instruction,
            generation_result=StoryDirectory._to_serializable(generation_result),
            generation_params=StoryDirectory._to_serializable(generation_params) if generation_params else None,
        )
        self.save_stage(stage, data, plain_data=plain_text)
    
    
    def load_stage(self, stage: str, index: int | None = None, filename: str | None = None) -> tuple[dict | None, str | None]:
        data = None
        plain_data = None
        
        if filename:
            json_path = self.path / f"{filename}.json"
        else:
            file = self._select_stage_file(stage, index)
            json_path = self.path / file if file else None

        if json_path and os.path.exists(json_path):
            with open(json_path, "r", encoding="utf-8") as file:
                data = json.load(file)

        if filename:
            plain_path = self.path / f"{filename}.txt"
        else:
            file = self._select_stage_file(stage, index, extension=".txt")
            plain_path = self.path / file if file else None

        if plain_path and os.path.exists(plain_path):
            with open(plain_path, "r", encoding="utf-8") as file:
                plain_data = file.read()
        
        return data, (plain_data or (data["output"] if data and "output" in data else None))
    
    
    def _next_stage_index(self, stage: str) ->int:
        existing = self._list_stage_indices(stage)
        if not existing:
            return 0
        next_index = max(existing) + 1
        return next_index


    def _select_stage_file(self, stage: str, index: int | None, extension: str = ".json") -> str | None:
        if index is None:
            existing = self._list_stage_indices(stage, extension=extension)
            if not existing:
                return None
            chosen = max(existing)
        else:
            chosen = index

        return f"{stage}_{chosen:02d}{extension}"


    def _list_stage_indices(self, stage: str, extension: str = ".json") -> list[int]:
        pattern = re.compile(rf"^{re.escape(stage)}(?:_(\d+))?{re.escape(extension)}$")
        indices = []
        for name in os.listdir(self.path):
            match = pattern.match(name)
            if not match:
                continue
            index = int(match.group(1)) if match.group(1) is not None else 0
            indices.append(index)
        return indices


    @staticmethod
    def _to_serializable(obj):
        if isinstance(obj, dict):
            return {k: StoryDirectory._to_serializable(v) for k, v in obj.items()}
        elif isinstance(obj, (list, tuple)):
            return [StoryDirectory._to_serializable(v) for v in obj]
        elif isinstance(obj, type) and issubclass(obj, BaseModel):
            return obj.model_json_schema()
        elif isinstance(obj, Enum):
            return obj.value
        elif hasattr(obj, "__dict__"):
            return {k: StoryDirectory._to_serializable(v) for k, v in obj.__dict__.items()}
        else:
            return obj