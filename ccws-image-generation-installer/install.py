#!/usr/bin/env python3
"""Install the CCWS Image Generation skill for Codex."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import shutil
import sys
from datetime import datetime
from typing import Iterable, List, Tuple


PACKAGE_ROOT = Path(__file__).resolve().parent
BUNDLED_SKILL = PACKAGE_ROOT / "skill" / "ccws-image-generation"
SKILL_NAME = "ccws-image-generation"
API_KEY_ENV = "CCWS_IMAGE_API_KEY"
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


SETUP_INSTRUCTIONS = """需要先配置 CCWS_IMAGE_API_KEY，安装脚本已停止，未写入本地技能。

请先完成：
1. 登录 CCWSPro 控制台。
2. 创建一个生图分组 API KEY，令牌需要包含 model: gpt-image-2。
3. 在当前环境配置变量 CCWS_IMAGE_API_KEY。

临时配置：
- macOS / Linux:
  export CCWS_IMAGE_API_KEY="你的 CCWSPro 令牌"
- Windows PowerShell:
  $env:CCWS_IMAGE_API_KEY="你的 CCWSPro 令牌"
- Windows CMD:
  set CCWS_IMAGE_API_KEY=你的 CCWSPro 令牌

永久配置：
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

不要把令牌直接发到聊天里。"""


def _codex_home(args: argparse.Namespace) -> Path:
    if args.skills_dir:
        return Path(args.skills_dir).expanduser().resolve().parent
    if args.codex_home:
        return Path(args.codex_home).expanduser().resolve()
    raw = os.environ.get("CODEX_HOME")
    if raw:
        return Path(raw).expanduser().resolve()
    return (Path.home() / ".codex").resolve()


def _skills_dir(args: argparse.Namespace) -> Path:
    if args.skills_dir:
        return Path(args.skills_dir).expanduser().resolve()
    return _codex_home(args) / "skills"


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


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
        if skill_dir.name == SKILL_NAME:
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
    else:
        print("Official image skill was not found under this skills directory.")

    if target:
        print("Existing CCWS Image Generation skill will be replaced:")
        for path in target:
            print(f"  - {path}")

    if other:
        print("Potential non-official image generation skills detected.")
        print("Recommendation: uninstall or move these first to avoid trigger conflicts. You may still continue.")
        for path in other:
            print(f"  - {path}")


def _confirm_continue(args: argparse.Namespace, other: List[Path]) -> None:
    if not other or args.yes:
        return
    if not sys.stdin.isatty():
        raise SystemExit("Non-official image generation skills were found. Re-run with --yes to continue anyway.")
    answer = input("Continue installation anyway? [y/N] ").strip().lower()
    if answer not in {"y", "yes"}:
        raise SystemExit("Installation cancelled. Remove conflicting skills or re-run with --yes to continue.")


def _require_api_key() -> None:
    if os.environ.get(API_KEY_ENV, "").strip():
        print(f"{API_KEY_ENV} is configured in the current environment.")
        return
    raise SystemExit(SETUP_INSTRUCTIONS)


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
    candidate = target.with_name(f"{target.name}.backup-{stamp}")
    suffix = 1
    while candidate.exists():
        candidate = target.with_name(f"{target.name}.backup-{stamp}-{suffix}")
        suffix += 1
    return candidate


def _install_skill(skills_root: Path, dry_run: bool) -> None:
    version = _validate_bundle()
    target = skills_root / SKILL_NAME
    print(f"Installing {SKILL_NAME} {version} to {target}")
    if dry_run:
        print("Dry run enabled; no files were written.")
        return

    skills_root.mkdir(parents=True, exist_ok=True)
    backup_path = None
    if target.exists() or target.is_symlink():
        backup_path = _unique_backup_path(target)
        shutil.move(str(target), str(backup_path))
        print(f"Backed up existing skill to {backup_path}")

    try:
        shutil.copytree(BUNDLED_SKILL, target)
    except Exception:
        if backup_path and not target.exists() and backup_path.exists():
            shutil.move(str(backup_path), str(target))
        raise

    print("Installation completed.")
    print("Next step: open a new Codex conversation or restart Codex, then request image generation again.")


def main() -> int:
    parser = argparse.ArgumentParser(description="Install the CCWS Image Generation skill for Codex.")
    parser.add_argument("--yes", action="store_true", help="Continue even if non-official image skills are detected.")
    parser.add_argument("--codex-home", help="Override CODEX_HOME; defaults to $CODEX_HOME or ~/.codex.")
    parser.add_argument("--skills-dir", help="Override the skills directory directly.")
    parser.add_argument("--dry-run", action="store_true", help="Run checks without copying files.")
    args = parser.parse_args()

    skills_root = _skills_dir(args)
    official, target, other = _scan_image_skills(skills_root)
    _print_skill_scan(skills_root, official, target, other)
    _confirm_continue(args, other)
    _require_api_key()
    _install_skill(skills_root, args.dry_run)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
