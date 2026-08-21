#!/bin/zsh

set -u
umask 077

SCRIPT_DIR="$(CDPATH= cd -- "$(/usr/bin/dirname -- "$0")" && pwd)"
MANIFEST="$SCRIPT_DIR/python-runtime.json"
RUNTIME_MARKER_NAME=".ccws-managed-python-runtime"
TEMP_ROOT=""
STAGING_ROOT=""

cleanup() {
  if [[ -n "${TEMP_ROOT:-}" && -d "$TEMP_ROOT" ]]; then
    /bin/rm -rf -- "$TEMP_ROOT"
  fi
  if [[ -n "${STAGING_ROOT:-}" && -d "$STAGING_ROOT" ]]; then
    /bin/rm -rf -- "$STAGING_ROOT"
  fi
}

trap cleanup EXIT INT TERM

manifest_value() {
  /usr/bin/plutil -extract "$1" raw -o - -- "$MANIFEST"
}

runtime_env() {
  local runtime_root="$1"
  local python_bin="$runtime_root/$PYTHON_RELATIVE_PATH"
  local framework_path="$runtime_root"
  local library_path="$runtime_root/$PYTHON_LIBRARY_RELATIVE_PATH"
  local cert_file="$runtime_root/$PYTHON_CERTIFICATE_RELATIVE_PATH"

  /usr/bin/env \
    DYLD_FRAMEWORK_PATH="$framework_path" \
    DYLD_LIBRARY_PATH="$library_path" \
    SSL_CERT_FILE="$cert_file" \
    "$python_bin" "${@:2}"
}

runtime_is_valid() {
  local runtime_root="$1"
  local python_bin="$runtime_root/$PYTHON_RELATIVE_PATH"
  local cert_file="$runtime_root/$PYTHON_CERTIFICATE_RELATIVE_PATH"

  [[ -x "$python_bin" && -s "$cert_file" ]] || return 1
  runtime_env "$runtime_root" -c \
    'import ssl, sys, urllib.request; ssl.create_default_context(); expected = tuple(map(int, sys.argv[1].split("."))); raise SystemExit(0 if sys.version_info[:3] == expected else 1)' \
    "$PYTHON_VERSION" \
    >/dev/null 2>&1
}

write_runtime_marker() {
  local runtime_root="$1"
  local marker_path="$runtime_root/$RUNTIME_MARKER_NAME"

  /usr/bin/printf 'ccws-image-generation:%s\n' "$PYTHON_VERSION" > "$marker_path" || return 1
  /bin/chmod 600 "$marker_path" || return 1
}

download_archive() {
  local destination="$1"
  local expected_sha256="$2"
  local source_url=""
  local actual_sha256=""
  local template_count=0
  local index=0
  local template=""
  local -a candidates

  if [[ -n "${CCWS_PYTHON_DOWNLOAD_URL:-}" ]]; then
    candidates=("$CCWS_PYTHON_DOWNLOAD_URL")
  else
    template_count="$(manifest_value download_url_templates)" || return 1
    for ((index = 0; index < template_count; index++)); do
      template="$(manifest_value "download_url_templates.$index")" || return 1
      template="${template//\{version\}/$PYTHON_VERSION}"
      template="${template//\{filename\}/$PYTHON_FILENAME}"
      candidates+=("$template")
    done
  fi

  for source_url in "${candidates[@]}"; do
    echo "正在下载 Python $PYTHON_VERSION：$source_url"
    /bin/rm -f -- "$destination"

    if [[ -f "$source_url" ]]; then
      /bin/cp -- "$source_url" "$destination" || continue
    else
      /usr/bin/curl \
        --fail \
        --location \
        --retry 2 \
        --retry-delay 1 \
        --connect-timeout 20 \
        --max-time 900 \
        --output "$destination" \
        "$source_url" || continue
    fi

    actual_sha256="$(/usr/bin/shasum -a 256 "$destination" | /usr/bin/awk '{print tolower($1)}')" || continue
    if [[ "$actual_sha256" == "$expected_sha256" ]]; then
      echo "Python 安装包 SHA256 校验通过。"
      return 0
    fi

    echo "下载文件 SHA256 校验失败，已拒绝使用该文件。"
    echo "期望：$expected_sha256"
    echo "实际：$actual_sha256"
  done

  echo "所有 Python 下载源均失败。请检查网络后重新运行安装器。"
  return 1
}

