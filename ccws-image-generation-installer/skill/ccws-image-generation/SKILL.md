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
