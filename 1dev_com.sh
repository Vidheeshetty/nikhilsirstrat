#!/usr/bin/env bash
# shellcheck disable=SC2086
set -euo pipefail

# Allow non-interactive usage: 1dev_com.sh --msg "your commit message"
COMMIT_MSG=""
if [[ ${1:-""} == "--msg" ]]; then
  COMMIT_MSG=$2
  shift 2
fi

# -------------------------------
# 0. Ensure we are on development
# -------------------------------
if ! git rev-parse --verify development &>/dev/null; then
  echo "[INFO] Creating 'development' branch"
  git checkout -b development
else
  git checkout development
fi

# -------------------------------
# 1. Quality-gate: lint, type-check, unit tests
# -------------------------------

function green() { echo -e "\033[32m$1\033[0m"; }
function red()   { echo -e "\033[31m$1\033[0m"; }

echo "▶ Running Ruff lint …"
ruff check src utils scripts tests

echo "▶ Checking code format …"
ruff format --check src utils scripts tests

printf "\n▶ Running mypy type-checks …\n"
if command -v mypy &>/dev/null; then
  mypy src/ tests/
else
  echo "[WARN] mypy not found – skipping type-checks"
fi

printf "\n▶ Executing test-suite …\n"
pytest -q

green "✓ All quality checks passed"

# -------------------------------
# 2. Commit -----------------------------------------------------------
# -------------------------------
# If message not supplied, prompt interactively
if [[ -z "$COMMIT_MSG" ]]; then
  read -rp "Commit message: " COMMIT_MSG
fi

git add -u
if git diff --cached --quiet; then
  red "Nothing to commit – working tree clean"
  exit 0
fi

git commit -m "$COMMIT_MSG"
git push gitrepo development

green "✅ Committed & pushed to 'development' successfully" 