"""gpt-image-2 parameter definitions for Custom Image Generation."""

from __future__ import annotations

from .gpt_image_common import GPTImageSpec


SPEC = GPTImageSpec(
    "gpt-image-2",
    allowed_qualities=frozenset({"low", "medium", "high", "auto"}),
    supports_transparent_background=False,
)
