"""gpt-image-2 parameter definitions for Custom Image Generation."""

from __future__ import annotations

from typing import Any, Dict, Optional, Tuple
import re


MODEL_ID = "gpt-image-2"
DEFAULT_SIZE = "auto"
DEFAULT_QUALITY = "medium"
DEFAULT_OUTPUT_FORMAT = "png"

ALLOWED_QUALITIES = {"low", "medium", "high", "auto"}
ALLOWED_BACKGROUNDS = {"opaque", "auto", "transparent", None}
ALLOWED_OUTPUT_FORMATS = {"png", "jpeg", "jpg", "webp"}
GPT_IMAGE_2_MIN_PIXELS = 655_360
GPT_IMAGE_2_MAX_PIXELS = 8_294_400
GPT_IMAGE_2_MAX_EDGE = 3840
GPT_IMAGE_2_MAX_RATIO = 3.0


def _die(message: str) -> None:
    raise ValueError(message)


def _payload_add(payload: Dict[str, Any], key: str, value: Any) -> None:
    if value is None:
        return
    if isinstance(value, str) and value == "":
        return
    payload[key] = value


def _parse_size(size: str) -> Optional[Tuple[int, int]]:
    match = re.fullmatch(r"([1-9][0-9]*)x([1-9][0-9]*)", size)
    if not match:
        return None
    return int(match.group(1)), int(match.group(2))


class GPTImage2Spec:
    model_id = MODEL_ID
    default_output_format = DEFAULT_OUTPUT_FORMAT

    def add_generate_arguments(self, parser) -> None:
        self._add_common_arguments(parser)

    def add_edit_arguments(self, parser) -> None:
        self._add_common_arguments(parser)

    def _add_common_arguments(self, parser) -> None:
        parser.add_argument("--n", type=int, default=1)
        parser.add_argument("--size", default=DEFAULT_SIZE)
        parser.add_argument("--quality", default=DEFAULT_QUALITY)
        parser.add_argument("--background")
        parser.add_argument("--output-format", default=DEFAULT_OUTPUT_FORMAT)
        parser.add_argument("--output-compression", type=int)
        parser.add_argument("--moderation")
        parser.add_argument("--user")

    def normalize_output_format(self, value: Optional[str]) -> str:
        if not value:
            return DEFAULT_OUTPUT_FORMAT
        normalized = value.lower().strip()
        if normalized == "jpg":
            return "jpeg"
        return normalized

    def output_count(self, args) -> int:
        return int(args.n or 1)

    def build_generate_payload(self, args, prompt: str, extra_json: dict) -> dict:
        self._validate_common(args)
        payload = self._base_payload(args, prompt)
        payload.update(extra_json)
        return payload

    def build_edit_payload(self, args, prompt: str, extra_json: dict) -> dict:
        self._validate_common(args)
        payload = self._base_payload(args, prompt)
        payload.update(extra_json)
        return payload

    def _base_payload(self, args, prompt: str) -> dict:
        output_format = self.normalize_output_format(args.output_format)
        payload: Dict[str, Any] = {"model": self.model_id, "prompt": prompt}
        _payload_add(payload, "n", args.n)
        _payload_add(payload, "size", args.size)
        _payload_add(payload, "quality", args.quality)
        _payload_add(payload, "background", args.background)
        _payload_add(payload, "output_format", output_format)
        _payload_add(payload, "output_compression", args.output_compression)
        _payload_add(payload, "moderation", args.moderation)
        _payload_add(payload, "user", args.user)
        return payload

    def _validate_common(self, args) -> None:
        n = int(args.n or 1)
        if n < 1 or n > 10:
            _die("--n must be between 1 and 10.")

        quality = str(args.quality or DEFAULT_QUALITY)
        if quality not in ALLOWED_QUALITIES:
            _die("--quality must be one of low, medium, high, or auto for gpt-image-2.")

        background = args.background
        if background not in ALLOWED_BACKGROUNDS:
            _die("--background must be one of opaque, auto, or transparent.")
        if background == "transparent":
            _die(
                "gpt-image-2 does not support background=transparent. "
                "Use opaque/auto or add a future model file that supports true transparency."
            )

        output_format = self.normalize_output_format(args.output_format)
        if output_format not in {"png", "jpeg", "webp"}:
            _die("--output-format must be png, jpeg, jpg, or webp.")

        compression = args.output_compression
        if compression is not None:
            if not (0 <= int(compression) <= 100):
                _die("--output-compression must be between 0 and 100.")
            if output_format == "png":
                _die("--output-compression is only valid with jpeg or webp for gpt-image-2.")

        self._validate_size(str(args.size or DEFAULT_SIZE))

    def _validate_size(self, size: str) -> None:
        if size == "auto":
            return

        parsed = _parse_size(size)
        if parsed is None:
            _die("--size must be auto or WIDTHxHEIGHT, for example 1024x1024.")

        width, height = parsed
        max_edge = max(width, height)
        min_edge = min(width, height)
        total_pixels = width * height

        if max_edge > GPT_IMAGE_2_MAX_EDGE:
            _die("gpt-image-2 size maximum edge length must be less than or equal to 3840px.")
        if width % 16 != 0 or height % 16 != 0:
            _die("gpt-image-2 size width and height must be multiples of 16px.")
        if max_edge / min_edge > GPT_IMAGE_2_MAX_RATIO:
            _die("gpt-image-2 size long edge to short edge ratio must not exceed 3:1.")
        if total_pixels < GPT_IMAGE_2_MIN_PIXELS or total_pixels > GPT_IMAGE_2_MAX_PIXELS:
            _die(
                "gpt-image-2 size total pixels must be at least 655,360 "
                "and no more than 8,294,400."
            )


SPEC = GPTImage2Spec()
