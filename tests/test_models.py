from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from types import SimpleNamespace


REPO_ROOT = Path(__file__).resolve().parents[1]
SKILL_ROOT = REPO_ROOT / "image-generation-installer" / "skill" / "custom-image-generation"
SCRIPTS_ROOT = SKILL_ROOT / "scripts"
CLI = SCRIPTS_ROOT / "image_generation.py"

if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

from models import DEFAULT_MODEL, get_model_spec, supported_model_ids  # noqa: E402


NEW_MODELS = (
    "gpt-image-2.5",
    "gpt-image-2.5-flare",
    "gpt-image-2.5-sunburst",
)
ALL_MODELS = (*NEW_MODELS, "gpt-image-2")


def _args(*, quality: str = "medium", background: str | None = None, output_format: str = "png"):
    return SimpleNamespace(
        n=1,
        size="1024x1024",
        quality=quality,
        background=background,
        output_format=output_format,
        output_compression=None,
        moderation=None,
        user=None,
    )


class ModelSpecTests(unittest.TestCase):
    def test_registry_contains_three_new_models_and_compatibility_model(self) -> None:
        self.assertEqual(tuple(supported_model_ids()), tuple(sorted(ALL_MODELS)))
        self.assertEqual(DEFAULT_MODEL, "gpt-image-2.5")

    def test_new_models_accept_extended_quality_and_transparency(self) -> None:
        for model_id in NEW_MODELS:
            spec = get_model_spec(model_id)
            for quality in ("xhigh", "max"):
                payload = spec.build_generate_payload(_args(quality=quality), "test prompt", {})
                self.assertEqual(payload["model"], model_id)
                self.assertEqual(payload["quality"], quality)

            payload = spec.build_generate_payload(
                _args(background="transparent", output_format="webp"),
                "transparent test",
                {},
            )
            self.assertEqual(payload["background"], "transparent")
            self.assertEqual(payload["output_format"], "webp")

    def test_new_models_reject_transparent_jpeg(self) -> None:
        for model_id in NEW_MODELS:
            with self.assertRaisesRegex(ValueError, "requires --output-format png or webp"):
                get_model_spec(model_id).build_generate_payload(
                    _args(background="transparent", output_format="jpeg"),
                    "test prompt",
                    {},
                )

    def test_compatibility_model_keeps_narrower_rules(self) -> None:
        spec = get_model_spec("gpt-image-2")
        with self.assertRaisesRegex(ValueError, "quality must be one of"):
            spec.build_generate_payload(_args(quality="xhigh"), "test prompt", {})
        with self.assertRaisesRegex(ValueError, "does not support background=transparent"):
            spec.build_generate_payload(_args(background="transparent"), "test prompt", {})

    def test_cli_dry_run_dispatches_each_model(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_dir:
            root = Path(temporary_dir)
            config = root / "config.json"
            config.write_text(
                json.dumps(
                    {
                        "api_url": "https://api.example.com/v1",
                        "api_key": "test-key-that-must-not-print",
                    }
                ),
                encoding="utf-8",
            )
            for model_id in ALL_MODELS:
                result = subprocess.run(
                    [
                        sys.executable,
                        str(CLI),
                        "generate",
                        "--config-file",
                        str(config),
                        "--prompt",
                        "test prompt",
                        "--model",
                        model_id,
                        "--dry-run",
                        "--out",
                        str(root / f"{model_id}.png"),
                    ],
                    check=True,
                    capture_output=True,
                    text=True,
                )
                self.assertNotIn("test-key-that-must-not-print", result.stdout + result.stderr)
                payload = json.loads(result.stdout)
                self.assertEqual(payload["payload"]["model"], model_id)

    def test_cli_dry_run_edit_preserves_new_model_fields(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_dir:
            root = Path(temporary_dir)
            config = root / "config.json"
            image = root / "input.png"
            mask = root / "mask.png"
            config.write_text(
                json.dumps({"api_url": "https://api.example.com/v1", "api_key": "edit-test-key"}),
                encoding="utf-8",
            )
            image.write_bytes(b"png-fixture")
            mask.write_bytes(b"mask-fixture")

            result = subprocess.run(
                [
                    sys.executable,
                    str(CLI),
                    "edit",
                    "--config-file",
                    str(config),
                    "--prompt",
                    "edit prompt",
                    "--model",
                    "gpt-image-2.5-sunburst",
                    "--quality",
                    "max",
                    "--background",
                    "transparent",
                    "--output-format",
                    "png",
                    "--image",
                    str(image),
                    "--mask",
                    str(mask),
                    "--dry-run",
                    "--out",
                    str(root / "edited.png"),
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            payload = json.loads(result.stdout)
            self.assertEqual(payload["fields"]["model"], "gpt-image-2.5-sunburst")
            self.assertEqual(payload["fields"]["quality"], "max")
            self.assertEqual(payload["fields"]["background"], "transparent")
            self.assertEqual(len(payload["files"]), 2)


if __name__ == "__main__":
    unittest.main()
