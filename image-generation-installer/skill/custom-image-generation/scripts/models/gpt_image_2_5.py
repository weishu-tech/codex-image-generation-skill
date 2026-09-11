"""GPT Image 2.5 model specifications."""

from __future__ import annotations

from .gpt_image_common import GPTImageSpec


GPT_IMAGE_2_5_QUALITIES = frozenset({"low", "medium", "high", "xhigh", "max", "auto"})

GPT_IMAGE_2_5_SPEC = GPTImageSpec(
    "gpt-image-2.5",
    allowed_qualities=GPT_IMAGE_2_5_QUALITIES,
    supports_transparent_background=True,
)

GPT_IMAGE_2_5_FLARE_SPEC = GPTImageSpec(
    "gpt-image-2.5-flare",
    allowed_qualities=GPT_IMAGE_2_5_QUALITIES,
    supports_transparent_background=True,
)

GPT_IMAGE_2_5_SUNBURST_SPEC = GPTImageSpec(
    "gpt-image-2.5-sunburst",
    allowed_qualities=GPT_IMAGE_2_5_QUALITIES,
    supports_transparent_background=True,
)
