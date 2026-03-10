#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
USER_CONFIG_BASE="${HIPPOCAMPUS_USER_CONFIG_DIR:-$HOME/.hippocampus}"
LLM_CONFIG_PATH="$USER_CONFIG_BASE/hippocampus-llm.yaml"
ARCHITEC_USER_CONFIG_BASE="${ARCHITEC_USER_CONFIG_DIR:-$HOME/.architec}"
ARCHITEC_LLM_CONFIG_PATH="$ARCHITEC_USER_CONFIG_BASE/architec-llm.yaml"
cd "$ROOT_DIR"

is_interactive() {
  [[ -t 0 && -t 1 ]]
}

prompt_required() {
  local var_name="$1"
  local prompt_text="$2"
  local secret="${3:-0}"
  local value="${!var_name:-}"

  if [[ -n "$value" ]]; then
    printf -v "$var_name" '%s' "$value"
    return 0
  fi

  if ! is_interactive; then
    echo "$var_name is required. Re-run install with $var_name set in the environment." >&2
    exit 1
  fi

  while [[ -z "$value" ]]; do
    if [[ "$secret" == "1" ]]; then
      read -r -s -p "$prompt_text" value
      echo
    else
      read -r -p "$prompt_text" value
    fi
    value="${value#"${value%%[![:space:]]*}"}"
    value="${value%"${value##*[![:space:]]}"}"
  done

  printf -v "$var_name" '%s' "$value"
}

load_existing_llm_config() {
  local source_path=""
  if [[ -f "$LLM_CONFIG_PATH" ]]; then
    source_path="$LLM_CONFIG_PATH"
  elif [[ -f "$ARCHITEC_LLM_CONFIG_PATH" ]]; then
    source_path="$ARCHITEC_LLM_CONFIG_PATH"
  fi
  if [[ -z "$source_path" ]]; then
    return 0
  fi

  local loaded
  loaded="$(python - "$source_path" <<'PY'
import sys
from pathlib import Path

import yaml

path = Path(sys.argv[1])
loaded = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
if isinstance(loaded, dict) and "llm" in loaded:
    llm = loaded.get("llm", {})
    if not isinstance(llm, dict):
        llm = {}
    base_url = str(llm.get("base_url", "") or llm.get("api_base", "") or "").strip()
    api_key = str(llm.get("api_key", "") or "").strip()
    model = str(llm.get("fallback_model", "") or "").strip()
else:
    providers = loaded.get("providers", {}) if isinstance(loaded, dict) else {}
    if not isinstance(providers, dict):
        providers = {}
    main = providers.get("main", {}) if isinstance(providers, dict) else {}
    if not isinstance(main, dict):
        main = {}
    tiers = loaded.get("tiers", {}) if isinstance(loaded, dict) else {}
    strong = tiers.get("strong", {}) if isinstance(tiers, dict) else {}
    candidates = strong.get("candidates", []) if isinstance(strong, dict) else []
    first = candidates[0] if isinstance(candidates, list) and candidates else {}
    base_url = str(main.get("base_url", "") or "").strip()
    api_key = str(main.get("api_key", "") or "").strip()
    model = str(first.get("model", "") or "").strip()
print(f"{base_url}\t{api_key}\t{model}")
PY
)"

  local loaded_url loaded_key loaded_model
  IFS=$'\t' read -r loaded_url loaded_key loaded_model <<<"$loaded"
  if [[ -z "${hippocampus_llm_base_url:-}" && -n "$loaded_url" ]]; then
    hippocampus_llm_base_url="$loaded_url"
  fi
  if [[ -z "${hippocampus_llm_api_key:-}" && -n "$loaded_key" ]]; then
    hippocampus_llm_api_key="$loaded_key"
  fi
  if [[ -z "${hippocampus_llm_model:-}" && -n "$loaded_model" ]]; then
    hippocampus_llm_model="$loaded_model"
  fi
}

write_user_llm_config() {
  mkdir -p "$USER_CONFIG_BASE"
  python - "$LLM_CONFIG_PATH" "$hippocampus_llm_base_url" "$hippocampus_llm_api_key" "$hippocampus_llm_model" <<'PY'
import sys
from pathlib import Path

from hippocampus.user_llm_config import write_user_llm_config

write_user_llm_config(
    Path(sys.argv[1]),
    base_url=sys.argv[2],
    api_key=sys.argv[3],
    model=sys.argv[4],
)
PY
  chmod 600 "$LLM_CONFIG_PATH"
}

if [[ "${1:-}" == "--help" || "${1:-}" == "-h" ]]; then
  cat <<'EOF'
Usage: ./scripts/install.sh

Installs hippocampus from the current source checkout into the active Python
environment as an editable package, including dev and repomap dependencies.
Writes user LLM config to ~/.hippocampus/hippocampus-llm.yaml
or $HIPPOCAMPUS_USER_CONFIG_DIR/hippocampus-llm.yaml.
If ~/.architec/architec-llm.yaml exists, install reuses it as defaults.
EOF
  exit 0
fi

if [[ $# -gt 0 ]]; then
  echo "install.sh takes no arguments." >&2
  exit 1
fi

python -m pip install --upgrade pip
python -m pip install -e ".[dev,repomap]"

hippocampus_llm_base_url="${hippocampus_llm_base_url:-}"
hippocampus_llm_api_key="${hippocampus_llm_api_key:-}"
hippocampus_llm_model="${hippocampus_llm_model:-openai/gpt-4o-mini}"

load_existing_llm_config
prompt_required hippocampus_llm_base_url "Hippo backend URL: "
prompt_required hippocampus_llm_api_key "Hippo API key: " 1
prompt_required hippocampus_llm_model "Hippo default model: "
write_user_llm_config

echo "Saved Hippo LLM config to $LLM_CONFIG_PATH"
