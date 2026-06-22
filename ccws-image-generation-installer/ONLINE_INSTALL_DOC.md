# CCWS Image Generation Codex Skill Online Install Guide

Use this document when a user gives an AI assistant an online page instead of a downloaded installer package. The AI assistant should follow the same install contract as the packaged installer.

## Goal

Install a Codex skill named `ccws-image-generation` that replaces the built-in AI image generation path with CCWS Image Generation.

Required behavior:

- Use base URL `https://www.ccws.pro/`.
- Use only `CCWS_IMAGE_API_KEY` for authentication.
- Support image generation and image editing.
- Currently support `gpt-image-2`.
- Keep model-specific parameter rules separate from the main CLI.
- Report detailed errors and include the skill version.
- On request/provider failures, include `请在售后群咨询。`
- Current version: `1.0.0`.

## AI Installation Procedure

Follow these steps in order.

### 1. Check Existing Image Generation Skills

Inspect the local Codex skills directory:

- `$CODEX_HOME/skills` when `CODEX_HOME` is set.
- `~/.codex/skills` otherwise.

Look for image generation skills by checking `SKILL.md` files and folder names for terms such as:

- `imagegen`
- `image generation`
- `AI image`
- `images/generations`
- `images/edits`
- `生图`
- `图像生成`
- `生成图片`

The official built-in image skill is usually:

```text
~/.codex/skills/.system/imagegen
```

If any other non-official image generation skills exist, recommend that the user uninstall or move them first to avoid trigger conflicts. The user may explicitly choose to continue anyway.

### 2. Require CCWS_IMAGE_API_KEY

Ask the user to create a CCWSPro image generation group API key in the CCWSPro console. The token must include access to:

```text
model: gpt-image-2
```

Then require the user to configure:

```text
CCWS_IMAGE_API_KEY
```

Do not proceed until the current shell/session can read `CCWS_IMAGE_API_KEY`. Do not accept `OPENAI_API_KEY`, `auth.json`, or pasted secrets as substitutes.

Temporary setup:

```bash
# macOS / Linux
export CCWS_IMAGE_API_KEY="your-ccws-token"

# Windows PowerShell
$env:CCWS_IMAGE_API_KEY="your-ccws-token"

# Windows CMD
set CCWS_IMAGE_API_KEY=your-ccws-token
```

Persistent setup:

```bash
# macOS / Linux zsh
echo 'export CCWS_IMAGE_API_KEY="your-ccws-token"' >> ~/.zshrc
source ~/.zshrc

# macOS / Linux bash
echo 'export CCWS_IMAGE_API_KEY="your-ccws-token"' >> ~/.bashrc
source ~/.bashrc
```

Windows PowerShell persistent setup:

```powershell
[Environment]::SetEnvironmentVariable("CCWS_IMAGE_API_KEY", "your-ccws-token", "User")
```

After persistent setup, the user may need to restart the terminal or Codex.

### 3. Install The Skill

Preferred path:

```text
~/.codex/skills/ccws-image-generation
```

If `CODEX_HOME` is set, install to:

```text
$CODEX_HOME/skills/ccws-image-generation
```

Create this structure:

```text
ccws-image-generation/
  SKILL.md
  VERSION
  agents/openai.yaml
  references/api.md
  scripts/
    ccws_image_generation.py
    models/
      __init__.py
      gpt_image_2.py
```

If an existing `ccws-image-generation` skill exists, back it up or replace it according to the user's instruction.

If the downloaded installer package is available, run:

```bash
python3 install.py --yes
```

Windows PowerShell:

```powershell
py -3 .\install.py --yes
```

### 4. Finish

After successful installation, tell the user:

```text
CCWS Image Generation skill is installed. Please open a new Codex conversation or restart Codex, then try image generation again.
```

## Safety Rules

- Never print or repeat the user's API key.
- Never proceed to installation when `CCWS_IMAGE_API_KEY` is missing.
- Keep `VERSION` as the canonical version source.
- Do not add fallback authentication paths.
- Preserve detailed error output for support diagnostics.

## Self-contained Skill Files

If the installer package is unavailable, recreate the skill by writing the following files under `ccws-image-generation/`. Preserve paths and file contents exactly.

### `SKILL.md`

````markdown
---
name: ccws-image-generation
description: Generate or edit AI raster images through the CCWS Image Generation flow at https://www.ccws.pro/. Use this skill for all AI image generation, image editing, image variation, image-to-image, inpainting, background replacement, and transparent-background image tasks, including requests that would otherwise use imagegen. This skill replaces the built-in imagegen path for AI image work.
---

