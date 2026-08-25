#!/bin/zsh

set -u

SCRIPT_DIR="$(CDPATH= cd -- "$(/usr/bin/dirname -- "$0")" && pwd)"
CLI="$SCRIPT_DIR/image_generation.py"
CONFIG_FILE="${IMAGE_GENERATION_CONFIG:-$HOME/Library/Application Support/Codex Image Generation/image-generation.json}"

read_config_value() {
  local key="$1"
  [[ -f "$CONFIG_FILE" ]] || return 1
  /usr/bin/plutil -extract "$key" raw -o - -- "$CONFIG_FILE" 2>/dev/null
}

PYTHON_BIN="$(read_config_value python_executable || true)"
if [[ -n "$PYTHON_BIN" && -x "$PYTHON_BIN" ]]; then
  PYTHON_FRAMEWORK_PATH="$(read_config_value python_framework_path || true)"
  PYTHON_LIBRARY_PATH="$(read_config_value python_library_path || true)"
  PYTHON_SSL_CERT_FILE="$(read_config_value ssl_cert_file || true)"

  if [[ -n "$PYTHON_FRAMEWORK_PATH" ]]; then
    export DYLD_FRAMEWORK_PATH="$PYTHON_FRAMEWORK_PATH${DYLD_FRAMEWORK_PATH:+:$DYLD_FRAMEWORK_PATH}"
  fi
  if [[ -n "$PYTHON_LIBRARY_PATH" ]]; then
    export DYLD_LIBRARY_PATH="$PYTHON_LIBRARY_PATH${DYLD_LIBRARY_PATH:+:$DYLD_LIBRARY_PATH}"
  fi
  if [[ -n "$PYTHON_SSL_CERT_FILE" && -s "$PYTHON_SSL_CERT_FILE" ]]; then
    export SSL_CERT_FILE="$PYTHON_SSL_CERT_FILE"
  fi

  exec "$PYTHON_BIN" "$CLI" "$@"
fi

if command -v python3 >/dev/null 2>&1; then
  exec python3 "$CLI" "$@"
fi

if command -v python >/dev/null 2>&1 && python --version 2>&1 | /usr/bin/grep -q "Python 3"; then
  exec python "$CLI" "$@"
fi

echo "未找到可用的 Python 3。请重新运行 Custom Image Generation 一键安装器。" >&2
exit 1
