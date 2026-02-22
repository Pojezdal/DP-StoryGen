from __future__ import annotations

from enum import Enum
import os
from datetime import datetime
import re
import json
from pydantic import BaseModel

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
    
     
    def save_stage(self, stage: str, prompt: str, response: str, model: str, system_instruction: str, generation_params, thoughts: str = None):
        output_dict = dict(
            prompt=prompt,
            response=StoryDirectory.to_serializable(response),
            model=model,
            system_instruction=system_instruction,
            generation_params=StoryDirectory.to_serializable(generation_params) if generation_params else None,
            thoughts=thoughts
        )
        filename = os.path.join(self.path, f"{stage}.json")
        with open(filename, "w", encoding="utf-8") as file:
            json.dump(output_dict, file, ensure_ascii=False, indent=4)
    
    
    def load_stage(self, stage: str):
        filename = os.path.join(self.path, f"{stage}.json")
        with open(filename, "r", encoding="utf-8") as file:
            data = json.load(file)
            if "output" in data: # backward compatibility
                data["response"] = data.pop("output")
            if "generation_config" in data: # backward compatibility
                data["generation_params"] = data.pop("generation_config")
            return data
    
    
    def save_plain_text(self, stage: str, text: str):
        filename = os.path.join(self.path, f"{stage}.txt")
        with open(filename, "w", encoding="utf-8") as file:
            file.write(text)
    
    
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