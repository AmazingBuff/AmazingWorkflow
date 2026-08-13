#!/usr/bin/env bash
# Install the small-project workflow for Pi.
#
# Usage:
#   scripts/install_pi.sh --global        Install globally (one-time per machine):
#                                         extension + /small-project prompt + 14 skills
#                                         + user-level fallback agents into ~/.pi/agent/.
#   scripts/install_pi.sh [project-dir]   Install into a project (default: the directory
#                                         containing this repository). Installs .pi/agents
#                                         (required project-scoped role files) and, when the
#                                         global install is absent, the full .pi bundle.
#
# Overridable via environment:
#   SPW_STRONG_MODEL      strong-role model selector (default: deepseek/deepseek-v4-pro)
#   SPW_EXECUTION_MODEL   execution-role model selector (default: deepseek/deepseek-v4-flash)
#   SPW_STRONG_THINKING   thinking level for strong roles (default: max)
#   SPW_EXECUTION_THINKING thinking level for execution roles (default: max)
#
# The defaults were verified against the pi models-store on this machine. Re-check
# with `pi models` if your Pi model setup changes.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
DEFAULT_TARGET="$(cd "${REPO_ROOT}/.." && pwd)"
AGENT_DIR="${PI_CODING_AGENT_DIR:-${HOME}/.pi/agent}"

STRONG_MODEL="${SPW_STRONG_MODEL:-deepseek/deepseek-v4-pro}"
EXECUTION_MODEL="${SPW_EXECUTION_MODEL:-deepseek/deepseek-v4-flash}"
STRONG_THINKING="${SPW_STRONG_THINKING:-max}"
EXECUTION_THINKING="${SPW_EXECUTION_THINKING:-max}"

MODE="project"
TARGET="${DEFAULT_TARGET}"
for arg in "$@"; do
  case "${arg}" in
    --global) MODE="global" ;;
    -h|--help) sed -n '2,12p' "$0"; exit 0 ;;
    *) TARGET="${arg}" ;;
  esac
done

verify_models() {
  local store="${AGENT_DIR}/models-store.json"
  if [ ! -f "${store}" ]; then
    echo "warning: ${store} not found; skipping model verification (extension enforces availability at runtime)"
    return
  fi
  local selector
  for selector in "${STRONG_MODEL}" "${EXECUTION_MODEL}"; do
    if ! python - "${selector}" "${store}" <<'PY' ; then
import json, sys
selector, store_path = sys.argv[1], sys.argv[2]
provider, _, model_id = selector.partition("/")
data = json.load(open(store_path, encoding="utf-8"))
ids = {m["id"] for p in data.values() if isinstance(p, dict) for m in p.get("models", [])}
sys.exit(0 if model_id in ids else 1)
PY
      echo "error: model ${selector} not found in ${store}; adjust SPW_*_MODEL" >&2
      exit 1
    fi
  done
}

build_bundle() {
  local out_dir="$1"
  python "${REPO_ROOT}/scripts/build_harness.py" \
    --harness pi \
    --output "${out_dir}" \
    --force \
    --strong-model "${STRONG_MODEL}" \
    --execution-model "${EXECUTION_MODEL}" \
    --strong-thinking "${STRONG_THINKING}" \
    --execution-thinking "${EXECUTION_THINKING}"
  python "${REPO_ROOT}/scripts/validate_bundle.py" "${out_dir}"
}

echo ">> Verifying model selectors against pi models-store ..."
verify_models

TMP_DIR="$(mktemp -d)"
trap 'rm -rf "${TMP_DIR}"' EXIT

if [ "${MODE}" = "global" ]; then
  echo ">> Building pi bundle ..."
  build_bundle "${TMP_DIR}/bundle"

  echo ">> Installing global parts into ${AGENT_DIR} ..."
  mkdir -p "${AGENT_DIR}/extensions" "${AGENT_DIR}/prompts" "${AGENT_DIR}/skills" "${AGENT_DIR}/agents"
  rm -rf "${AGENT_DIR}/extensions/small-project-subagents"
  cp -r "${TMP_DIR}/bundle/.pi/extensions/small-project-subagents" "${AGENT_DIR}/extensions/"
  cp -r "${TMP_DIR}/bundle/.pi/prompts/." "${AGENT_DIR}/prompts/"
  rm -rf "${AGENT_DIR}/skills"
  cp -r "${TMP_DIR}/bundle/.pi/skills/." "${AGENT_DIR}/skills/"
  rm -rf "${AGENT_DIR}/agents"
  cp -r "${TMP_DIR}/bundle/.pi/agents/." "${AGENT_DIR}/agents/"

  echo
  echo "Installed globally into ${AGENT_DIR}:"
  echo "  extensions/small-project-subagents/  (small_project_subagent tool)"
  echo "  prompts/small-project.md             (/small-project entry, available in every project)"
  echo "  skills/                              (14 small-project-* skills)"
  echo "  agents/                              (user-level fallback roles; project .pi/agents wins)"
  echo
  echo "Per project, run:  scripts/install_pi.sh <project-dir>"
  echo "Then in pi: trust the project and start with  /small-project <request>"
  exit 0
fi

if [ ! -d "${TARGET}" ]; then
  echo "error: target project directory does not exist: ${TARGET}" >&2
  exit 1
fi
TARGET="$(cd "${TARGET}" && pwd)"
if [ "${TARGET}" = "${REPO_ROOT}" ]; then
  echo "error: refusing to install into the workflow spec repository itself" >&2
  exit 1
fi

echo ">> Building pi bundle ..."
build_bundle "${TMP_DIR}/bundle"

GLOBAL_PARTS_PRESENT=0
[ -f "${AGENT_DIR}/extensions/small-project-subagents/index.ts" ] && GLOBAL_PARTS_PRESENT=1

echo ">> Installing into ${TARGET} ..."
mkdir -p "${TARGET}/.pi"
rm -rf "${TARGET}/.pi/agents"
cp -r "${TMP_DIR}/bundle/.pi/agents" "${TARGET}/.pi/agents"

if [ "${GLOBAL_PARTS_PRESENT}" = "1" ]; then
  echo "   (global extension/prompt/skills detected; skipping project-local copies to avoid duplicates)"
  rm -rf "${TARGET}/.pi/extensions" "${TARGET}/.pi/prompts" "${TARGET}/.pi/skills"
else
  echo "   (no global install detected; copying full self-contained bundle)"
  rm -rf "${TARGET}/.pi/extensions" "${TARGET}/.pi/prompts" "${TARGET}/.pi/skills"
  cp -r "${TMP_DIR}/bundle/.pi/extensions" "${TARGET}/.pi/"
  cp -r "${TMP_DIR}/bundle/.pi/prompts" "${TARGET}/.pi/"
  cp -r "${TMP_DIR}/bundle/.pi/skills" "${TARGET}/.pi/"
fi

echo
echo "Installed small-project workflow agents into: ${TARGET}/.pi/agents"
echo
echo "Next steps:"
echo "  1. Open pi in ${TARGET} and trust the project (the extension requires project trust)."
echo "  2. Start or continue the workflow with:  /small-project <request>"
echo "  3. Inspect .pi/agents before trusting; they are project-controlled and take"
echo "     precedence over the user-level fallback agents."
