#!/usr/bin/env python3
"""Cross-platform Custom Image Generation CLI."""

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


DEFAULT_API_PREFIX = "/v1"
API_URL_EXAMPLE = "https://api.example.com/v1"
DEFAULT_OUTPUT_PATH = "output/custom-image-generation/output.png"
DEFAULT_TIMEOUT = 300
SKILL_ROOT = Path(__file__).resolve().parents[1]
VERSION_FILE = SKILL_ROOT / "VERSION"

API_URL_ENV = "IMAGE_GENERATION_API_URL"
API_KEY_ENV = "IMAGE_GENERATION_API_KEY"
CONFIG_ENV = "IMAGE_GENERATION_CONFIG"
KEY_FIELDS = (API_KEY_ENV, "api_key")
SUPPORT_GROUP_NOTE = "请在售后群咨询。"

MISSING_API_KEY_MESSAGE = """没有找到 Custom Image Generation API Key。

请重新运行一键安装器，并输入：
1. API 地址，例如 https://api.example.com（缺少 /v1 时会自动补充）
2. 支持以下模型的 API Key：gpt-image-2.5、gpt-image-2.5-flare、gpt-image-2.5-sunburst（同时兼容 gpt-image-2）

也可以通过 IMAGE_GENERATION_API_KEY 环境变量临时覆盖安装器保存的配置。
请不要把 API Key 直接发到聊天里。"""


def _die(message: str, code: int = 1, *, include_version: bool = True) -> None:
    if include_version and "Version:" not in message:
        message = f"{message}\nVersion: custom-image-generation {_read_version()}"
    print(f"Error: {message}", file=sys.stderr)
    raise SystemExit(code)


def _read_version() -> str:
    try:
        return VERSION_FILE.read_text(encoding="utf-8").strip()
    except OSError:
        return "unknown"


def _default_config_file() -> Path:
    override = os.environ.get(CONFIG_ENV, "").strip()
    if override:
        return Path(override).expanduser().resolve()

    if sys.platform == "win32":
        app_data = os.environ.get("APPDATA", "").strip()
        root = Path(app_data) if app_data else Path.home() / "AppData" / "Roaming"
        return (root / "Codex Image Generation" / "image-generation.json").resolve()

    if sys.platform == "darwin":
        return (Path.home() / "Library" / "Application Support" / "Codex Image Generation" / "image-generation.json").resolve()

    xdg_config = os.environ.get("XDG_CONFIG_HOME", "").strip()
    root = Path(xdg_config).expanduser() if xdg_config else Path.home() / ".config"
    return (root / "codex-image-generation" / "image-generation.json").resolve()


def _config_file(args: Optional[argparse.Namespace] = None) -> Path:
    override = getattr(args, "config_file", None) if args is not None else None
    if override:
        return Path(override).expanduser().resolve()
    return _default_config_file()


def _read_config(args: Optional[argparse.Namespace] = None) -> Dict[str, Any]:
    path = _config_file(args)
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        _die(f"Could not read configuration file {path}: {exc}")
    if not isinstance(data, dict):
        _die(f"Configuration file must contain a JSON object: {path}")
    return data


def _normalize_api_url(raw: str) -> str:
    value = raw.strip()
    if not value:
        _die("API address cannot be empty.")
    if "://" not in value:
        value = f"https://{value}"

    parsed = urllib.parse.urlsplit(value)
    if parsed.scheme not in {"http", "https"}:
        _die("API address must use http:// or https://.")
    if not parsed.hostname:
        _die("API address must include a host name.")
    if parsed.username or parsed.password:
        _die("API address must not contain embedded credentials.")
    if parsed.query or parsed.fragment:
        _die("API address must not contain a query string or fragment.")

    path = parsed.path.rstrip("/")
    for endpoint in ("/images/generations", "/images/edits"):
        if path.lower().endswith(endpoint):
            path = path[: -len(endpoint)].rstrip("/")
            break

    if path.lower().endswith("/v1"):
        path = f"{path[:-3]}/v1"
    else:
        path = f"{path}/v1" if path else "/v1"
    return urllib.parse.urlunsplit((parsed.scheme, parsed.netloc, path, "", "")).rstrip("/")


def _legacy_api_url(base_url: str, api_prefix: str) -> str:
    base = base_url.rstrip("/")
    prefix = api_prefix.strip()
    if not prefix or prefix == "/":
        return base
    return f"{base}/{prefix.strip('/')}"