# CCWS Image Generation

Version: `1.0.0`

Use this skill for all AI image generation and AI image editing tasks. It is the CCWS-backed replacement for the built-in `imagegen` path.

The bundled CLI entrypoint is `scripts/ccws_image_generation.py`. It uses:

- Base URL: `https://www.ccws.pro/`
- Default API prefix: `/v1`
- Generation endpoint: `https://www.ccws.pro/v1/images/generations`
- Edit endpoint: `https://www.ccws.pro/v1/images/edits`

The version source is `VERSION`. Check it with:

```bash
python ~/.codex/skills/ccws-image-generation/scripts/ccws_image_generation.py --version
```

If CCWS expects paths without `/v1`, retry with `--api-prefix ""` or set `CCWS_IMAGE_API_PREFIX=""`.

## Workflow

1. Decide whether the task is generation or editing.
2. For editing local files, inspect the image first when visual preservation matters.
3. Use `scripts/ccws_image_generation.py generate` for new images and `scripts/ccws_image_generation.py edit` for modifying source images.
4. Write final images under the current project, usually `output/ccws-image-generation/`.
5. Use `--dry-run` first when changing base URL, API prefix, model, transparency, or multipart field names.
6. Never print API keys. The script reads only `CCWS_IMAGE_API_KEY`.
7. If generation or editing fails, preserve the script's detailed error output. It includes endpoint, HTTP status, response body, request id when present, and `请在售后群咨询。`

## Required Environment Variable

Before using this skill, `CCWS_IMAGE_API_KEY` must be set. If it is missing, the CLI exits with setup instructions.

Temporary setup:

```bash
# macOS / Linux
export CCWS_IMAGE_API_KEY="your-ccws-token"

# Windows PowerShell
$env:CCWS_IMAGE_API_KEY="your-ccws-token"

# Windows CMD
set CCWS_IMAGE_API_KEY=your-ccws-token
```

Persistent setup:

```bash
# macOS / Linux zsh
echo 'export CCWS_IMAGE_API_KEY="your-ccws-token"' >> ~/.zshrc
source ~/.zshrc

# Windows PowerShell
[Environment]::SetEnvironmentVariable("CCWS_IMAGE_API_KEY", "your-ccws-token", "User")
```

The token must be created in the CCWSPro console and include access to `model: gpt-image-2`.

## Generate

```bash
python ~/.codex/skills/ccws-image-generation/scripts/ccws_image_generation.py generate \
  --prompt "A fairy-tale enchanted forest with glowing mushrooms and a winding moss path" \
  --model gpt-image-2 \
  --size 1536x1024 \
  --quality high \
  --out output/ccws-image-generation/fairy-forest.png
```

Useful prompt augmentation fields:

- `--use-case`
- `--scene`
- `--subject`
- `--style-medium`
- `--composition`
- `--lighting`
- `--palette`
- `--materials`
- `--constraints`
- `--negative`

Provider-specific parameters can be passed with `--extra-json '{"key":"value"}'`.

## Edit

```bash
python ~/.codex/skills/ccws-image-generation/scripts/ccws_image_generation.py edit \
  --image input.png \
  --prompt "Change only the background to a warm sunset forest; keep the subject unchanged" \
  --model gpt-image-2 \
  --size 1536x1024 \
  --quality high \
  --out output/ccws-image-generation/forest-edit.png
```

For multiple source images, repeat `--image`. The default multipart file field is `image`. If CCWS requires array-style fields, use:

```bash
--image-field "image[]"
```

Use `--mask mask.png` when the API supports masks. Repeat invariants in the prompt, such as `change only the background; keep the subject edges, face, pose, and lighting unchanged`.

## Parameters

Read `references/api.md` before using advanced parameters, transparency, provider-specific JSON, or endpoint overrides.

Common options:

- `--base-url`: default `https://www.ccws.pro/`
- `--api-prefix`: default `/v1`
- `--model`: default `gpt-image-2`
- `--size`: default `auto`
- `--quality`: default `medium`
- `--n`: default `1`
- `--background`: optional `transparent`, `opaque`, or `auto`
- `--output-format`: default `png`
- `--extra-json`: JSON object merged into the request

Current supported model: `gpt-image-2`, implemented in `scripts/models/gpt_image_2.py`. Add future model-specific parameter definitions under `scripts/models/` and register them in `scripts/models/__init__.py`.

`gpt-image-2` does not support `background=transparent`; add a future model file for true transparent output when CCWS exposes a compatible model.

