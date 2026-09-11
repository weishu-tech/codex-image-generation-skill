#!/usr/bin/env python3
"""Install and configure the Custom Image Generation skill for Codex."""

from __future__ import annotations

import argparse
from datetime import datetime
import getpass
import json
import os
from pathlib import Path
import shutil
import stat
import sys
from typing import Dict, Iterable, List, Optional, Tuple
import urllib.parse


PACKAGE_ROOT = Path(__file__).resolve().parent
BUNDLED_SKILL = PACKAGE_ROOT / "skill" / "custom-image-generation"
SKILL_NAME = "custom-image-generation"
LEGACY_SKILL_NAMES = ("ccws-image-generation",)
MODEL_ID = "gpt-image-2.5"
SUPPORTED_MODEL_HINT = "gpt-image-2.5、gpt-image-2.5-flare、gpt-image-2.5-sunburst（同时兼容 gpt-image-2）"

API_URL_EXAMPLE = "https://api.example.com/v1"
API_URL_ENV = "IMAGE_GENERATION_API_URL"
API_KEY_ENV = "IMAGE_GENERATION_API_KEY"
CONFIG_ENV = "IMAGE_GENERATION_CONFIG"
RUNTIME_CONFIG_FIELDS = (
    "python_executable",
    "python_framework_path",
    "python_library_path",
    "ssl_cert_file",
)

OFFICIAL_IMAGE_SKILL_REL = ".system/imagegen"
IMAGE_SKILL_KEYWORDS = (
    "imagegen",
    "image generation",
    "ai image",
    "images/generations",
    "images/edits",
    "生图",
    "图像生成",
    "生成图片",
    "图片生成",
)


def _codex_home(args: argparse.Namespace) -> Optional[Path]:
    if args.skills_dir:
        return None
    if args.codex_home:
        return Path(args.codex_home).expanduser().resolve()
    raw = os.environ.get("CODEX_HOME")
    if raw:
        return Path(raw).expanduser().resolve()
    return None


def _skills_dir(args: argparse.Namespace) -> Path:
    if args.skills_dir:
        return Path(args.skills_dir).expanduser().resolve()

    codex_home = _codex_home(args)
    if codex_home is not None:
        return codex_home / "skills"

    modern = (Path.home() / ".agents" / "skills").resolve()
    legacy = (Path.home() / ".codex" / "skills").resolve()

    # Keep existing installations in place. Fresh installs use the current
    # user-level Codex skill directory documented by OpenAI.
    if any((modern / name).exists() or (modern / name).is_symlink() for name in (SKILL_NAME, *LEGACY_SKILL_NAMES)):
        return modern
    if any((legacy / name).exists() or (legacy / name).is_symlink() for name in (SKILL_NAME, *LEGACY_SKILL_NAMES)):
        return legacy
    return modern


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


def _legacy_config_files() -> List[Path]:
    if sys.platform == "win32":
        app_data = os.environ.get("APPDATA", "").strip()
        root = Path(app_data) if app_data else Path.home() / "AppData" / "Roaming"
        return [(root / "CCWS" / "image-generation.json").resolve()]
    if sys.platform == "darwin":
        return [
            (Path.home() / "Library" / "Application Support" / "CCWS" / "image-generation.json").resolve()
        ]
    xdg_config = os.environ.get("XDG_CONFIG_HOME", "").strip()
    root = Path(xdg_config).expanduser() if xdg_config else Path.home() / ".config"
    return [(root / "ccws" / "image-generation.json").resolve()]


def _config_file(args: argparse.Namespace) -> Path:
    if args.config_file:
        return Path(args.config_file).expanduser().resolve()
    return _default_config_file()


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def _read_config(path: Path) -> Dict[str, str]:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SystemExit(f"Existing configuration could not be read: {path}\n{exc}") from exc
    if not isinstance(data, dict):
        raise SystemExit(f"Existing configuration must be a JSON object: {path}")
    return {str(key): str(value) for key, value in data.items() if isinstance(value, (str, int, float, bool))}


def _read_existing_config(path: Path) -> Dict[str, str]:
    if path.exists():
        return _read_config(path)
    for legacy_path in _legacy_config_files():
        if legacy_path.exists():
            print("Legacy image configuration detected; saved values will be migrated.")
            return _read_config(legacy_path)
    return {}


def _iter_skill_dirs(skills_root: Path) -> Iterable[Path]:
    if not skills_root.exists():
        return []
    return [path.parent for path in skills_root.rglob("SKILL.md")]


def _looks_like_image_skill(skill_dir: Path) -> bool:
    skill_md = skill_dir / "SKILL.md"
    text = f"{skill_dir.name}\n{_read_text(skill_md)}".lower()
    return any(keyword.lower() in text for keyword in IMAGE_SKILL_KEYWORDS)


