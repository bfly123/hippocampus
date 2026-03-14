#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [[ -f "$SCRIPT_DIR/pyproject.toml" ]]; then
  ROOT_DIR="$SCRIPT_DIR"
elif [[ -f "$SCRIPT_DIR/../pyproject.toml" ]]; then
  ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
else
  echo "Could not locate repository root from $SCRIPT_DIR" >&2
  exit 1
fi
USER_CONFIG_BASE="${HIPPOCAMPUS_USER_CONFIG_DIR:-$HOME/.hippocampus}"
LLM_CONFIG_PATH="$USER_CONFIG_BASE/hippocampus-llm.yaml"
ARCHITEC_USER_CONFIG_BASE="${ARCHITEC_USER_CONFIG_DIR:-$HOME/.architec}"
ARCHITEC_LLM_CONFIG_PATH="$ARCHITEC_USER_CONFIG_BASE/architec-llm.yaml"
EXAMPLE_CONFIG_PATH="$ROOT_DIR/config/hippocampus-llm.example.yaml"
LLMGATEWAY_LOCAL_PATH="${LLMGATEWAY_LOCAL_PATH:-$ROOT_DIR/../llmgateway}"
LLMGATEWAY_GIT_URL="${LLMGATEWAY_GIT_URL:-git+https://github.com/bfly123/llmgateway.git@main}"
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

prompt_with_default() {
  local var_name="$1"
  local prompt_text="$2"
  local default_value="${3:-}"
  local value="${!var_name:-}"

  if [[ -n "$value" ]]; then
    printf -v "$var_name" '%s' "$value"
    return 0
  fi

  if ! is_interactive; then
    printf -v "$var_name" '%s' "$default_value"
    return 0
  fi

  read -r -p "$prompt_text" value
  if [[ -z "$value" ]]; then
    value="$default_value"
  fi
  printf -v "$var_name" '%s' "$value"
}