## Output

The script supports base64 and URL image responses. It writes decoded or downloaded images to `--out` or generated filenames in `--out-dir`. It fails rather than overwriting existing files unless `--force` is set.

## Failure Output

Network errors, HTTP errors, non-JSON responses, malformed response bodies, missing image data, image download failures, and invalid base64 payloads are reported with structured details and redacted credentials. All failures include the CLI version. The final line for request/response failures is always:

```text
请在售后群咨询。
```
````

### `VERSION`

````text
1.0.0
````

### `agents/openai.yaml`

````yaml
interface:
  display_name: "CCWS Image Generation"
  short_description: "Default CCWS AI image workflow"
  default_prompt: "Use $ccws-image-generation to generate an enchanted forest scene through CCWS."
````

### `references/api.md`

````markdown
# CCWS Image Generation API Notes

Use this reference when advanced request controls are needed.

Current version: `1.0.0`. The canonical version source is the skill root `VERSION` file; the CLI exposes it through `--version`.

## URL construction

`scripts/ccws_image_generation.py` uses a root base URL plus an API prefix:

```text
base_url: https://www.ccws.pro/
api_prefix: /v1
generate: https://www.ccws.pro/v1/images/generations
edit: https://www.ccws.pro/v1/images/edits
```

Override when needed:

```bash
--base-url "https://www.ccws.pro/"
--api-prefix "/v1"
--api-prefix ""
```

Set environment defaults:

```bash
export CCWS_IMAGE_BASE_URL="https://www.ccws.pro/"
export CCWS_IMAGE_API_PREFIX="/v1"
```

## Authentication

The CLI requires one environment variable:

```bash
CCWS_IMAGE_API_KEY
```

It does not fall back to `OPENAI_API_KEY` or `~/.codex/auth.json`.

Current macOS/zsh setup:

```bash
export CCWS_IMAGE_API_KEY="your-ccws-token"
```

Windows PowerShell setup:

```powershell
$env:CCWS_IMAGE_API_KEY="your-ccws-token"
[Environment]::SetEnvironmentVariable("CCWS_IMAGE_API_KEY", "your-ccws-token", "User")
```

Persistent setup:

```bash
echo 'export CCWS_IMAGE_API_KEY="your-ccws-token"' >> ~/.zshrc
source ~/.zshrc
```

The token must be created in the CCWSPro console and include access to `model: gpt-image-2`.

## JSON generation payload

The generate command sends JSON to `/images/generations`.

Core fields:

- `model`
- `prompt`
- `n`
- `size`
- `quality`
- `background`
- `output_format`
- `output_compression`
- `moderation`
- `user`

Only non-empty optional fields are sent. Use `--extra-json` to merge provider-specific fields after the built-in fields.

## Multipart edit payload

The edit command sends multipart form data to `/images/edits`.

Core text fields:

- `model`
- `prompt`
- `n`
- `size`
- `quality`
- `background`
- `output_format`
- `output_compression`
- `moderation`
- `user`

File fields:

- `--image <path>` repeats for each source image.
- `--image-field image` is the default.
- `--image-field "image[]"` is available for services that expect array-style multipart fields.
- `--mask <path>` uploads a `mask` file when masks are supported.

## Output handling

The script accepts response items with:

- `b64_json`
- `url`
- `image`
- direct data URLs

If a response contains more images than `--n`, the script creates additional numbered output filenames.

## Script structure

- `scripts/ccws_image_generation.py`: cross-platform main CLI. Handles auth, URL construction, HTTP, multipart upload, response decoding, output files, dry-run, and model dispatch.
- `scripts/models/__init__.py`: model registry.
- `scripts/models/gpt_image_2.py`: current gpt-image-2 parameter definitions, payload construction, and validation.

To add a future model, create a new `scripts/models/<model_name>.py` file with the same `SPEC` interface and register it in `scripts/models/__init__.py`.

## Troubleshooting

- HTTP or provider errors include CLI version, endpoint, status, response body, request id when present, and `请在售后群咨询。`
- 401: credential reached CCWS but was rejected.
- Missing `CCWS_IMAGE_API_KEY`: create a CCWSPro token with `model: gpt-image-2`, then export it in the current environment.
- 404: retry with `--api-prefix ""` if the endpoint might not use `/v1`.
- `background=transparent`: current `gpt-image-2` model file rejects this before sending because gpt-image-2 does not support true transparent output.
- Multipart edit field errors: retry with `--image-field "image[]"`.
````