def _scan_image_skills(skills_root: Path) -> Tuple[List[Path], List[Path], List[Path]]:
    official: List[Path] = []
    target: List[Path] = []
    other: List[Path] = []
    for skill_dir in _iter_skill_dirs(skills_root):
        try:
            rel = skill_dir.relative_to(skills_root).as_posix()
        except ValueError:
            rel = skill_dir.as_posix()
        if rel == OFFICIAL_IMAGE_SKILL_REL:
            official.append(skill_dir)
            continue
        if skill_dir.name == SKILL_NAME or skill_dir.name in LEGACY_SKILL_NAMES:
            target.append(skill_dir)
            continue
        if _looks_like_image_skill(skill_dir):
            other.append(skill_dir)
    return official, target, other


def _print_skill_scan(skills_root: Path, official: List[Path], target: List[Path], other: List[Path]) -> None:
    print(f"Codex skills directory: {skills_root}")
    if official:
        print("Official image skill detected:")
        for path in official:
            print(f"  - {path}")

    if target:
        print("Existing or legacy image generation skill will be upgraded in place:")
        for path in target:
            print(f"  - {path}")

    if other:
        print("Warning: potential non-official image generation skills were detected.")
        print("They will not be changed, but overlapping trigger descriptions may cause routing conflicts:")
        for path in other:
            print(f"  - {path}")


def _normalize_api_url(raw: str) -> str:
    value = raw.strip()
    if not value:
        raise ValueError("API address cannot be empty.")
    if "://" not in value:
        value = f"https://{value}"

    parsed = urllib.parse.urlsplit(value)
    if parsed.scheme not in {"http", "https"}:
        raise ValueError("API address must use http:// or https://.")
    if not parsed.hostname:
        raise ValueError("API address must include a host name.")
    if parsed.username or parsed.password:
        raise ValueError("API address must not contain embedded credentials.")
    if parsed.query or parsed.fragment:
        raise ValueError("API address must not contain a query string or fragment.")

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


def _prompt_api_url(existing: str) -> str:
    while True:
        suffix = "（直接回车沿用现有地址）" if existing else ""
        raw = input(f"API 地址{suffix}: ").strip()
        if not raw:
            if existing:
                return existing
            print("API 地址不能为空。")
            continue
        try:
            return _normalize_api_url(raw)
        except ValueError as exc:
            print(f"API 地址无效：{exc}")


def _prompt_api_key(existing: str) -> str:
    while True:
        suffix = "（直接回车沿用现有 Key）" if existing else ""
        value = getpass.getpass(f"支持 {SUPPORTED_MODEL_HINT} 的 API Key{suffix}: ").strip()
        if value:
            return value
        if existing:
            return existing
        print("API Key 不能为空。")


def _resolve_configuration(args: argparse.Namespace, existing: Dict[str, str]) -> Tuple[str, str]:
    raw_existing_url = (
        args.api_url
        or os.environ.get(API_URL_ENV, "").strip()
        or existing.get("api_url", "").strip()
    )
    existing_url = ""
    if raw_existing_url:
        try:
            existing_url = _normalize_api_url(raw_existing_url)
        except ValueError as exc:
            raise SystemExit(f"Configured API address is invalid: {exc}") from exc

    existing_key = (
        args.api_key
        or os.environ.get(API_KEY_ENV, "").strip()
        or existing.get("api_key", "").strip()
    )

    interactive = args.interactive or (sys.stdin.isatty() and not args.non_interactive)
    if interactive:
        api_url = _prompt_api_url(existing_url)
        api_key = _prompt_api_key(existing_key)
        return api_url, api_key

    if not existing_key:
        raise SystemExit(
            f"Missing API Key. Pass --api-key, set {API_KEY_ENV}, or run the installer interactively."
        )
    if not existing_url:
        raise SystemExit(
            f"Missing API address. Pass --api-url, set {API_URL_ENV}, or run the installer interactively."
        )
    return existing_url, existing_key


def _normalized_runtime_path(raw: str) -> str:
    return str(Path(raw).expanduser().resolve())


def _resolve_runtime_configuration(args: argparse.Namespace) -> Dict[str, str]:
    executable = _normalized_runtime_path(args.python_executable or sys.executable)
    if not Path(executable).is_file():
        raise SystemExit(f"Python executable not found: {executable}")

    runtime = {"python_executable": executable}
    optional_values = {
        "python_framework_path": args.python_framework_path,
        "python_library_path": args.python_library_path,
        "ssl_cert_file": args.ssl_cert_file,
    }
    for key, raw in optional_values.items():
        if raw:
            runtime[key] = _normalized_runtime_path(raw)
    return runtime


def _validate_bundle() -> str:
    if not BUNDLED_SKILL.exists():
        raise SystemExit(f"Bundled skill directory not found: {BUNDLED_SKILL}")
    skill_md = BUNDLED_SKILL / "SKILL.md"
    version_file = BUNDLED_SKILL / "VERSION"
    if not skill_md.exists():
        raise SystemExit(f"Bundled skill is missing SKILL.md: {skill_md}")
    if not version_file.exists():
        raise SystemExit(f"Bundled skill is missing VERSION: {version_file}")
    version = version_file.read_text(encoding="utf-8").strip()
    if not version:
        raise SystemExit(f"Bundled skill VERSION is empty: {version_file}")
    return version


