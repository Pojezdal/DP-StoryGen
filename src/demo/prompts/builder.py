from __future__ import annotations

import importlib.util
import os
import sys
from types import ModuleType
from typing import Dict, Optional, Tuple


DEFAULT_MODULE_NAME = "default"


def _module_path_for_stage(stage: str) -> str:
    return os.path.join(os.path.dirname(__file__), f"{stage}.py")


def _load_module_from_path(path: str, name: Optional[str] = None) -> ModuleType:
    name = name or os.path.splitext(os.path.basename(path))[0]
    spec = importlib.util.spec_from_file_location(os.name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot create spec for {path}")
    module = importlib.util.module_from_spec(spec)
    # make imports inside the module relative to this package
    module.__package__ = __package__
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module

def _get_base_module() -> ModuleType:
    path = os.path.join(os.path.dirname(__file__), f"{DEFAULT_MODULE_NAME}.py")
    if not os.path.exists(path):
        raise FileNotFoundError(f"Base templates file not found: {path}")
    return _load_module_from_path(path, DEFAULT_MODULE_NAME)


def build_prompt(
    stage: str,
    data: Optional[Dict[str, object]] = None,
    system_override: Optional[str] = None,
    prompt_override: Optional[str] = None,
) -> Tuple[str, str]:
    data = dict(data or {})
    stage_path = _module_path_for_stage(stage)
    base = _get_base_module()
    
    if not os.path.exists(stage_path):
        raise FileNotFoundError(f"Stage module not found: {stage_path}")
    else:
        mod = _load_module_from_path(stage_path, stage)
        system_instruction = getattr(mod, "SYSTEM_INSTRUCTION", None)
        prompt_template = getattr(mod, "PROMPT_TEMPLATE", None)
        data_dict_cls = getattr(mod, "DataDict", None)
        
        if system_instruction is None:
            system_instruction = getattr(base, "SYSTEM_INSTRUCTION", "")
        if prompt_template is None:
            prompt_template = getattr(base, "PROMPT_TEMPLATE", "")
        if data_dict_cls is None:
            data_dict_cls = getattr(base, "DataDict")
            
    if system_override is not None:
        system_instruction = system_override
    if prompt_override is not None:
        prompt_template = prompt_override
        
    prompt_text = prompt_template.format_map(data_dict_cls(data))
    return system_instruction, prompt_text

__all__ = ["build_prompt"]