### `scripts/ccws_image_generation.py`

````python
#!/usr/bin/env python3
"""Cross-platform CCWS Image Generation CLI."""

from __future__ import annotations

import argparse
import base64
import binascii
import json
import mimetypes
import os
from pathlib import Path
import re
import sys
import time
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple, Union
import urllib.error
import urllib.parse
import urllib.request
import uuid

from models import DEFAULT_MODEL, get_model_spec, supported_model_ids


DEFAULT_BASE_URL = "https://www.ccws.pro/"
DEFAULT_API_PREFIX = "/v1"
DEFAULT_OUTPUT_PATH = "output/ccws-image-generation/output.png"
DEFAULT_TIMEOUT = 300
SKILL_ROOT = Path(__file__).resolve().parents[1]
VERSION_FILE = SKILL_ROOT / "VERSION"

API_KEY_ENV = "CCWS_IMAGE_API_KEY"
KEY_FIELDS = (API_KEY_ENV,)
SUPPORT_GROUP_NOTE = "请在售后群咨询。"

MISSING_API_KEY_MESSAGE = """在安装/使用本技能之前，请登录 CCWSPro 控制台，创建一个包含model：gpt-image-2的令牌，并将该令牌添加到环境变量中：CCWS_IMAGE_API_KEY。

临时设置方法：
- macOS / Linux:
  export CCWS_IMAGE_API_KEY="你的 CCWSPro 令牌"
- Windows PowerShell:
  $env:CCWS_IMAGE_API_KEY="你的 CCWSPro 令牌"
- Windows CMD:
  set CCWS_IMAGE_API_KEY=你的 CCWSPro 令牌

永久设置方法：
- macOS / Linux zsh:
  echo 'export CCWS_IMAGE_API_KEY="你的 CCWSPro 令牌"' >> ~/.zshrc
  source ~/.zshrc
- macOS / Linux bash:
  echo 'export CCWS_IMAGE_API_KEY="你的 CCWSPro 令牌"' >> ~/.bashrc
  source ~/.bashrc
- Windows PowerShell:
  [Environment]::SetEnvironmentVariable("CCWS_IMAGE_API_KEY", "你的 CCWSPro 令牌", "User")

验证：
- macOS / Linux:
  echo "$CCWS_IMAGE_API_KEY"
- Windows PowerShell:
  echo $env:CCWS_IMAGE_API_KEY

请不要把令牌直接发到聊天里。"""


def _die(message: str, code: int = 1, *, include_version: bool = True) -> None:
    if include_version and "Version:" not in message:
        message = f"{message}\nVersion: ccws-image-generation {_read_version()}"
    print(f"Error: {message}", file=sys.stderr)
    raise SystemExit(code)


def _read_version() -> str:
    try:
        return VERSION_FILE.read_text(encoding="utf-8").strip()
    except OSError:
        return "unknown"


def _die_request_failure(
    *,
    operation: str,
    url: str,
    message: str,
    status: Optional[int] = None,
    reason: Optional[str] = None,
    body: Optional[str] = None,
    exception: Optional[BaseException] = None,
) -> None:
    details = [
        f"{operation} failed.",
        f"Version: ccws-image-generation {_read_version()}",
        f"Endpoint: {url}",
    ]
    if status is not None:
        status_text = f"HTTP status: {status}"
        if reason:
            status_text += f" {reason}"
        details.append(status_text)
    details.append(f"Reason: {message}")

    request_id = _extract_request_id(body or "")
    if request_id:
        details.append(f"Request ID: {request_id}")
    if body:
        details.append(f"Response body: {_redact(body)}")
    if exception is not None:
        details.append(f"Exception: {exception.__class__.__name__}: {_redact(str(exception))}")

    details.append(SUPPORT_GROUP_NOTE)
    _die("\n".join(details))


def _redact(value: str) -> str:
    value = re.sub(r"sk-[A-Za-z0-9_-]{8,}", "sk-[REDACTED]", value)
    value = re.sub(r"Bearer\s+[A-Za-z0-9._~+/=-]{8,}", "Bearer [REDACTED]", value, flags=re.I)
    for field in KEY_FIELDS:
        value = re.sub(
            rf'("{re.escape(field)}"\s*:\s*")([^"]+)(")',
            rf'\1[REDACTED]\3',
            value,
            flags=re.I,
        )
    return value


