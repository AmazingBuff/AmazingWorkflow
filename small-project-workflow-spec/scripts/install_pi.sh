#!/usr/bin/env bash
# Install the small-project workflow into a target project for Pi.
#
# Usage:
#   scripts/install_pi.sh [target-project-dir]
#
#   Default target: the directory containing this repository
#   (i.e. the parent of the repo root).
#
# Overridable via environment:
#   SPW_STRONG_MODEL      strong-role model selector (default: deepseek/deepseek-v4-pro)
#   SPW_EXECUTION_MODEL   execution-role model selector (default: deepseek/deepseek-v4-flash)
#   SPW_STRONG_THINKING   thinking level for strong roles (default: max)
#   SPW_EXECUTION_THINKING thinking level for execution roles (default: max)
#
# The defaults were verified against `pi models` on this machine at install time.
# Re-run with `pi models` first if your Pi model setup changes.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
DEFAULT_TARGET="$(cd "${REPO_ROOT}/.." && pwd)"
TARGET="${1:-${DEFAULT_TARGET}}"

STRONG_MODEL="${SPW_STRONG_MODEL:-deepseek/deepseek-v4-pro}"
EXECUTION_MODEL="${SPW_EXECUTION_MODEL:-deepseek/deepseek-v4-flash}"
STRONG_THINKING="${SPW_STRONG_THINKING:-max}"
EXECUTION_THINKING="${SPW_EXECUTION_THINKING:-max}"

if [ ! -d "${TARGET}" ]; then
  echo "error: target project directory does not exist: ${TARGET}" >&2
  exit 1
fi
TARGET="$(cd "${TARGET}" && pwd)"
if [ "${TARGET}" = "${REPO_ROOT}" ]; then
  echo "error: refusing to install into the workflow spec repository itself" >&2
  exit 1
fi

echo ">> Verifying model selectors against pi models-store ..."
STORE="${HOME}/.pi/agent/models-store.json"
if [ ! -f "${STORE}" ]; then
  echo "warning: ${STORE} not found; skipping model verification (extension will enforce availability at runtime)"
else
  for selector in "${STRONG_MODEL}" "${EXECUTION_MODEL}"; do
    if ! python - "${selector}" "${STORE}" <<'PY' ; then
import json, sys
selector, store_path = sys.argv[1], sys.argv[2]
provider, _, model_id = selector.partition("/")
data = json.load(open(store_path, encoding="utf-8"))
ids = {m["id"] for p in data.values() if isinstance(p, dict) for m in p.get("models", [])}
sys.exit(0 if model_id in ids else 1)
PY
      echo "error: model ${selector} not found in ${STORE}; adjust SPW_*_MODEL" >&2
      exit 1
    fi
  done
fi

TMP_DIR="$(mktemp -d)"
trap 'rm -rf "${TMP_DIR}"' EXIT

echo ">> Building pi bundle ..."
python "${REPO_ROOT}/scripts/build_harness.py" \
  --harness pi \
  --output "${TMP_DIR}/bundle" \
  --force \
  --strong-model "${STRONG_MODEL}" \
  --execution-model "${EXECUTION_MODEL}" \
  --strong-thinking "${STRONG_THINKING}" \
  --execution-thinking "${EXECUTION_THINKING}"

echo ">> Validating bundle ..."
python "${REPO_ROOT}/scripts/validate_bundle.py" "${TMP_DIR}/bundle"

echo ">> Installing .pi into ${TARGET} ..."
if [ -e "${TARGET}/.pi" ]; then
  rm -rf "${TARGET}/.pi"
fi
cp -r "${TMP_DIR}/bundle/.pi" "${TARGET}/.pi"

echo
echo "Installed small-project workflow into: ${TARGET}/.pi"
echo
echo "Next steps:"
echo "  1. Open pi in ${TARGET} and trust the project (the extension requires project trust)."
echo "  2. Start or continue the workflow with:  /small-project <request>"
echo "  3. Inspect .pi/agents and .pi/extensions before trusting; they are project-controlled."
