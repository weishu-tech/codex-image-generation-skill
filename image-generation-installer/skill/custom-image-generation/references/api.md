# Custom Image Generation API Notes

Use this reference when advanced request controls are needed.

Current version: `2.0.0`. The canonical version source is the skill root `VERSION` file; the platform launchers expose it through `--version`.

## URL construction

`scripts/image_generation.py` requires one configured API address. It has no built-in default, appends `/v1` when missing, and then appends the image endpoint:

```text
input: https://api.example.com
api_url: https://api.example.com/v1
generate: https://api.example.com/v1/images/generations
edit: https://api.example.com/v1/images/edits
```

Override when needed:

```bash
--api-url "https://api.example.com"
--config-file "/path/to/image-generation.json"
```

Legacy `--base-url` and `--api-prefix` options remain available for compatibility.

Set environment overrides:

```bash
export IMAGE_GENERATION_API_URL="https://api.example.com"
export IMAGE_GENERATION_CONFIG="/optional/custom/image-generation.json"
```

## Authentication

The one-click installer saves the API root and API Key in the current user's application configuration directory:

```text
macOS:  ~/Library/Application Support/Codex Image Generation/image-generation.json
Windows: %APPDATA%\Codex Image Generation\image-generation.json
```

On POSIX systems an installer-created config directory is limited to the current user and the file is written with mode `0600`. On Windows the file inherits the current user's AppData permissions.

The same file records the installer-managed Python executable and, on macOS, the framework, library, and CA certificate paths. Use `scripts/run-image-generation.command` on macOS or `scripts/run-image-generation.ps1` on Windows so those runtime settings are applied automatically. Do not print the configuration file because it also contains the API Key.

Environment variables override the saved values for a single process or terminal session:

```bash
export IMAGE_GENERATION_API_URL="https://api.example.com"
export IMAGE_GENERATION_API_KEY="your-api-key"
```

Windows PowerShell:

```powershell
$env:IMAGE_GENERATION_API_URL="https://api.example.com"
$env:IMAGE_GENERATION_API_KEY="your-api-key"
```

The CLI does not fall back to `OPENAI_API_KEY` or Codex authentication files. The token must include access to `model: gpt-image-2`.

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

- `scripts/run-image-generation.command`: macOS runtime launcher.
- `scripts/run-image-generation.ps1`: Windows runtime launcher.
- `scripts/image_generation.py`: cross-platform main CLI. Handles auth, URL construction, HTTP, multipart upload, response decoding, output files, dry-run, and model dispatch.
- `scripts/models/__init__.py`: model registry.
- `scripts/models/gpt_image_2.py`: current gpt-image-2 parameter definitions, payload construction, and validation.

To add a future model, create a new `scripts/models/<model_name>.py` file with the same `SPEC` interface and register it in `scripts/models/__init__.py`.

## Troubleshooting

- HTTP or provider errors include CLI version, endpoint, status, response body, request id when present, and `请在售后群咨询。`
- 401: the credential reached the configured provider but was rejected.
- Missing API Key: rerun the one-click installer, or set `IMAGE_GENERATION_API_KEY` for the current process.
- Missing Python 3: rerun the one-click installer. It installs a private, user-level Python runtime without changing PATH or the system Python.
- 404: check the saved API root and proxy path. The installer and CLI automatically append `/v1` when it is missing.
- `background=transparent`: current `gpt-image-2` model file rejects this before sending because gpt-image-2 does not support true transparent output.
- Multipart edit field errors: retry with `--image-field "image[]"`.