def _extract_request_id(value: str) -> Optional[str]:
    if not value:
        return None
    try:
        data = json.loads(value)
    except json.JSONDecodeError:
        data = None

    if isinstance(data, dict):
        candidates: List[Any] = [
            data.get("request_id"),
            data.get("requestId"),
            data.get("id"),
        ]
        error = data.get("error")
        if isinstance(error, dict):
            candidates.extend(
                [
                    error.get("request_id"),
                    error.get("requestId"),
                    error.get("id"),
                ]
            )
            message = error.get("message")
            if isinstance(message, str):
                candidates.append(_extract_request_id_from_text(message))
        for candidate in candidates:
            if isinstance(candidate, str) and candidate.strip():
                return candidate.strip()

    return _extract_request_id_from_text(value)


def _extract_request_id_from_text(value: str) -> Optional[str]:
    patterns = [
        r"request id[:：]\s*([A-Za-z0-9_.:-]+)",
        r"request_id[\"']?\s*[:=]\s*[\"']?([A-Za-z0-9_.:-]+)",
    ]
    for pattern in patterns:
        match = re.search(pattern, value, flags=re.I)
        if match:
            return match.group(1)
    return None


def _get_api_key() -> Optional[str]:
    raw = os.environ.get(API_KEY_ENV)
    return raw.strip() if raw and raw.strip() else None


def _require_api_key() -> str:
    api_key = _get_api_key()
    if api_key:
        return api_key
    print(MISSING_API_KEY_MESSAGE, file=sys.stderr)
    _die("Missing required environment variable: CCWS_IMAGE_API_KEY.")


def _build_url(base_url: str, api_prefix: str, endpoint: str) -> str:
    base = base_url.rstrip("/")
    prefix = api_prefix.strip()
    endpoint = endpoint.strip("/")
    if not prefix or prefix == "/":
        return f"{base}/{endpoint}"
    return f"{base}/{prefix.strip('/')}/{endpoint}"


def _json_load_object(raw: Optional[str], label: str) -> Dict[str, Any]:
    if not raw:
        return {}
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        _die(f"{label} must be valid JSON: {exc}")
    if not isinstance(data, dict):
        _die(f"{label} must be a JSON object.")
    return data


def _prompt_from_file(path: Optional[str]) -> Optional[str]:
    if not path:
        return None
    return Path(path).expanduser().read_text(encoding="utf-8").strip()


def _compose_prompt(args: argparse.Namespace) -> str:
    prompt_file_text = _prompt_from_file(getattr(args, "prompt_file", None))
    prompt = (prompt_file_text or getattr(args, "prompt", None) or "").strip()
    if not prompt:
        _die("Missing prompt. Use --prompt or --prompt-file.")
    if getattr(args, "no_augment", False):
        return prompt

    fields = [
        ("Use case", getattr(args, "use_case", None)),
        ("Scene/backdrop", getattr(args, "scene", None)),
        ("Subject", getattr(args, "subject", None)),
        ("Style/medium", getattr(args, "style_medium", None)),
        ("Composition/framing", getattr(args, "composition", None)),
        ("Lighting/mood", getattr(args, "lighting", None)),
        ("Color palette", getattr(args, "palette", None)),
        ("Materials/textures", getattr(args, "materials", None)),
        ("Text", getattr(args, "text", None)),
        ("Constraints", getattr(args, "constraints", None)),
        ("Avoid", getattr(args, "negative", None)),
    ]
    lines = [f"Primary request: {prompt}"]
    for label, value in fields:
        if value:
            lines.append(f"{label}: {value.strip()}")
    return "\n".join(lines)


def _request_json(url: str, payload: Dict[str, Any], api_key: str, timeout: int) -> Dict[str, Any]:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        method="POST",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
    )
    return _read_json_response(req, timeout, operation="Image generation request", url=url)


def _read_json_response(req: urllib.request.Request, timeout: int, *, operation: str, url: str) -> Dict[str, Any]:
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read()
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        _die_request_failure(
            operation=operation,
            url=url,
            status=exc.code,
            reason=exc.reason,
            body=body,
            message="CCWS returned an HTTP error.",
        )
    except urllib.error.URLError as exc:
        _die_request_failure(
            operation=operation,
            url=url,
            message="Network request failed.",
            exception=exc,
        )

    try:
        data = json.loads(raw.decode("utf-8"))
    except json.JSONDecodeError as exc:
        preview = raw[:500].decode("utf-8", errors="replace")
        _die_request_failure(
            operation=operation,
            url=url,
            message=f"Response was not JSON: {exc}",
            body=preview,
        )
    if not isinstance(data, dict):
        _die_request_failure(
            operation=operation,
            url=url,
            message=f"Response JSON was not an object; got {type(data).__name__}.",
            body=json.dumps(data, ensure_ascii=False)[:500],
        )
    return data


