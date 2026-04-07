# unifox-ci 🦊

AI-powered CI/CD bot for Unifica Paraguay repositories.

unifox-ci is the automation layer that lives alongside every PR in Unifica
repos. It enriches pull requests, enforces Odoo coding and git standards,
bumps module versions automatically, runs Odoo tests, and generates release
changelogs — all powered by Claude.

The fox is the spirit of Unifica: quick, precise, and always watching your PRs.

---

## What it does

| Action | What happens |
|--------|-------------|
| **PR Enrich** | Evaluates and updates PR title (Odoo `[TAG]` format) and description (Purpose/Changes/Notes), assigns reviewers on first open |
| **PR Review** | Stateful AI code review with inline comments; tracks thread resolution across pushes; enforces Odoo coding guidelines |
| **PR Version Bump** | Detects changed modules, asks Claude for the correct semver bump, commits to the PR branch |
| **PR Static Checks** | Branch naming, version bump, manifest & structure, test existence, flake8 |
| **Odoo Tests Layer 1** | Runs test suite for modified modules only (fast, blocks merge) |
| **Odoo Tests Layer 2** | Runs test suite for native Odoo dependencies of modified modules (regression, blocks merge) |
| **Odoo Tests Layer 3** | Full nightly suite across all modules, no tag filter — opens a GitHub issue on failure |
| **Release Prepare** | Generates AI changelog, creates git tag, publishes GitHub Release |

---

## Installing in a new repository

### 1. Ensure org secrets are configured

The following secrets must exist at the **organization** level
(Settings → Secrets → Actions):

| Secret | Description |
|--------|-------------|
| `UNIFOX_CI_APP_ID` | GitHub App ID for unifox-ci |
| `UNIFOX_CI_PRIVATE_KEY` | GitHub App private key |
| `ANTHROPIC_API_KEY` | Anthropic Claude API key |

### 2. Add `.unifox.yml` to the repo root

```bash
cp .unifox.yml.example .unifox.yml
# Edit as needed
```

### 3. Add the workflows

Create `.github/workflows/pr-pipeline.yml` (orchestrator) and the individual
thin workflow files shown below. Copy the examples from `examples/` or write
them from scratch — each workflow is just a few lines that delegate to the
composite actions here.

**`pr-pipeline.yml`** (sequences stages with `needs:`):
```yaml
name: PR Pipeline
on:
  pull_request:
    branches: ["19.0"]
    types: [opened, synchronize, reopened]
permissions:
  contents: write
  pull-requests: write
jobs:
  ai-enrich:
    name: AI Enrichment
    uses: ./.github/workflows/pr-ai-enrich.yml
    secrets: inherit
  version-bump:
    name: Version Bump
    needs: [ai-enrich]
    if: always() && needs.ai-enrich.result != 'cancelled'
    uses: ./.github/workflows/pr-version-bump.yml
    secrets: inherit
  static-checks:
    name: Static Checks
    needs: [version-bump]
    if: always() && needs.version-bump.result != 'cancelled'
    uses: ./.github/workflows/pr-static-checks.yml
    secrets: inherit
  odoo-tests:
    name: Odoo Tests — Layer 1
    needs: [version-bump]
    if: always() && needs.version-bump.result != 'cancelled'
    uses: ./.github/workflows/pr-odoo-tests.yml
    secrets: inherit
  dependency-tests:
    name: Odoo Tests — Layer 2
    needs: [version-bump]
    if: always() && needs.version-bump.result != 'cancelled'
    uses: ./.github/workflows/pr-dependency-tests.yml
    secrets: inherit
```

