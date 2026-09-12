from __future__ import annotations

import base64
import contextlib
import io
from pathlib import Path
import struct
import sys
import tempfile
import unittest


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_ROOT = REPO_ROOT / "image-generation-installer" / "skill" / "custom-image-generation" / "scripts"
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

from image_generation import ImageInfo, _inspect_image_bytes, _write_response_images  # noqa: E402


def _png(width: int, height: int, color_type: int = 2) -> bytes:
    ihdr = struct.pack(">IIBBBBB", width, height, 8, color_type, 0, 0, 0)
    return b"\x89PNG\r\n\x1a\n" + struct.pack(">I", len(ihdr)) + b"IHDR" + ihdr + b"\x00\x00\x00\x00"


class OutputValidationTests(unittest.TestCase):
    def test_inspects_png_dimensions_and_alpha(self) -> None:
        self.assertEqual(_inspect_image_bytes(_png(1254, 1254)), ImageInfo("png", 1254, 1254, False))
        self.assertEqual(_inspect_image_bytes(_png(1312, 1199, 6)), ImageInfo("png", 1312, 1199, True))

    def test_inspects_jpeg_dimensions(self) -> None:
        jpeg = b"\xff\xd8\xff\xc0" + struct.pack(">H", 17) + b"\x08" + struct.pack(">HH", 941, 1672) + b"\x03" + b"\x00" * 10
        self.assertEqual(_inspect_image_bytes(jpeg), ImageInfo("jpeg", 1672, 941, False))

    def test_inspects_webp_dimensions(self) -> None:
        vp8x = b"\x00\x00\x00\x00" + (2047).to_bytes(3, "little") + (1023).to_bytes(3, "little")
        webp = b"RIFF" + struct.pack("<I", 20) + b"WEBP" + b"VP8X" + struct.pack("<I", len(vp8x)) + vp8x
        self.assertEqual(_inspect_image_bytes(webp), ImageInfo("webp", 2048, 1024, False))

        vp8 = b"\x00\x00\x00\x9d\x01\x2a" + (640).to_bytes(2, "little") + (480).to_bytes(2, "little")
        webp_lossy = b"RIFF" + struct.pack("<I", 20) + b"WEBP" + b"VP8 " + struct.pack("<I", len(vp8)) + vp8
        self.assertEqual(_inspect_image_bytes(webp_lossy), ImageInfo("webp", 640, 480, False))

    def test_mismatch_warns_but_preserves_requested_path_and_writes(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_dir:
            output = Path(temporary_dir) / "result.jpg"
            response = {"data": [{"b64_json": base64.b64encode(_png(1254, 1254)).decode("ascii")}]}
            warning = io.StringIO()

            with contextlib.redirect_stderr(warning):
                _write_response_images(
                    response,
                    [output],
                    force=False,
                    timeout=10,
                    expected_format="jpeg",
                    expected_size="2048x2048",
                )

            self.assertTrue(output.is_file())
            self.assertTrue(output.read_bytes().startswith(b"\x89PNG"))
            message = warning.getvalue()
            self.assertIn("请求格式为 JPEG，实际返回 PNG", message)
            self.assertIn("请求尺寸为 2048x2048，实际返回 1254x1254", message)
            self.assertIn("仍按原路径保存，不会中断流程", message)

    def test_unknown_result_still_writes_and_only_warns(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_dir:
            output = Path(temporary_dir) / "result.png"
            warning = io.StringIO()
            with contextlib.redirect_stderr(warning):
                _write_response_images(
                    {"data": [{"b64_json": base64.b64encode(b"not-an-image").decode("ascii")}]},
                    [output],
                    force=False,
                    timeout=10,
                    expected_format="png",
                )

            self.assertEqual(output.read_bytes(), b"not-an-image")
            self.assertIn("无法识别", warning.getvalue())


if __name__ == "__main__":
    unittest.main()
