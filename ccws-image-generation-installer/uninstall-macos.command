#!/bin/zsh

set -u
umask 077

SCRIPT_DIR="$(CDPATH= cd -- "$(/usr/bin/dirname -- "$0")" && pwd)"
MANIFEST="$SCRIPT_DIR/python-runtime.json"
SKILL_NAME="ccws-image-generation"
RUNTIME_MARKER_NAME=".ccws-managed-python-runtime"
ASSUME_YES=0
REFUSED_TARGETS=0
typeset -a TARGET_KINDS
typeset -a TARGET_PATHS
typeset -A SEEN_TARGETS

normalize_path() {
  local raw="$1"
  /usr/bin/printf '%s\n' "${raw:a}"
}

path_exists() {
  [[ -e "$1" || -L "$1" ]]
}

add_existing_target() {
  local kind="$1"
  local raw_path="$2"
  local path=""

  path="$(normalize_path "$raw_path")" || return 1
  path_exists "$path" || return 0
  [[ -n "${SEEN_TARGETS[$path]-}" ]] && return 0

  SEEN_TARGETS[$path]=1
  TARGET_KINDS+=("$kind")
  TARGET_PATHS+=("$path")
}

config_is_ccws() {
  local path="$1"
  local model=""

  [[ -f "$path" ]] || return 1
  model="$(/usr/bin/plutil -extract model raw -o - -- "$path" 2>/dev/null)" || return 1
  [[ "$model" == "gpt-image-2" ]]
}

runtime_has_marker() {
  local runtime_root="$1"
  local marker="$runtime_root/$RUNTIME_MARKER_NAME"
  local expected="ccws-image-generation:$PYTHON_VERSION"
  local actual=""

  [[ -f "$marker" ]] || return 1
  actual="$(/bin/cat -- "$marker" 2>/dev/null)" || return 1
  [[ "$actual" == "$expected" ]]
}

show_preserved_backups() {
  echo
  echo "以下历史 Skill 备份不会删除："
  echo "  - $HOME_PATH/.agents/skill-backups"
  echo "  - $HOME_PATH/.codex/skill-backups"
  if [[ -n "${CODEX_HOME:-}" ]]; then
    echo "  - $CODEX_HOME_PATH/skill-backups"
  fi
}

remove_target() {
  local kind="$1"
  local path="$2"

  case "$kind" in
    "配置")
      /bin/rm -f -- "$path"
      ;;
    "Skill"|"Python")
      /bin/rm -rf -- "$path"
      ;;
    *)
      echo "未知卸载目标类型：$kind"
      return 1
      ;;
  esac
}

main() {
  local argument=""
  local default_config=""
  local config_path=""
  local default_runtime=""
  local runtime_path=""
  local answer=""
  local failure=0
  local index=0
  local path=""
  local kind=""

  for argument in "$@"; do
    case "$argument" in
      --yes|-y)
        ASSUME_YES=1
        ;;
      *)
        echo "未知参数：$argument"
        echo "可用参数：--yes"
        return 2
        ;;
    esac
  done

  [[ -n "${HOME:-}" ]] || {
    echo "无法确定当前用户目录，卸载已停止。"
    return 1
  }
  [[ -f "$MANIFEST" ]] || {
    echo "缺少 Python 运行时清单：$MANIFEST"
    return 1
  }

  cd "$SCRIPT_DIR" || return 1
  HOME_PATH="$(normalize_path "$HOME")" || return 1
  PYTHON_VERSION="$(/usr/bin/plutil -extract version raw -o - -- "$MANIFEST")" || return 1

  add_existing_target "Skill" "$HOME_PATH/.agents/skills/$SKILL_NAME" || return 1
  add_existing_target "Skill" "$HOME_PATH/.codex/skills/$SKILL_NAME" || return 1
  CODEX_HOME_PATH=""
  if [[ -n "${CODEX_HOME:-}" ]]; then
    CODEX_HOME_PATH="$(normalize_path "$CODEX_HOME")" || return 1
    add_existing_target "Skill" "$CODEX_HOME_PATH/skills/$SKILL_NAME" || return 1
  fi

  default_config="$(normalize_path "$HOME_PATH/Library/Application Support/CCWS/image-generation.json")" || return 1
  config_path="$(normalize_path "${CCWS_IMAGE_CONFIG:-$default_config}")" || return 1
  if path_exists "$config_path"; then
    if [[ "$config_path" == "$default_config" ]] || config_is_ccws "$config_path"; then
      add_existing_target "配置" "$config_path" || return 1
    else
      echo "为避免误删，未识别的自定义配置文件不会删除：$config_path"
      REFUSED_TARGETS=1
    fi
  fi

  default_runtime="$(normalize_path "$HOME_PATH/Library/Application Support/CCWS/Python/$PYTHON_VERSION")" || return 1
  runtime_path="$(normalize_path "${CCWS_PYTHON_RUNTIME_ROOT:-$default_runtime}")" || return 1
  if path_exists "$runtime_path"; then
    if [[ "$runtime_path" == "$default_runtime" ]] || runtime_has_marker "$runtime_path"; then
      add_existing_target "Python" "$runtime_path" || return 1
    else
      echo "为避免误删，没有 CCWS 安全标记的自定义 Python 目录不会删除：$runtime_path"
      REFUSED_TARGETS=1
    fi
  fi

  if (( ${#TARGET_PATHS[@]} == 0 )); then
    if (( REFUSED_TARGETS )); then
      echo "未删除任何内容。请检查上面的安全提示。"
      return 1
    fi
    echo "未检测到需要卸载的 CCWS Image Generation 当前安装。"
    show_preserved_backups
    return 0
  fi

  echo "CCWS Image Generation 卸载器"
  echo
  echo "将删除以下当前安装内容："
  for ((index = 1; index <= ${#TARGET_PATHS[@]}; index++)); do
    echo "  - ${TARGET_KINDS[$index]}：${TARGET_PATHS[$index]}"
  done
  show_preserved_backups
  echo
  echo "系统 Python、PATH、其他 Skill 和上述历史备份不会修改。"

  if (( ! ASSUME_YES )); then
    /usr/bin/printf '确认卸载？输入 y 继续，直接回车取消: '
    IFS= read -r answer || answer=""
    answer="${answer:l}"
    if [[ "$answer" != "y" && "$answer" != "yes" ]]; then
      echo "已取消卸载，未删除任何内容。"
      return 0
    fi
  fi

  echo
  for ((index = 1; index <= ${#TARGET_PATHS[@]}; index++)); do
    kind="${TARGET_KINDS[$index]}"
    path="${TARGET_PATHS[$index]}"
    if remove_target "$kind" "$path" && ! path_exists "$path"; then
      echo "已删除 $kind：$path"
    else
      echo "删除失败 $kind：$path"
      failure=1
    fi
  done

  /bin/rmdir -- "$HOME_PATH/Library/Application Support/CCWS/Python" 2>/dev/null || true
  /bin/rmdir -- "$HOME_PATH/Library/Application Support/CCWS" 2>/dev/null || true

  if (( REFUSED_TARGETS )); then
    failure=1
  fi
  if (( failure )); then
    echo
    echo "卸载未完全完成，请保留上面的错误信息。"
    return 1
  fi

  echo
  echo "卸载完成。请重启 Codex，或新开一个 Codex 任务。"
  return 0
}

main "$@"
STATUS=$?

echo
if [[ $STATUS -eq 0 ]]; then
  echo "可以关闭此窗口。"
else
  echo "卸载器已停止，请检查上面的提示。"
fi

exit $STATUS