def _guess_mime(path: Path) -> str:
    mime, _ = mimetypes.guess_type(str(path))
    return mime or "application/octet-stream"


def _multipart_body(fields: Sequence[Tuple[str, Any]], files: Sequence[Tuple[str, Path]]) -> Tuple[bytes, str]:
    boundary = f"----ccws-image-generation-{uuid.uuid4().hex}"
    chunks: List[bytes] = []

    def add(value: Union[str, bytes]) -> None:
        chunks.append(value if isinstance(value, bytes) else value.encode("utf-8"))

    for name, value in fields:
        add(f"--{boundary}\r\n")
        add(f'Content-Disposition: form-data; name="{name}"\r\n\r\n')
        add(str(value))
        add("\r\n")

    for name, path in files:
        add(f"--{boundary}\r\n")
        add(f'Content-Disposition: form-data; name="{name}"; filename="{path.name}"\r\n')
        add(f"Content-Type: {_guess_mime(path)}\r\n\r\n")
        chunks.append(path.read_bytes())
        add("\r\n")

    add(f"--{boundary}--\r\n")
    return b"".join(chunks), boundary


def _request_multipart(
    url: str,
    fields: Sequence[Tuple[str, Any]],
    files: Sequence[Tuple[str, Path]],
    api_key: str,
    timeout: int,
) -> Dict[str, Any]:
    body, boundary = _multipart_body(fields, files)
    req = urllib.request.Request(
        url,
        data=body,
        method="POST",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": f"multipart/form-data; boundary={boundary}",
            "Accept": "application/json",
        },
    )
    return _read_json_response(req, timeout, operation="Image edit request", url=url)


def _build_output_paths(out: str, out_dir: Optional[str], output_format: str, count: int) -> List[Path]:
    ext = ".jpg" if output_format == "jpeg" else f".{output_format}"
    if out_dir:
        base = Path(out_dir)
        base.mkdir(parents=True, exist_ok=True)
        return [base / f"image_{i}{ext}" for i in range(1, count + 1)]

    out_path = Path(out)
    if out_path.suffix == "":
        out_path = out_path.with_suffix(ext)
    if count == 1:
        return [out_path]
    return [out_path.with_name(f"{out_path.stem}-{i}{out_path.suffix}") for i in range(1, count + 1)]


def _ensure_writable(paths: Iterable[Path], force: bool) -> None:
    for path in paths:
        if path.exists() and not force:
            _die(f"Output already exists: {path} (use --force to overwrite)")
        path.parent.mkdir(parents=True, exist_ok=True)


def _extract_response_items(response: Dict[str, Any], *, operation: str) -> List[Any]:
    for key in ("data", "images", "output"):
        value = response.get(key)
        if isinstance(value, list):
            return value
    if any(key in response for key in ("b64_json", "url", "image")):
        return [response]
    _die_request_failure(
        operation=operation,
        url="response",
        message=f"Could not find image data in response keys: {', '.join(sorted(response.keys()))}",
        body=json.dumps(response, ensure_ascii=False)[:1000],
    )


def _bytes_from_data_url(value: str) -> Optional[bytes]:
    if not value.startswith("data:"):
        return None
    try:
        header, payload = value.split(",", 1)
    except ValueError:
        return None
    if ";base64" not in header:
        return urllib.parse.unquote_to_bytes(payload)
    try:
        return base64.b64decode(payload)
    except (binascii.Error, ValueError) as exc:
        _die_request_failure(
            operation="Image response decoding",
            url="response",
            message="Data URL image payload is not valid base64.",
            exception=exc,
        )


def _bytes_from_b64(value: str) -> bytes:
    data_url = _bytes_from_data_url(value)
    if data_url is not None:
        return data_url
    try:
        return base64.b64decode(value)
    except (binascii.Error, ValueError) as exc:
        _die_request_failure(
            operation="Image response decoding",
            url="response",
            message="Image payload is not valid base64.",
            exception=exc,
        )


