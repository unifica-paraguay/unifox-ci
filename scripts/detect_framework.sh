#!/usr/bin/env bash
# detect_framework.sh
# Auto-detects the framework/profile of a repository.
# Outputs one of: odoo | react | astro | python | node | default
#
# Detection order (first match wins):
#   1. .unifox.yml  — explicit profile field always wins
#   2. __manifest__.py anywhere  → odoo
#   3. astro.config.*            → astro
#   4. package.json with react   → react
#   5. package.json (any)        → node
#   6. pyproject.toml / setup.py / setup.cfg / requirements.txt → python
#   7. fallback                  → default
set -euo pipefail

REPO_ROOT="${1:-.}"

# 1. Explicit .unifox.yml profile field
if [ -f "${REPO_ROOT}/.unifox.yml" ]; then
  profile=$(grep -E '^profile:' "${REPO_ROOT}/.unifox.yml" 2>/dev/null \
    | head -1 | sed 's/profile:[[:space:]]*//' | tr -d "'\""  | xargs)
  if [ -n "$profile" ] && [ "$profile" != "auto" ]; then
    echo "$profile"
    exit 0
  fi
fi

# 2. Odoo module manifest
if find "${REPO_ROOT}" -maxdepth 3 -name "__manifest__.py" -not -path "*/node_modules/*" \
     -not -path "*/.git/*" 2>/dev/null | grep -q .; then
  echo "odoo"
  exit 0
fi

# 3. Astro config file
if find "${REPO_ROOT}" -maxdepth 2 \
     \( -name "astro.config.ts" -o -name "astro.config.mjs" -o -name "astro.config.js" \) \
     2>/dev/null | grep -q .; then
  echo "astro"
  exit 0
fi

# 4. React (package.json with "react" as a dependency)
if [ -f "${REPO_ROOT}/package.json" ]; then
  if python3 -c "
import json, sys
try:
    data = json.load(open('${REPO_ROOT}/package.json'))
    deps = {**data.get('dependencies', {}), **data.get('devDependencies', {})}
    sys.exit(0 if 'react' in deps or 'next' in deps else 1)
except Exception:
    sys.exit(1)
" 2>/dev/null; then
    echo "react"
    exit 0
  fi
  # Any other package.json → generic Node
  echo "node"
  exit 0
fi

# 5. Python project files
if [ -f "${REPO_ROOT}/pyproject.toml" ] \
  || [ -f "${REPO_ROOT}/setup.py" ] \
  || [ -f "${REPO_ROOT}/setup.cfg" ] \
  || [ -f "${REPO_ROOT}/requirements.txt" ] \
  || [ -f "${REPO_ROOT}/requirements-dev.txt" ]; then
  echo "python"
  exit 0
fi

# Fallback
echo "default"
