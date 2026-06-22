# CCWS Image Generation Skill Installer

This package installs the `ccws-image-generation` Codex skill. It makes CCWS Image Generation the AI image generation/editing path for Codex.

Give this whole folder or the zip file to an AI assistant and ask it to run the installer. Do not paste API keys into chat.

## Install Flow

1. Check local image generation skills.
   - The official skill is usually `~/.codex/skills/.system/imagegen`.
   - If other non-official image generation skills are found, recommend that the user uninstall or move them first to avoid trigger conflicts.
   - The user may ignore this warning and continue.
2. Require `CCWS_IMAGE_API_KEY`.
   - The user must create a CCWSPro image generation group API key in the CCWSPro console.
   - The token must include access to `model: gpt-image-2`.
   - The installer must stop if `CCWS_IMAGE_API_KEY` is not visible in the current environment.
3. Install the bundled skill to `$CODEX_HOME/skills/ccws-image-generation` or `~/.codex/skills/ccws-image-generation`.
4. Tell the user to open a new Codex conversation or restart Codex before trying image generation again.

## One Command

Run from this package directory:

```bash
python3 install.py --yes
```

Windows PowerShell:

```powershell
py -3 .\install.py --yes
```

Use `--yes` to continue even if non-official image generation skills are detected. Without `--yes`, the installer asks before continuing when conflicts are found.

## API Key Setup

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

After persistent Windows setup, restart the terminal or Codex so the new environment variable is loaded.

## Package Contents

```text
install.py
AI_INSTALL.md
ONLINE_INSTALL_DOC.md
skill/
  ccws-image-generation/
    SKILL.md
    VERSION
    agents/openai.yaml
    references/api.md
    scripts/ccws_image_generation.py
    scripts/models/__init__.py
    scripts/models/gpt_image_2.py
```

## Notes For AI Assistants

- Never print or repeat the user's API key.
- Do not use `OPENAI_API_KEY` or `~/.codex/auth.json`.
- Do not continue to the install step if `CCWS_IMAGE_API_KEY` is missing from the current environment.
- If installation succeeds, tell the user to open a new Codex conversation or restart Codex.