def _resolve_api_url(args: argparse.Namespace) -> str:
    if args.api_url:
        return _normalize_api_url(args.api_url)

    if args.base_url is not None or args.api_prefix is not None:
        if not args.base_url:
            _die("--base-url is required when using legacy --base-url/--api-prefix overrides.")
        base_url = args.base_url
        api_prefix = args.api_prefix if args.api_prefix is not None else DEFAULT_API_PREFIX
        return _normalize_api_url(_legacy_api_url(base_url, api_prefix))

    direct_env = os.environ.get(API_URL_ENV, "").strip()
    if direct_env:
        return _normalize_api_url(direct_env)

    legacy_base = os.environ.get("IMAGE_GENERATION_BASE_URL")
    legacy_prefix = os.environ.get("IMAGE_GENERATION_API_PREFIX")
    if legacy_base is not None or legacy_prefix is not None:
        if not legacy_base:
            _die("IMAGE_GENERATION_BASE_URL is required when using legacy API environment overrides.")
        return _normalize_api_url(
            _legacy_api_url(
                legacy_base,
                legacy_prefix if legacy_prefix is not None else DEFAULT_API_PREFIX,
            )
        )

    configured = _read_config(args).get("api_url")
    if isinstance(configured, str) and configured.strip():
        return _normalize_api_url(configured)
    _die(
        "Missing API address. Rerun the one-click installer, pass --api-url, "
        f"or set {API_URL_ENV}. Example: {API_URL_EXAMPLE}"
    )


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
        f"Version: custom-image-generation {_read_version()}",
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


def _get_api_key(args: argparse.Namespace) -> Optional[str]:
    raw = os.environ.get(API_KEY_ENV)
    if raw and raw.strip():
        return raw.strip()
    configured = _read_config(args).get("api_key")
    if isinstance(configured, str) and configured.strip():
        return configured.strip()
    return None


def _require_api_key(args: argparse.Namespace) -> str:
    api_key = _get_api_key(args)
    if api_key:
        return api_key
    print(MISSING_API_KEY_MESSAGE, file=sys.stderr)
    _die(f"Missing API Key in environment or configuration file: {_config_file(args)}")


def _build_url(api_url: str, endpoint: str) -> str:
    base = api_url.rstrip("/")
    endpoint = endpoint.strip("/")
    return f"{base}/{endpoint}"


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
            message="The configured image provider returned an HTTP error.",
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
    boundary = f"----custom-image-generation-{uuid.uuid4().hex}"
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

    url = _build_url(_resolve_api_url(args), "images/generations")
    outputs = _build_output_paths(args.out, args.out_dir, output_format, spec.output_count(args))
    api_key = _require_api_key(args)

    if args.dry_run:
        _print_dry_run({"method": "POST", "url": url, "payload": payload, "outputs": [str(p) for p in outputs]})
        return

    print(f"Calling Custom Image Generation endpoint: {url}", file=sys.stderr)
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

    url = _build_url(_resolve_api_url(args), "images/edits")
    outputs = _build_output_paths(args.out, args.out_dir, output_format, spec.output_count(args))
    fields = _payload_to_form_fields(payload)
    api_key = _require_api_key(args)

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

    print(f"Calling Custom Image Generation edit endpoint: {url}", file=sys.stderr)
    started = time.time()
    response = _request_multipart(url, fields, files, api_key, args.timeout)
    print(f"Edit completed in {time.time() - started:.1f}s.", file=sys.stderr)
    _write_response_images(response, outputs, args.force, args.timeout)


def _add_common_request_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--api-url",
        help="API address; /v1 is appended automatically when missing. Default comes only from installer config.",
    )
    parser.add_argument("--config-file", help=f"Override the saved configuration file or set {CONFIG_ENV}.")
    parser.add_argument("--base-url", help="Legacy override for the API host/root URL.")
    parser.add_argument("--api-prefix", help="Legacy override for the API prefix, for example /v1 or an empty string.")
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--force", action="store_true")


def _add_common_image_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--model", default=os.environ.get("IMAGE_GENERATION_MODEL", DEFAULT_MODEL), choices=list(supported_model_ids()))
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
    model = os.environ.get("IMAGE_GENERATION_MODEL", DEFAULT_MODEL)
    for index, item in enumerate(argv):
        if item == "--model" and index + 1 < len(argv):
            return argv[index + 1]
        if item.startswith("--model="):
            return item.split("=", 1)[1]
    return model


def build_parser(selected_model: Optional[str] = None) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate or edit images through the Custom Image Generation API.")
    parser.add_argument("--version", action="version", version=f"custom-image-generation {_read_version()}")
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
