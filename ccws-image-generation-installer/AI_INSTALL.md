# CCWS Image Generation Skill Installer

This package installs and configures the `ccws-image-generation` Codex skill on macOS and Windows. Never ask the user to paste an API Key into chat.

## Preferred install flow

- macOS: ask the user to double-click `install-macos.command`.
- Windows: ask the user to double-click `install-windows.bat`.

The installer itself asks for exactly two configuration values:

1. The required API address, for example `https://www.ccws.pro`. There is no built-in default.
2. An API Key that supports `model: gpt-image-2`.

The installer appends `/v1` when the normalized address does not already end with that exact path segment. The API Key prompt is hidden. Potentially conflicting image skills are reported without adding another confirmation question and are never modified.

No preinstalled Python is required. Before showing those two prompts, the launcher automatically installs official CPython `3.12.10` under the current user's CCWS application-data directory. It does not request administrator privileges, change PATH, or replace a system Python.

Download order is Tsinghua TUNA, Huawei Cloud, npmmirror, then python.org. Every artifact is checked against the pinned SHA256 in `python-runtime.json`; the macOS package signature is also verified before extraction.

## Preferred uninstall flow

- macOS: ask the user to double-click `uninstall-macos.command`.
- Windows: ask the user to double-click `uninstall-windows.bat`.

The uninstaller displays every existing target and asks for one confirmation, defaulting to cancel. It never asks for the API address or API Key. Once confirmed, it removes active `ccws-image-generation` skill directories, the saved configuration/API Key, and the CCWS-managed Python `3.12.10` runtime.

It does not modify system Python, PATH, unrelated skills, other CCWS files, or historical `skill-backups`. For isolated automation only, both platform uninstallers accept `--yes`; set `HOME`/`USERPROFILE`, `APPDATA`, `LOCALAPPDATA`, `CODEX_HOME`, `CCWS_IMAGE_CONFIG`, and `CCWS_PYTHON_RUNTIME_ROOT` to temporary targets as applicable. A custom Python runtime is removed only when its CCWS managed-runtime marker is present.

## AI-assisted command

If an AI assistant is guiding installation, prefer the double-click flow so the user enters the secret directly. Equivalent interactive commands are:

```bash
./install-macos.command
```

Windows PowerShell:

```powershell
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File .\install-windows.ps1
```

Do not request, print, echo, inspect, or repeat the user's API Key.

For isolated automated tests with an existing Python 3 only, `install.py` remains callable directly:

```bash
python3 install.py --yes --non-interactive \
  --api-url "https://www.ccws.pro" \
  --api-key "test-only-value"
```

Command-line API keys can be visible in process listings, so this path is not the normal user installation flow.

Bootstrap tests can set `CCWS_PYTHON_DOWNLOAD_URL` to a verified local artifact or alternate URL and `CCWS_PYTHON_RUNTIME_ROOT` to an isolated target. These variables do not add interactive questions.

## Install and configuration locations

Fresh user installs go to `~/.agents/skills/ccws-image-generation`. If the same skill already exists under `~/.codex/skills`, the installer upgrades it there. `CODEX_HOME` and `--skills-dir` remain supported.

Saved configuration:

```text
macOS:  ~/Library/Application Support/CCWS/image-generation.json
Windows: %APPDATA%\CCWS\image-generation.json
```

Managed Python runtime:

```text
macOS:  ~/Library/Application Support/CCWS/Python/3.12.10
Windows: %LOCALAPPDATA%\CCWS\Python\3.12.10
```

`CCWS_IMAGE_API_URL`, `CCWS_IMAGE_API_KEY`, and `CCWS_IMAGE_CONFIG` can override the saved configuration at runtime.

## Package Contents

```text
install.py
install-macos.command
install-windows.bat
install-windows.ps1
uninstall-macos.command
uninstall-windows.bat
uninstall-windows.ps1
python-runtime.json
AI_INSTALL.md
skill/
  ccws-image-generation/
    SKILL.md
    VERSION
    agents/openai.yaml
    references/api.md
    scripts/ccws_image_generation.py
    scripts/run-ccws-image-generation.command
    scripts/run-ccws-image-generation.ps1
    scripts/models/__init__.py
    scripts/models/gpt_image_2.py
```

## Notes For AI Assistants

- Never print or repeat the user's API key.
- Do not use `OPENAI_API_KEY` or `~/.codex/auth.json`.
- Let the user type the API Key into the installer's hidden terminal prompt.
- If installation succeeds, tell the user to open a new Codex task or restart Codex.