def _unique_backup_path(target: Path) -> Path:
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup_root = target.parent.parent / "skill-backups"
    backup_root.mkdir(parents=True, exist_ok=True)
    candidate = backup_root / f"{target.name}.backup-{stamp}"
    suffix = 1
    while candidate.exists():
        candidate = backup_root / f"{target.name}.backup-{stamp}-{suffix}"
        suffix += 1
    return candidate


def _install_skill(skills_root: Path, dry_run: bool) -> None:
    version = _validate_bundle()
    target = skills_root / SKILL_NAME
    print(f"Installing {SKILL_NAME} {version} to {target}")
    if dry_run:
        print("Dry run enabled; no skill files were written.")
        return

    skills_root.mkdir(parents=True, exist_ok=True)
    for legacy_name in LEGACY_SKILL_NAMES:
        legacy_target = skills_root / legacy_name
        if legacy_target.exists() or legacy_target.is_symlink():
            legacy_backup = _unique_backup_path(skills_root / f"{SKILL_NAME}-legacy")
            shutil.move(str(legacy_target), str(legacy_backup))
            print(f"Backed up legacy image skill to {legacy_backup}")

    backup_path = None
    if target.exists() or target.is_symlink():
        backup_path = _unique_backup_path(target)
        shutil.move(str(target), str(backup_path))
        print(f"Backed up existing skill to {backup_path}")

    try:
        shutil.copytree(
            BUNDLED_SKILL,
            target,
            ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
        )
    except Exception:
        if backup_path and not target.exists() and backup_path.exists():
            shutil.move(str(backup_path), str(target))
        raise


def _write_config(
    path: Path,
    api_url: str,
    api_key: str,
    runtime: Dict[str, str],
    dry_run: bool,
) -> None:
    print(f"Configuration file: {path}")
    if dry_run:
        print("Dry run enabled; no configuration was written.")
        return

    parent_existed = path.parent.exists()
    path.parent.mkdir(parents=True, exist_ok=True)
    if os.name != "nt" and not parent_existed:
        path.parent.chmod(stat.S_IRWXU)

    data = {
        "api_url": api_url,
        "api_key": api_key,
        "model": MODEL_ID,
        "updated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
    }
    data.update({key: value for key, value in runtime.items() if key in RUNTIME_CONFIG_FIELDS})
    temporary = path.with_name(f".{path.name}.tmp-{os.getpid()}")
    try:
        temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        if os.name != "nt":
            temporary.chmod(stat.S_IRUSR | stat.S_IWUSR)
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def main() -> int:
    parser = argparse.ArgumentParser(description="Install and configure Custom Image Generation for Codex.")
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Compatibility flag. Conflicting skills are reported but never modified.",
    )
    parser.add_argument("--codex-home", help="Override CODEX_HOME and install under its skills directory.")
    parser.add_argument("--skills-dir", help="Override the skills directory directly.")
    parser.add_argument("--config-file", help=f"Override the configuration file or set {CONFIG_ENV}.")
    parser.add_argument(
        "--api-url",
        help=f"API address, for example {API_URL_EXAMPLE}; /v1 is appended automatically when missing.",
    )
    parser.add_argument("--api-key", help="API Key for automation only; interactive entry is safer.")
    parser.add_argument("--interactive", action="store_true", help="Always ask for API address and API Key.")
    parser.add_argument("--non-interactive", action="store_true", help="Never prompt; require args, env, or saved config.")
    parser.add_argument("--dry-run", action="store_true", help="Run checks without copying files or saving config.")
    parser.add_argument("--python-executable", help="Python executable used by the installed skill launcher.")
    parser.add_argument("--python-framework-path", help="macOS DYLD framework path for the managed Python runtime.")
    parser.add_argument("--python-library-path", help="macOS DYLD library path for the managed Python runtime.")
    parser.add_argument("--ssl-cert-file", help="CA certificate bundle for the managed Python runtime.")
    args = parser.parse_args()

    if args.interactive and args.non_interactive:
        parser.error("--interactive and --non-interactive cannot be used together.")

    skills_root = _skills_dir(args)
    config_path = _config_file(args)
    existing_config = _read_existing_config(config_path)
    api_url, api_key = _resolve_configuration(args, existing_config)
    runtime_config = _resolve_runtime_configuration(args)

    official, target, other = _scan_image_skills(skills_root)
    _print_skill_scan(skills_root, official, target, other)
    _install_skill(skills_root, args.dry_run)
    _write_config(config_path, api_url, api_key, runtime_config, args.dry_run)

    if args.dry_run:
        print("Dry run completed successfully.")
    else:
        print("Installation completed.")
        print(f"Configured API address: {api_url}")
        print(f"Configured model: {MODEL_ID}")
        print(f"Configured Python runtime: {runtime_config['python_executable']}")
        print("API Key saved without being displayed.")
        print("Next step: restart Codex or open a new Codex task, then request image generation.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