prompt_optional() {
  local var_name="$1"
  local prompt_text="$2"
  local secret="${3:-0}"
  local default_value="${4:-}"
  local value="${!var_name:-}"

  if [[ -n "$value" ]]; then
    printf -v "$var_name" '%s' "$value"
    return 0
  fi

  if ! is_interactive; then
    printf -v "$var_name" '%s' "$default_value"
    return 0
  fi

  if [[ "$secret" == "1" ]]; then
    read -r -s -p "$prompt_text" value
    echo
  else
    read -r -p "$prompt_text" value
  fi
  if [[ -z "$value" ]]; then
    value="$default_value"
  fi
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
  loaded="$(python3 - "$source_path" <<'PY'
import sys
import json
from pathlib import Path

from hippocampus.architec_llm_compat import load_architec_llm_as_hippo
from hippocampus.user_llm_config import load_user_llm_config

path = Path(sys.argv[1])
if path.name == "architec-llm.yaml":
    loaded = load_architec_llm_as_hippo(path)
else:
    loaded = load_user_llm_config(path)

llm = loaded.get("llm", {}) if isinstance(loaded, dict) else {}
if not isinstance(llm, dict):
    llm = {}
phase_models = llm.get("phase_models", {})
if not isinstance(phase_models, dict):
    phase_models = {}
phase_reasoning_effort = llm.get("phase_reasoning_effort", {})
if not isinstance(phase_reasoning_effort, dict):
    phase_reasoning_effort = {}

base_url = str(llm.get("base_url", "") or llm.get("api_base", "") or "").strip()
api_key = str(llm.get("api_key", "") or "").strip()
small_model = str(phase_models.get("phase_1", "") or llm.get("fallback_model", "") or "").strip()
strong_model = str(phase_models.get("phase_2a", "") or phase_models.get("phase_3b", "") or small_model).strip()
max_concurrent = str(llm.get("max_concurrent", "") or "").strip()
small_effort = str(phase_reasoning_effort.get("phase_1", "") or "").strip().lower()
strong_effort = str(phase_reasoning_effort.get("phase_2a", "") or phase_reasoning_effort.get("phase_3b", "") or "").strip().lower()
model_map = llm.get("model_map", {})
if not isinstance(model_map, dict):
    model_map = {}
print(f"{base_url}\t{api_key}\t{small_model}\t{strong_model}\t{max_concurrent}\t{small_effort}\t{strong_effort}\t{json.dumps(model_map, ensure_ascii=True, sort_keys=True)}")
PY
)"

  local loaded_url loaded_key loaded_small_model loaded_strong_model loaded_max_concurrent loaded_small_effort loaded_strong_effort loaded_model_map
  IFS=$'\t' read -r loaded_url loaded_key loaded_small_model loaded_strong_model loaded_max_concurrent loaded_small_effort loaded_strong_effort loaded_model_map <<<"$loaded"
  if [[ -z "${hippocampus_llm_base_url:-}" && -n "$loaded_url" ]]; then
    hippocampus_llm_base_url="$loaded_url"
  fi
  if [[ -z "${hippocampus_llm_api_key:-}" && -n "$loaded_key" ]]; then
    hippocampus_llm_api_key="$loaded_key"
  fi
  if [[ -z "${hippocampus_llm_small_model:-}" && -n "$loaded_small_model" ]]; then
    hippocampus_llm_small_model="$loaded_small_model"
  fi
  if [[ -z "${hippocampus_llm_strong_model:-}" && -n "$loaded_strong_model" ]]; then
    hippocampus_llm_strong_model="$loaded_strong_model"
  fi
  if [[ -z "${hippocampus_llm_max_concurrent:-}" && -n "$loaded_max_concurrent" ]]; then
    hippocampus_llm_max_concurrent="$loaded_max_concurrent"
  fi
  if [[ -z "${hippocampus_llm_small_reasoning_effort:-}" && -n "$loaded_small_effort" ]]; then
    hippocampus_llm_small_reasoning_effort="$loaded_small_effort"
  fi
  if [[ -z "${hippocampus_llm_strong_reasoning_effort:-}" && -n "$loaded_strong_effort" ]]; then
    hippocampus_llm_strong_reasoning_effort="$loaded_strong_effort"
  fi
  if [[ -z "${hippocampus_llm_model_map_json:-}" && -n "$loaded_model_map" ]]; then
    hippocampus_llm_model_map_json="$loaded_model_map"
  fi
}

write_user_llm_config() {
  mkdir -p "$USER_CONFIG_BASE"
  python3 - "$LLM_CONFIG_PATH" "$hippocampus_llm_base_url" "$hippocampus_llm_api_key" "$hippocampus_llm_small_model" "$hippocampus_llm_strong_model" "$hippocampus_llm_max_concurrent" "$hippocampus_llm_small_reasoning_effort" "$hippocampus_llm_strong_reasoning_effort" "$hippocampus_llm_model_map_json" <<'PY'
import sys
import json
from pathlib import Path

from hippocampus.user_llm_config import write_user_llm_config

model_map = json.loads(sys.argv[9]) if len(sys.argv) > 9 and sys.argv[9] else {}
if not isinstance(model_map, dict):
    model_map = {}

write_user_llm_config(
    Path(sys.argv[1]),
    base_url=sys.argv[2],
    api_key=sys.argv[3],
    model=sys.argv[4],
    small_model=sys.argv[4],
    strong_model=sys.argv[5],
    max_concurrent=int(sys.argv[6] or 4),
    small_reasoning_effort=sys.argv[7],
    strong_reasoning_effort=sys.argv[8],
    model_map=model_map,
)
PY
  chmod 600 "$LLM_CONFIG_PATH"
}

validate_llm_config() {
  python3 - "$ROOT_DIR" <<'PY'
import sys
from pathlib import Path

from hippocampus.config import load_config, require_llm_configured

root = Path(sys.argv[1]).resolve()
cfg = load_config(None, project_root=root)
require_llm_configured(cfg)
assert str(cfg.llm.base_url or cfg.llm.api_base or "").strip()
assert str(cfg.llm.api_key or "").strip()
assert str(cfg.llm.phase_models.phase_1 or "").strip()
assert str(cfg.llm.phase_models.phase_2a or "").strip()
PY
}

