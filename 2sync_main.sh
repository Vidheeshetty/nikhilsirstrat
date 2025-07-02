#!/usr/bin/env bash
# shellcheck disable=SC2086
set -euo pipefail

function green() { echo -e "\033[32m$1\033[0m"; }

# ------------------------------------------------------------------
# Flags: --yes (skip prompt)  --msg "annotation" ----------------------
# ------------------------------------------------------------------

AUTO_YES=0
SYNC_MSG=""

while [[ $# -gt 0 ]]; do
  case $1 in
    --yes)
      AUTO_YES=1
      shift
      ;;
    --msg)
      SYNC_MSG=$2
      shift 2
      ;;
    *)
      break
      ;;
  esac
done

# Prompt for message unless --yes provided with optional --msg
if [[ $AUTO_YES -eq 0 ]]; then
  read -rp "Sync message (tag annotation, leave blank for default): " msg
else
  msg=$SYNC_MSG
fi

# Ensure dev is up-to-date and green ----------------------------------
git checkout development
git pull --ff-only gitrepo development
pytest -q -k "not paper_trading_setup"

git checkout main
# Fast-forward only merge so main history is linear
if git merge --ff-only development; then
  green "Merged development ➜ main (fast-forward)"
else
  echo "❌ Cannot fast-forward. Rebase development or resolve conflicts first." >&2
  exit 1
fi

pytest -q -k "not paper_trading_setup"   # sanity after merge

# ------------------------------------------------------------------
# 4.   Semantic-version bump & tag ----------------------------------
# ------------------------------------------------------------------

# Ensure VERSION file exists
if [[ ! -f VERSION ]]; then
  echo "0.0.0" > VERSION
  git add VERSION
fi

ver=$(cat VERSION)
IFS=. read -r major minor patch <<<"$ver"
patch=$((patch+1))
new_ver="${major}.${minor}.${patch}"

# Guard against duplicate tag
if git rev-parse "refs/tags/v$new_ver" >/dev/null 2>&1; then
  echo "❌ Tag v$new_ver already exists" >&2; exit 1;
fi

# Update VERSION file
echo "$new_ver" > VERSION
git add VERSION
git commit -m "chore(release): v$new_ver"

# Optional mini-changelog from last tag
last_tag=$(git describe --tags --abbrev=0 2>/dev/null || echo "")
range=${last_tag}..HEAD
changelog=$(git log --oneline $range | sed 's/^/- /')

git tag -a "v$new_ver" -m "${msg:-release v$new_ver}" -m "\nChanges since ${last_tag:-initial}:\n$changelog"

git push gitrepo main --follow-tags

git checkout development

green "✅ main updated & tagged v$new_ver" 