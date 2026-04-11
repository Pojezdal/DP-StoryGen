from __future__ import annotations

from dataclasses import dataclass
import hashlib
import importlib.util
from pathlib import Path
import re
import sys
from types import ModuleType
from typing import Any, Optional


_VALID_STAGE_NAME = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


class DataDict(dict):
    def __missing__(self, key):
        return ""


@dataclass(frozen=True)
class PromptParts:
    system_instruction: str
    prompt: str


class PromptBuilder:
    def __init__(
        self,
        prompts_dir: str | Path,
        enable_cache: bool = True,
    ):
        self.prompts_dir = Path(prompts_dir).resolve()
        self.enable_cache = enable_cache

        if not self.prompts_dir.exists() or not self.prompts_dir.is_dir():
            raise FileNotFoundError(
                f"Prompt directory does not exist or is not a folder: {self.prompts_dir}"
            )

        self._module_cache: dict[str, ModuleType] = {}
        self._base_module: Optional[ModuleType] = None

    def build_prompt(
        self,
        stage: str,
        data: Optional[dict[str, Any]] = None,
        system_override: Optional[str] = None,
        prompt_override: Optional[str] = None,
    ) -> PromptParts:
        stage_name = self._validate_stage_name(stage)
        stage_module = self._load_stage_module(stage_name)

        system_instruction = self._resolve_attr(
            stage_module=stage_module,
            attr_name="SYSTEM_INSTRUCTION",
            hard_default="",
        ) if system_override is None else system_override
        
        prompt_template = self._resolve_attr(
            stage_module=stage_module,
            attr_name="PROMPT_TEMPLATE",
            hard_default="",
        ) if prompt_override is None else prompt_override
        
        prompt_text = prompt_template.format_map(DataDict(data or {}))
        return PromptParts(system_instruction=system_instruction, prompt=prompt_text)


    def list_stages(self) -> list[str]:
        names: list[str] = []
        for file in self.prompts_dir.glob("*.py"):
            if file.is_file() and _VALID_STAGE_NAME.fullmatch(file.stem):
                names.append(file.stem)
        return sorted(names)


    def stage_exists(self, stage: str) -> bool:
        try:
            stage_name = self._validate_stage_name(stage)
        except ValueError:
            return False
        return self._module_path(stage_name).is_file()


    def _module_path(self, stage: str) -> Path:
        return self.prompts_dir / f"{stage}.py"


    def _validate_stage_name(self, stage: str) -> str:
        if not stage or not _VALID_STAGE_NAME.fullmatch(stage):
            raise ValueError(
                f"Invalid stage name '{stage}'. Stage must be a valid Python module identifier."
            )
        return stage


    def _resolve_attr(
        self,
        stage_module: ModuleType,
        attr_name: str,
        hard_default: Any,
    ) -> Any:
        stage_value = getattr(stage_module, attr_name, None)
        if stage_value is not None:
            return stage_value
        return hard_default
    

    def _load_stage_module(self, stage: str) -> ModuleType:
        module_path = self._module_path(stage)
        if not module_path.is_file():
            raise FileNotFoundError(f"Stage module not found: {module_path}")

        if self.enable_cache and stage in self._module_cache:
            return self._module_cache[stage]

        module = self._load_module_from_path(module_path=module_path, stage_name=stage)
        if self.enable_cache:
            self._module_cache[stage] = module
        return module


    def _load_module_from_path(self, module_path: Path, stage_name: str) -> ModuleType:
        unique_suffix = hashlib.sha1(str(module_path).encode("utf-8")).hexdigest()[:12]
        module_name = f"final_prompt_{stage_name}_{unique_suffix}"

        spec = importlib.util.spec_from_file_location(module_name, module_path)
        if spec is None or spec.loader is None:
            raise ImportError(f"Cannot create module spec for: {module_path}")

        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)
        return module


def build_prompt(
    stage: str,
    prompts_dir: str | Path,
    data: Optional[dict[str, Any]] = None,
    system_override: Optional[str] = None,
    prompt_override: Optional[str] = None,
) -> tuple[str, str]:
    builder = PromptBuilder(prompts_dir=prompts_dir)
    parts = builder.build_prompt(
        stage=stage,
        data=data,
        system_override=system_override,
        prompt_override=prompt_override,
    )
    return parts.system_instruction, parts.prompt


__all__ = ["PromptBuilder", "PromptParts", "build_prompt"]