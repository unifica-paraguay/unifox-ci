#!/usr/bin/env bash
# detect_modules.sh <base_branch>
# Outputs a space-separated list of Odoo module directories modified in this branch
# compared to origin/<base_branch>.
set -euo pipefail

BASE_BRANCH="${1:-19.0}"

CHANGED_FILES=$(git diff --name-only "origin/${BASE_BRANCH}...HEAD" 2>/dev/null) || {
  echo "Warning: could not diff against origin/${BASE_BRANCH}" >&2
  exit 0
}

declare -A seen
MODULES=()

while IFS= read -r file; do
  [ -z "$file" ] && continue
  dir=$(echo "$file" | cut -d'/' -f1)
  if [ -z "${seen[$dir]:-}" ] && [ -f "${dir}/__manifest__.py" ]; then
    seen[$dir]=1
    MODULES+=("$dir")
  fi
done <<< "$CHANGED_FILES"

if [ ${#MODULES[@]} -gt 0 ]; then
  echo "${MODULES[*]}"
fi