**Each delegating workflow** (example for `pr-ai-enrich.yml`):
```yaml
name: PR AI Enrichment
on:
  workflow_call:
permissions:
  contents: read
  pull-requests: write
jobs:
  enrich-metadata:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with: { fetch-depth: 0 }
      - uses: unifica-paraguay/unifox-ci/actions/pr-enrich@v1
        with:
          anthropic_api_key: ${{ secrets.ANTHROPIC_API_KEY }}
          unifox_app_id: ${{ secrets.UNIFOX_CI_APP_ID }}
          unifox_private_key: ${{ secrets.UNIFOX_CI_PRIVATE_KEY }}
          base_branch: ${{ github.base_ref || 'main' }}
          event_action: ${{ github.event.action }}
          profile: odoo
  ai-code-review:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with: { fetch-depth: 0 }
      - uses: unifica-paraguay/unifox-ci/actions/pr-review@v1
        with:
          anthropic_api_key: ${{ secrets.ANTHROPIC_API_KEY }}
          unifox_app_id: ${{ secrets.UNIFOX_CI_APP_ID }}
          unifox_private_key: ${{ secrets.UNIFOX_CI_PRIVATE_KEY }}
          base_branch: ${{ github.base_ref || 'main' }}
          profile: odoo
```

---

## Profiles

| Profile | Use for |
|---------|---------|
| `odoo` | Odoo addons repositories — enforces coding guidelines, version bumps, Odoo test runner |
| `default` | Generic repositories — git guidelines only, flake8 lint |

---

## Repository structure

```
unifox-ci/
├── actions/              Composite actions (one per CI stage)
│   ├── pr-enrich/        Title, description, reviewer assignment
│   ├── pr-review/        AI code review with inline comments
│   ├── pr-version-bump/  Odoo module version bump
│   ├── pr-static-checks/ Branch naming, manifest, tests, lint
│   ├── odoo-tests-layer1/ Tests for modified modules
│   ├── odoo-tests-layer2/ Tests for native Odoo dependencies
│   ├── odoo-tests-layer3/ Full nightly suite, opens issue on failure
│   └── release-prepare/  Changelog + GitHub Release
├── scripts/              Shared Python/bash scripts
│   ├── claude_api.py     Claude API wrapper (reads CLAUDE.md + guidelines)
│   ├── detect_modules.sh Detects changed Odoo modules vs base branch
│   ├── check_version_bump.py
│   ├── check_manifest.py
│   └── check_tests.py
├── docker/               Docker Compose setup for Odoo tests
├── context/              Official Odoo guidelines (RST) loaded into Claude
│   ├── coding_guidelines.rst
│   ├── git_guidelines.rst
│   ├── content_guidelines.rst
│   └── rst_guidelines.rst
└── profiles/             Profile definitions (odoo.yml, default.yml)
```

---

## Versioning policy

unifox-ci uses **floating major tags** — the same pattern as `actions/checkout@v4`.

| Ref | Stability | Use for |
|-----|-----------|---------|
| `@v1` | ✅ Stable — always the latest `v1.x.x` | **Production** — use this in all consuming repos |
| `@v1.0.0` | 🔒 Pinned — exact commit, never moves | Emergency pin when you need strict reproducibility |
| `@main` | ⚠️ Unstable — may break at any push | Development and testing only |

### Releasing a new version

```bash
# Patch/minor fix — update v1 tag to the new commit
git tag v1.x.x          # create the immutable patch tag
git tag -f v1           # move the floating major tag forward
git push origin v1.x.x
git push origin v1 --force

# Breaking change — bump to v2
git tag v2.0.0
git tag v2
git push origin v2.0.0 v2
# Update consuming repos to use @v2
```

---

## Contributing

unifox-ci is itself an Odoo-adjacent project, so contributions follow the same
conventions:

- Commit format: `[TAG] scope: description` (see `context/git_guidelines.rst`)
- PRs need a clear **Purpose** section explaining WHY, not just what changed
- Test composite actions by pointing a test repo at your branch:
  `uses: unifica-paraguay/unifox-ci/actions/pr-enrich@your-branch`

---

*unifox-ci is maintained by the Unifica Paraguay team.*
