# Custom Image Generation Skill Installer

This package installs and configures the `custom-image-generation` Codex skill on macOS and Windows. Never ask the user to paste an API Key into chat.

## Preferred install flow

- macOS: ask the user to double-click `install-macos.command`.
- Windows: ask the user to double-click `install-windows.bat`.

The installer itself asks for exactly two configuration values:

1. The required API address, for example `https://api.example.com`. There is no built-in default.
2. An API Key that supports `model: gpt-image-2.5`, `gpt-image-2.5-flare`, and `gpt-image-2.5-sunburst` (with `gpt-image-2` retained for compatibility).

The installer appends `/v1` when the normalized address does not already end with that exact path segment. The API Key prompt is hidden. Potentially conflicting image skills are reported without adding another confirmation question and are never modified.

To update to the newest repository-provided skill, download the latest `image-generation-installer.zip` from Releases and run the same platform installer again. It backs up and replaces only `custom-image-generation`, preserves the saved API address and API Key when the user presses Enter, and never modifies Codex's official built-in image skill.

No preinstalled Python is required. Before showing those two prompts, the launcher automatically installs official CPython `3.12.10` under the current user's image-generation application-data directory. It does not request administrator privileges, change PATH, or replace a system Python.

Download order is Tsinghua TUNA, Huawei Cloud, npmmirror, then python.org. Every artifact is checked against the pinned SHA256 in `python-runtime.json`; the macOS package signature is also verified before extraction.

## Preferred uninstall flow

- macOS: ask the user to double-click `uninstall-macos.command`.
- Windows: ask the user to double-click `uninstall-windows.bat`.

The uninstaller displays every existing target and asks for one confirmation, defaulting to cancel. It never asks for the API address or API Key. Once confirmed, it removes active `custom-image-generation` skill directories, the saved configuration/API Key, and the installer-managed Python `3.12.10` runtime.

It does not modify system Python, PATH, unrelated skills, other application files, or historical `skill-backups`. For isolated automation only, both platform uninstallers accept `--yes`; set `HOME`/`USERPROFILE`, `APPDATA`, `LOCALAPPDATA`, `CODEX_HOME`, `IMAGE_GENERATION_CONFIG`, and `IMAGE_GENERATION_PYTHON_RUNTIME_ROOT` to temporary targets as applicable. A custom Python runtime is removed only when its managed-runtime marker is present.

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
  --api-url "https://api.example.com" \
  --api-key "test-only-value"
```

Command-line API keys can be visible in process listings, so this path is not the normal user installation flow.

Bootstrap tests can set `IMAGE_GENERATION_PYTHON_DOWNLOAD_URL` to a verified local artifact or alternate URL and `IMAGE_GENERATION_PYTHON_RUNTIME_ROOT` to an isolated target. These variables do not add interactive questions.

## Install and configuration locations

Fresh user installs go to `~/.agents/skills/custom-image-generation`. If the same skill already exists under `~/.codex/skills`, the installer upgrades it there. `CODEX_HOME` and `--skills-dir` remain supported.

Saved configuration:

```text
macOS:  ~/Library/Application Support/Codex Image Generation/image-generation.json
Windows: %APPDATA%\Codex Image Generation\image-generation.json
```

Managed Python runtime:

```text
macOS:  ~/Library/Application Support/Codex Image Generation/Python/3.12.10
Windows: %LOCALAPPDATA%\Codex Image Generation\Python\3.12.10
```

`IMAGE_GENERATION_API_URL`, `IMAGE_GENERATION_API_KEY`, and `IMAGE_GENERATION_CONFIG` can override the saved configuration at runtime.

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
  custom-image-generation/
    SKILL.md
    VERSION
    agents/openai.yaml
    references/api.md
    scripts/image_generation.py
    scripts/run-image-generation.command
    scripts/run-image-generation.ps1
    scripts/models/__init__.py
    scripts/models/gpt_image_common.py
    scripts/models/gpt_image_2.py
    scripts/models/gpt_image_2_5.py
```

## Notes For AI Assistants

- Never print or repeat the user's API key.
- Do not use `OPENAI_API_KEY` or `~/.codex/auth.json`.
- Let the user type the API Key into the installer's hidden terminal prompt.
- If installation succeeds, tell the user to open a new Codex task or restart Codex.