print_manual_config_hint() {
  echo "Skipped LLM config generation."
  echo "Manually create $LLM_CONFIG_PATH"
  echo "Reference template: $EXAMPLE_CONFIG_PATH"
}

has_llmgateway() {
  python3 - <<'PY' >/dev/null 2>&1
import importlib.util
import sys

sys.exit(0 if importlib.util.find_spec("llmgateway") else 1)
PY
}

install_llmgateway() {
  if has_llmgateway; then
    return 0
  fi
  if [[ -f "$LLMGATEWAY_LOCAL_PATH/pyproject.toml" ]]; then
    echo "Installing llmgateway from local checkout: $LLMGATEWAY_LOCAL_PATH"
    python3 -m pip install -e "$LLMGATEWAY_LOCAL_PATH"
    return 0
  fi
  echo "Installing llmgateway from GitHub: $LLMGATEWAY_GIT_URL"
  python3 -m pip install "$LLMGATEWAY_GIT_URL"
}

if [[ "${1:-}" == "--help" || "${1:-}" == "-h" ]]; then
  cat <<'EOF'
Usage: ./install.sh

Installs hippocampus from the current source checkout into the active Python
environment as an editable package, including dev and repomap dependencies.
Also installs the llmgateway dependency, preferring ../llmgateway when present.
Prompts for backend URL and API key during install.
Writes ~/.hippocampus/hippocampus-llm.yaml in plaintext using a simplified
providers/tiers/tasks structure aligned with architec.
If you skip URL or API key, install completes and prints the manual config path.
If ~/.architec/architec-llm.yaml exists, install reuses it as defaults.
EOF
  exit 0
fi

if [[ $# -gt 0 ]]; then
  echo "install.sh takes no arguments." >&2
  exit 1
fi

python3 -m pip install --upgrade pip
install_llmgateway
python3 -m pip install -e ".[dev,repomap]"

hippocampus_llm_base_url="${hippocampus_llm_base_url:-}"
hippocampus_llm_api_key="${hippocampus_llm_api_key:-}"
hippocampus_llm_small_model="${hippocampus_llm_small_model:-${hippocampus_llm_model:-gpt-5.4}}"
hippocampus_llm_strong_model="${hippocampus_llm_strong_model:-gpt-5.4}"
hippocampus_llm_max_concurrent="${hippocampus_llm_max_concurrent:-4}"
hippocampus_llm_small_reasoning_effort="${hippocampus_llm_small_reasoning_effort:-low}"
hippocampus_llm_strong_reasoning_effort="${hippocampus_llm_strong_reasoning_effort:-high}"
hippocampus_llm_model_map_json="${hippocampus_llm_model_map_json:-}"

load_existing_llm_config

if is_interactive; then
  prompt_optional hippocampus_llm_base_url "Hippo backend URL (leave blank to skip): " 0 "$hippocampus_llm_base_url"
  prompt_optional hippocampus_llm_api_key "Hippo API key (leave blank to skip): " 1 "$hippocampus_llm_api_key"
  if [[ -n "$hippocampus_llm_base_url" && -n "$hippocampus_llm_api_key" ]]; then
    prompt_with_default hippocampus_llm_small_model "Hippo small model [$hippocampus_llm_small_model]: " "$hippocampus_llm_small_model"
    prompt_with_default hippocampus_llm_strong_model "Hippo strong model [$hippocampus_llm_strong_model]: " "$hippocampus_llm_strong_model"
  fi
elif [[ -n "$hippocampus_llm_base_url" && -n "$hippocampus_llm_api_key" ]]; then
  :
else
  print_manual_config_hint
  exit 0
fi

if [[ -z "$hippocampus_llm_base_url" || -z "$hippocampus_llm_api_key" ]]; then
  print_manual_config_hint
  exit 0
fi

write_user_llm_config
validate_llm_config

echo "Saved Hippo LLM config to $LLM_CONFIG_PATH"
