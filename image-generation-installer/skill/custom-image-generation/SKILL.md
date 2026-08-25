---
name: custom-image-generation
description: Generate or edit AI raster images through a user-configured OpenAI-compatible API that supports gpt-image-2. Use this skill for AI image generation, image editing, variations, image-to-image, inpainting, and background replacement requests that would otherwise use imagegen. This skill replaces the built-in imagegen path for AI image work.
---

# Custom Image Generation

Version: `2.0.0`

Use this skill for all AI image generation and AI image editing tasks. It is a provider-agnostic replacement for the built-in `imagegen` path and works with compatible APIs that expose `gpt-image-2` image endpoints.

Resolve the platform launcher relative to this `SKILL.md` file. The installer records its user-level managed Python 3 runtime, and the launcher applies the required runtime environment without exposing the API Key:

- macOS: `scripts/run-image-generation.command`
- Windows: `scripts/run-image-generation.ps1`

The underlying CLI is `scripts/image_generation.py`. The API root comes only from installer configuration or an explicit override; there is no built-in default. A supplied address that does not already end in `/v1` is normalized by appending `/v1`.

- Example input: `https://api.example.com`
- Normalized API root: `https://api.example.com/v1`
- Generation endpoint suffix: `/images/generations`
- Edit endpoint suffix: `/images/edits`

The version source is `VERSION`. Check it with the platform launcher:

```bash
"<skill-directory>/scripts/run-image-generation.command" --version
```

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "<skill-directory>\scripts\run-image-generation.ps1" --version
```

Use these launchers instead of calling Python directly. If the recorded runtime is unavailable, they may fall back to an existing system Python 3.

## Workflow

1. Decide whether the task is generation or editing.
2. For editing local files, inspect the image first when visual preservation matters.
3. Use the platform launcher with `generate` for new images and `edit` for modifying source images.
4. Write final images under the current project, usually `output/custom-image-generation/`.
5. Use `--dry-run` first when changing the API URL, model, transparency, or multipart field names.
6. Never print API keys. The script reads the installer-managed config or `IMAGE_GENERATION_API_KEY`.
7. If generation or editing fails, preserve the script's detailed error output. It includes endpoint, HTTP status, response body, request id when present, and `请在售后群咨询。`

## Required Configuration

The macOS and Windows one-click installers ask for exactly two configuration values:

- API address with no default, such as `https://api.example.com`; `/v1` is appended automatically when missing
- An API Key with access to `model: gpt-image-2`

Python 3 is downloaded and installed automatically in the current user's application data directory. This bootstrap does not require administrator privileges, alter PATH, or replace the system Python. The installer saves the API values and runtime paths in the current user's application configuration directory. Do not read, print, or copy the saved API Key into chat.

Environment variables are optional runtime overrides:

```bash
IMAGE_GENERATION_API_URL="https://api.example.com"
IMAGE_GENERATION_API_KEY="your-api-key"
IMAGE_GENERATION_CONFIG="/optional/custom/config.json"
```

The CLI never falls back to `OPENAI_API_KEY` or Codex authentication files.

## Generate

```bash
"<skill-directory>/scripts/run-image-generation.command" generate \
  --prompt "A fairy-tale enchanted forest with glowing mushrooms and a winding moss path" \
  --model gpt-image-2 \
  --size 1536x1024 \
  --quality high \
  --out output/custom-image-generation/fairy-forest.png
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
"<skill-directory>/scripts/run-image-generation.command" edit \
  --image input.png \
  --prompt "Change only the background to a warm sunset forest; keep the subject unchanged" \
  --model gpt-image-2 \
  --size 1536x1024 \
  --quality high \
  --out output/custom-image-generation/forest-edit.png
```

On Windows, pass the same arguments after `powershell.exe -NoProfile -ExecutionPolicy Bypass -File "<skill-directory>\scripts\run-image-generation.ps1"`.

For multiple source images, repeat `--image`. The default multipart file field is `image`. If the configured API provider requires array-style fields, use:

```bash
--image-field "image[]"
```

Use `--mask mask.png` when the API supports masks. Repeat invariants in the prompt, such as `change only the background; keep the subject edges, face, pose, and lighting unchanged`.

## Parameters

Read `references/api.md` before using advanced parameters, transparency, provider-specific JSON, or endpoint overrides.

Common options:

- `--api-url`: overrides the saved API root URL
- `--config-file`: overrides the installer-managed config file
- `--base-url` and `--api-prefix`: retained as legacy endpoint overrides
- `--model`: default `gpt-image-2`
- `--size`: default `auto`
- `--quality`: default `medium`
- `--n`: default `1`
- `--background`: optional `transparent`, `opaque`, or `auto`
- `--output-format`: default `png`
- `--extra-json`: JSON object merged into the request

Current supported model: `gpt-image-2`, implemented in `scripts/models/gpt_image_2.py`. Add future model-specific parameter definitions under `scripts/models/` and register them in `scripts/models/__init__.py`.

`gpt-image-2` does not support `background=transparent`; add a future model file for true transparent output when the configured provider exposes a compatible model.

## Output

The script supports base64 and URL image responses. It writes decoded or downloaded images to `--out` or generated filenames in `--out-dir`. It fails rather than overwriting existing files unless `--force` is set.

## Failure Output

Network errors, HTTP errors, non-JSON responses, malformed response bodies, missing image data, image download failures, and invalid base64 payloads are reported with structured details and redacted credentials. All failures include the CLI version. The final line for request/response failures is always:

```text
请在售后群咨询。
```