ensure_python_runtime() {
  if runtime_is_valid "$PYTHON_RUNTIME_ROOT"; then
    write_runtime_marker "$PYTHON_RUNTIME_ROOT" || return 1
    echo "已检测到 CCWS 托管 Python $PYTHON_VERSION：$PYTHON_RUNTIME_ROOT"
    return 0
  fi

  local runtime_parent="$(/usr/bin/dirname -- "$PYTHON_RUNTIME_ROOT")"
  local archive=""
  local expanded=""
  local staging=""
  local backup=""

  /bin/mkdir -p -- "$runtime_parent" || return 1
  TEMP_ROOT="$(/usr/bin/mktemp -d "${TMPDIR:-/tmp}/ccws-python.XXXXXX")" || return 1
  STAGING_ROOT="$(/usr/bin/mktemp -d "${PYTHON_RUNTIME_ROOT}.staging.XXXXXX")" || return 1
  staging="$STAGING_ROOT"
  archive="$TEMP_ROOT/$PYTHON_FILENAME"
  expanded="$TEMP_ROOT/expanded"

  download_archive "$archive" "$PYTHON_SHA256" || return 1

  echo "正在验证 Python 官方安装包签名……"
  /usr/sbin/pkgutil --check-signature "$archive" >/dev/null || {
    echo "Python 安装包签名无效，安装已停止。"
    return 1
  }

  /usr/sbin/pkgutil --expand-full "$archive" "$expanded" || return 1
  /usr/bin/ditto "$expanded/Python_Framework.pkg/Payload" "$staging/Python.framework" || return 1

  /usr/bin/security find-certificate \
    -a -p /System/Library/Keychains/SystemRootCertificates.keychain \
    > "$staging/$PYTHON_CERTIFICATE_RELATIVE_PATH" || return 1
  if [[ -f /Library/Keychains/System.keychain ]]; then
    /usr/bin/security find-certificate \
      -a -p /Library/Keychains/System.keychain \
      >> "$staging/$PYTHON_CERTIFICATE_RELATIVE_PATH" 2>/dev/null || true
  fi
  /bin/chmod 600 "$staging/$PYTHON_CERTIFICATE_RELATIVE_PATH" || return 1

  runtime_is_valid "$staging" || {
    echo "下载的 Python 运行时未通过启动验证，安装已停止。"
    return 1
  }
  write_runtime_marker "$staging" || return 1

  if [[ -e "$PYTHON_RUNTIME_ROOT" || -L "$PYTHON_RUNTIME_ROOT" ]]; then
    backup="${PYTHON_RUNTIME_ROOT}.backup-$(/bin/date +%Y%m%d-%H%M%S)-$$"
    /bin/mv -- "$PYTHON_RUNTIME_ROOT" "$backup" || return 1
    echo "原有异常运行时已备份到：$backup"
  fi

  if ! /bin/mv -- "$staging" "$PYTHON_RUNTIME_ROOT"; then
    if [[ -n "$backup" && ! -e "$PYTHON_RUNTIME_ROOT" && -e "$backup" ]]; then
      /bin/mv -- "$backup" "$PYTHON_RUNTIME_ROOT" || true
    fi
    return 1
  fi
  STAGING_ROOT=""
  echo "Python $PYTHON_VERSION 已安装到当前用户目录：$PYTHON_RUNTIME_ROOT"
}

main() {
  cd "$SCRIPT_DIR" || return 1
  [[ -f "$MANIFEST" ]] || {
    echo "缺少 Python 运行时清单：$MANIFEST"
    return 1
  }

  PYTHON_VERSION="$(manifest_value version)" || return 1
  PYTHON_FILENAME="$(manifest_value macos.filename)" || return 1
  PYTHON_SHA256="$(manifest_value macos.sha256)" || return 1
  PYTHON_RELATIVE_PATH="$(manifest_value macos.python_relative_path)" || return 1
  PYTHON_LIBRARY_RELATIVE_PATH="$(manifest_value macos.library_relative_path)" || return 1
  PYTHON_CERTIFICATE_RELATIVE_PATH="$(manifest_value macos.certificate_relative_path)" || return 1
  PYTHON_RUNTIME_ROOT="${CCWS_PYTHON_RUNTIME_ROOT:-$HOME/Library/Application Support/CCWS/Python/$PYTHON_VERSION}"

  ensure_python_runtime || return 1

  local python_bin="$PYTHON_RUNTIME_ROOT/$PYTHON_RELATIVE_PATH"
  local framework_path="$PYTHON_RUNTIME_ROOT"
  local library_path="$PYTHON_RUNTIME_ROOT/$PYTHON_LIBRARY_RELATIVE_PATH"
  local cert_file="$PYTHON_RUNTIME_ROOT/$PYTHON_CERTIFICATE_RELATIVE_PATH"
  local -a install_args

  install_args=(--yes)
  if (( $# == 0 )); then
    install_args+=(--interactive)
  else
    install_args+=("$@")
  fi
  install_args+=(
    --python-executable "$python_bin"
    --python-framework-path "$framework_path"
    --python-library-path "$library_path"
    --ssl-cert-file "$cert_file"
  )

  runtime_env "$PYTHON_RUNTIME_ROOT" "$SCRIPT_DIR/install.py" "${install_args[@]}"
}

main "$@"
STATUS=$?

echo
if [[ $STATUS -eq 0 ]]; then
  echo "CCWS Image Generation 安装完成，可以关闭此窗口。"
else
  echo "安装失败，请保留上面的错误信息。"
fi

exit $STATUS