def _download_url(url: str, timeout: int) -> bytes:
    req = urllib.request.Request(url, method="GET", headers={"Accept": "image/*,*/*"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read()
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        _die_request_failure(
            operation="Image download",
            url=url,
            status=exc.code,
            reason=exc.reason,
            message="Downloading the generated image URL failed.",
            body=body,
        )
    except urllib.error.URLError as exc:
        _die_request_failure(
            operation="Image download",
            url=url,
            message="Downloading the generated image URL failed.",
            exception=exc,
        )


def _item_to_bytes(item: Any, timeout: int) -> bytes:
    if isinstance(item, str):
        data_url = _bytes_from_data_url(item)
        if data_url is not None:
            return data_url
        if item.startswith("http://") or item.startswith("https://"):
            return _download_url(item, timeout)
        return _bytes_from_b64(item)

    if not isinstance(item, dict):
        _die_request_failure(
            operation="Image response decoding",
            url="response",
            message=f"Unsupported response item type: {type(item).__name__}.",
        )

    for key in ("b64_json", "image", "base64", "data"):
        value = item.get(key)
        if isinstance(value, str):
            if value.startswith("http://") or value.startswith("https://"):
                return _download_url(value, timeout)
            return _bytes_from_b64(value)
    url = item.get("url")
    if isinstance(url, str):
        return _download_url(url, timeout)

    _die_request_failure(
        operation="Image response decoding",
        url="response",
        message=f"Response item did not contain b64_json or url. Keys: {', '.join(sorted(item.keys()))}",
        body=json.dumps(item, ensure_ascii=False)[:1000],
    )


def _write_response_images(
    response: Dict[str, Any],
    output_paths: List[Path],
    force: bool,
    timeout: int,
) -> None:
    items = _extract_response_items(response, operation="Image response decoding")
    if len(items) > len(output_paths):
        last = output_paths[-1]
        extra = [
            last.with_name(f"{last.stem}-{i}{last.suffix}")
            for i in range(len(output_paths) + 1, len(items) + 1)
        ]
        output_paths.extend(extra)
    paths = output_paths[: len(items)]
    _ensure_writable(paths, force)
    for item, path in zip(items, paths):
        path.write_bytes(_item_to_bytes(item, timeout))
        print(f"Wrote {path}")


def _payload_to_form_fields(payload: Dict[str, Any]) -> List[Tuple[str, Any]]:
    fields: List[Tuple[str, Any]] = []
    for key, value in payload.items():
        if value is None:
            continue
        if isinstance(value, (dict, list)):
            fields.append((key, json.dumps(value, ensure_ascii=False)))
        else:
            fields.append((key, value))
    return fields


def _check_paths(paths: Sequence[str], label: str) -> List[Path]:
    result: List[Path] = []
    for raw in paths:
        path = Path(raw).expanduser()
        if not path.exists():
            _die(f"{label} not found: {path}")
        result.append(path)
    return result


def _print_dry_run(data: Dict[str, Any]) -> None:
    print(json.dumps(json.loads(_redact(json.dumps(data, ensure_ascii=False))), ensure_ascii=False, indent=2))


def _model_spec(args: argparse.Namespace):
    try:
        return get_model_spec(args.model)
    except ValueError as exc:
        _die(str(exc))


def _do_generate(args: argparse.Namespace) -> None:
    spec = _model_spec(args)
    output_format = spec.normalize_output_format(args.output_format)
    prompt = _compose_prompt(args)
    extra_json = _json_load_object(args.extra_json, "--extra-json")
    try:
        payload = spec.build_generate_payload(args, prompt, extra_json)
    except ValueError as exc:
        _die(str(exc))

    url = _build_url(args.base_url, args.api_prefix, "images/generations")
    outputs = _build_output_paths(args.out, args.out_dir, output_format, spec.output_count(args))
    api_key = _require_api_key()

    if args.dry_run:
        _print_dry_run({"method": "POST", "url": url, "payload": payload, "outputs": [str(p) for p in outputs]})
        return

    print(f"Calling CCWS Image Generation endpoint: {url}", file=sys.stderr)
    started = time.time()
    response = _request_json(url, payload, api_key, args.timeout)
    print(f"Generation completed in {time.time() - started:.1f}s.", file=sys.stderr)
    _write_response_images(response, outputs, args.force, args.timeout)


def _do_edit(args: argparse.Namespace) -> None:
    spec = _model_spec(args)
    output_format = spec.normalize_output_format(args.output_format)
    prompt = _compose_prompt(args)
    extra_json = _json_load_object(args.extra_json, "--extra-json")
    try:
        payload = spec.build_edit_payload(args, prompt, extra_json)
    except ValueError as exc:
        _die(str(exc))

    image_paths = _check_paths(args.image, "Image")
    files: List[Tuple[str, Path]] = [(args.image_field, path) for path in image_paths]
    if args.mask:
        files.append(("mask", _check_paths([args.mask], "Mask")[0]))

    url = _build_url(args.base_url, args.api_prefix, "images/edits")
    outputs = _build_output_paths(args.out, args.out_dir, output_format, spec.output_count(args))
    fields = _payload_to_form_fields(payload)
    api_key = _require_api_key()

    if args.dry_run:
        _print_dry_run(
            {
                "method": "POST",
                "url": url,
                "fields": payload,
                "files": [{"field": name, "path": str(path), "bytes": path.stat().st_size} for name, path in files],
                "outputs": [str(p) for p in outputs],
            }
        )
        return

    print(f"Calling CCWS Image Generation edit endpoint: {url}", file=sys.stderr)
    started = time.time()
    response = _request_multipart(url, fields, files, api_key, args.timeout)
    print(f"Edit completed in {time.time() - started:.1f}s.", file=sys.stderr)
    _write_response_images(response, outputs, args.force, args.timeout)


def _add_common_request_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--base-url", default=os.environ.get("CCWS_IMAGE_BASE_URL", DEFAULT_BASE_URL))
    parser.add_argument("--api-prefix", default=os.environ.get("CCWS_IMAGE_API_PREFIX", DEFAULT_API_PREFIX))
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--force", action="store_true")


def _add_common_image_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--model", default=os.environ.get("CCWS_IMAGE_MODEL", DEFAULT_MODEL), choices=list(supported_model_ids()))
    parser.add_argument("--prompt")
    parser.add_argument("--prompt-file")
    parser.add_argument("--extra-json")
    parser.add_argument("--out", default=DEFAULT_OUTPUT_PATH)
    parser.add_argument("--out-dir")

    parser.add_argument("--no-augment", action="store_true")
    parser.add_argument("--use-case")
    parser.add_argument("--scene")
    parser.add_argument("--subject")
    parser.add_argument("--style-medium")
    parser.add_argument("--composition")
    parser.add_argument("--lighting")
    parser.add_argument("--palette")
    parser.add_argument("--materials")
    parser.add_argument("--text")
    parser.add_argument("--constraints")
    parser.add_argument("--negative")


def _detect_model(argv: Sequence[str]) -> str:
    model = os.environ.get("CCWS_IMAGE_MODEL", DEFAULT_MODEL)
    for index, item in enumerate(argv):
        if item == "--model" and index + 1 < len(argv):
            return argv[index + 1]
        if item.startswith("--model="):
            return item.split("=", 1)[1]
    return model


def build_parser(selected_model: Optional[str] = None) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate or edit images through the CCWS Image Generation API.")
    parser.add_argument("--version", action="version", version=f"ccws-image-generation {_read_version()}")
    sub = parser.add_subparsers(dest="command", required=True)

    selected_spec = get_model_spec(selected_model or DEFAULT_MODEL)

    generate = sub.add_parser("generate", help="Generate a new image.")
    _add_common_request_args(generate)
    _add_common_image_args(generate)
    selected_spec.add_generate_arguments(generate)
    generate.set_defaults(func=_do_generate)

    edit = sub.add_parser("edit", help="Edit one or more images.")
    _add_common_request_args(edit)
    _add_common_image_args(edit)
    selected_spec.add_edit_arguments(edit)
    edit.add_argument("--image", action="append", required=True)
    edit.add_argument("--image-field", default="image")
    edit.add_argument("--mask")
    edit.set_defaults(func=_do_edit)

    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    raw_argv = list(sys.argv[1:] if argv is None else argv)
    selected_model = _detect_model(raw_argv)
    try:
        parser = build_parser(selected_model)
    except ValueError as exc:
        _die(str(exc))
    args = parser.parse_args(raw_argv)
    args.func(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
````

### `scripts/models/__init__.py`

````python
"""Model registry for CCWS Image Generation."""

from __future__ import annotations

from typing import Dict, Iterable, Optional, Protocol

from .gpt_image_2 import SPEC as GPT_IMAGE_2_SPEC


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
}

DEFAULT_MODEL = GPT_IMAGE_2_SPEC.model_id


def supported_model_ids() -> Iterable[str]:
    return sorted(MODEL_SPECS)


def get_model_spec(model_id: str) -> ModelSpec:
    try:
        return MODEL_SPECS[model_id]
    except KeyError as exc:
        supported = ", ".join(supported_model_ids())
        raise ValueError(f"Unsupported model: {model_id}. Supported models: {supported}") from exc
````

### `scripts/models/gpt_image_2.py`

````python
"""gpt-image-2 parameter definitions for CCWS Image Generation."""

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
````
