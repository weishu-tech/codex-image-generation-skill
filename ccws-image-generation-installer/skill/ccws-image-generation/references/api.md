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
