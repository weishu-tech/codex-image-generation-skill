"""Model registry for Custom Image Generation."""

from __future__ import annotations

from typing import Dict, Iterable, Optional, Protocol

from .gpt_image_2 import SPEC as GPT_IMAGE_2_SPEC
from .gpt_image_2_5 import (
    GPT_IMAGE_2_5_FLARE_SPEC,
    GPT_IMAGE_2_5_SPEC,
    GPT_IMAGE_2_5_SUNBURST_SPEC,
)


class ModelSpec(Protocol):
    model_id: str
    default_output_format: str

    def add_generate_arguments(self, parser) -> None: ...

    def add_edit_arguments(self, parser) -> None: ...

    def normalize_output_format(self, value: Optional[str]) -> str: ...

    def output_count(self, args) -> int: ...

    def build_generate_payload(self, args, prompt: str, extra_json: dict) -> dict: ...

    def build_edit_payload(self, args, prompt: str, extra_json: dict) -> dict: ...


MODEL_SPECS: Dict[str, ModelSpec] = {
    GPT_IMAGE_2_SPEC.model_id: GPT_IMAGE_2_SPEC,
    GPT_IMAGE_2_5_SPEC.model_id: GPT_IMAGE_2_5_SPEC,
    GPT_IMAGE_2_5_FLARE_SPEC.model_id: GPT_IMAGE_2_5_FLARE_SPEC,
    GPT_IMAGE_2_5_SUNBURST_SPEC.model_id: GPT_IMAGE_2_5_SUNBURST_SPEC,
}

DEFAULT_MODEL = GPT_IMAGE_2_5_SPEC.model_id


def supported_model_ids() -> Iterable[str]:
    return sorted(MODEL_SPECS)


def get_model_spec(model_id: str) -> ModelSpec:
    try:
        return MODEL_SPECS[model_id]
    except KeyError as exc:
        supported = ", ".join(supported_model_ids())
        raise ValueError(f"Unsupported model: {model_id}. Supported models: {supported}") from exc
