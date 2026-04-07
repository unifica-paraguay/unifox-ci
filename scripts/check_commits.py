#!/usr/bin/env python3
"""check_commits.py <base_branch>

Validates that every commit on the current branch (since it diverged from
origin/<base_branch>) follows the organisation-wide commit message convention,
aligned with Odoo's git guidelines and general naming best practices:

    [TAG] scope: short description in imperative mood

Rules enforced (failures block the PR):
  - Subject must match the pattern  [TAG] scope: description
  - TAG must be one of the recognised tags (upper-case, see list below)
  - scope must be non-empty — use the technical module/package/area name;
    use "various" when multiple unrelated areas are touched
  - description must be non-empty
  - description must start with a verb in imperative mood — it should complete
    the sentence "if applied, this commit will <description>"
    (e.g. "add retry logic", NOT "added retry logic" or "adding retry logic")

Soft warnings (printed but do not block the PR):
  - Subject line longer than 50 characters (Odoo guideline: ideally < 50)
  - Description appears to use past tense (first word ends with -ed)
  - Description appears to use gerund/present-participle (first word ends with -ing)

Exempt commits (not validated):
  - GitHub auto-generated merge commits  ("Merge pull request …", "Merge branch …")
  - GitHub auto-generated revert commits ("Revert \\"…\\"")
  - Empty subject lines

Exit codes:
  0  — all commits conform
  1  — one or more commits do not conform
"""

import re
import subprocess
import sys

# ---------------------------------------------------------------------------
# Valid tags — Odoo's canonical set + sensible modern additions.
# All tags are UPPER-CASE. Extend only after org-wide agreement.
# ---------------------------------------------------------------------------
VALID_TAGS = {
    # ── Odoo canonical ─────────────────────────────────────────────────────
    "ADD",    # new modules, features, files
    "FIX",    # bug fixes
    "REF",    # refactoring — heavy rewrite of a feature
    "REM",    # removing resources: dead code, views, modules
    "MOV",    # moving/renaming files (no content change; use git mv)
    "IMP",    # incremental improvements (most common)
    "REL",    # release commits — new major or minor stable versions
    "MERGE",  # merge/forward-port commits
    "REV",    # reverting a previous commit
    "CLN",    # code cleanup
    "LINT",   # linting / formatting passes
    "PERF",   # performance improvements
    "I18N",   # translation / i18n changes
    "CLA",    # Contributor License Agreement
    # ── Extended (org additions) ───────────────────────────────────────────
    "UPD",    # dependency or data updates
    "SEC",    # security patches
    "DOCS",   # documentation-only changes
    "TEST",   # test-only changes
    "CI",     # CI/CD configuration changes
    "CHORE",  # maintenance: deps, tooling, config (no production code)
}

# Subject-line regex: [TAG] scope: description
# Allows any non-colon chars as scope (trimmed); description is everything after ": "
SUBJECT_RE = re.compile(r"^\[([A-Z][A-Z0-9]*)\] ([^:]+): (.+)$")

# Commits generated automatically by GitHub — exempt from format enforcement.
EXEMPT_PREFIXES = (
    "Merge pull request ",
    "Merge branch ",
    "Merge tag ",
    "Merge remote-tracking ",
    'Revert "',
    "Initial commit",
)

# GitHub auto-generates "Merge <sha> into <sha>" when syncing a branch via the UI.
_MERGE_SHA_RE = re.compile(r"^Merge [0-9a-f]{40} into [0-9a-f]{40}$")

# First words that suggest non-imperative mood (soft warnings only).
# Past tense: "added", "fixed", "updated", "removed" …
# Gerund:     "adding", "fixing", "updating" …
_PAST_TENSE_RE = re.compile(r"^[a-z]+ed$", re.IGNORECASE)
_GERUND_RE = re.compile(r"^[a-z]+ing$", re.IGNORECASE)


def get_commits(base_branch: str) -> list[tuple[str, str]]:
    """Return list of (sha_short, subject) for commits on this branch."""
    result = subprocess.run(
        ["git", "log", f"origin/{base_branch}...HEAD", "--format=%h|%s"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print(
            f"Warning: could not enumerate commits against origin/{base_branch}. "
            "Skipping commit message check.",
            file=sys.stderr,
        )
        return []

    commits = []
    for line in result.stdout.strip().splitlines():
        if not line.strip():
            continue
        sha, _, subject = line.partition("|")
        commits.append((sha.strip(), subject.strip()))
    return commits


def validate_subject(subject: str) -> tuple[list[str], list[str]]:
    """Return (errors, warnings) for a commit subject line.

    errors   — hard failures that block the PR
    warnings — soft issues printed but do not fail
    """
    errors: list[str] = []
    warnings: list[str] = []

    if not subject:
        return [], []

    for prefix in EXEMPT_PREFIXES:
        if subject.startswith(prefix):
            return [], []

    if _MERGE_SHA_RE.match(subject):
        return [], []

    m = SUBJECT_RE.match(subject)
    if not m:
        errors.append(
            "Does not match required format:  [TAG] scope: description\n"
            f"    Got: {subject!r}\n"
            "    Example: [IMP] sale_order: add automatic discount on bulk orders"
        )
        return errors, warnings   # no point continuing if base format is wrong

    tag, scope, description = m.group(1), m.group(2).strip(), m.group(3).strip()

    # ── TAG ────────────────────────────────────────────────────────────────
    if tag not in VALID_TAGS:
        valid_sorted = ", ".join(f"[{t}]" for t in sorted(VALID_TAGS))
        errors.append(
            f"Unknown tag [{tag}].\n"
            f"    Valid tags: {valid_sorted}"
        )

    # ── scope ───────────────────────────────────────────────────────────────
    if not scope:
        errors.append(
            "Scope is empty. Use the technical module, package, or area name.\n"
            "    Use 'various' when the change touches multiple unrelated areas."
        )

    # ── description ─────────────────────────────────────────────────────────
    if not description:
        errors.append("Description is empty.")
    else:
        first_word = description.split()[0] if description.split() else ""

        # Imperative mood check (soft warning — heuristic)
        if _PAST_TENSE_RE.match(first_word):
            warnings.append(
                f"Description starts with past tense ({first_word!r}).\n"
                "    Use imperative mood: the subject should complete\n"
                '    "if applied, this commit will <description>".\n'
                f"    Suggestion: {description[len(first_word):].lstrip()!r} (remove the -ed suffix)"
            )
        elif _GERUND_RE.match(first_word):
            warnings.append(
                f"Description starts with a gerund ({first_word!r}).\n"
                "    Use imperative mood: the subject should complete\n"
                '    "if applied, this commit will <description>".\n'
                f"    Suggestion: drop the -ing form and use the base verb instead."
            )

    # ── subject length (soft limit: ~50 chars per Odoo guideline) ──────────
    if len(subject) > 72:
        errors.append(
            f"Subject is {len(subject)} chars — hard limit is 72.\n"
            "    Keep it under 50 for readability (Odoo guideline)."
        )
    elif len(subject) > 50:
        warnings.append(
            f"Subject is {len(subject)} chars. Odoo recommends ≤ 50 for readability."
        )

    return errors, warnings


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: check_commits.py <base_branch>", file=sys.stderr)
        sys.exit(1)

    base_branch = sys.argv[1]
    commits = get_commits(base_branch)

    if not commits:
        print("No commits found to validate — nothing to check.")
        return 0

    print(f"Checking {len(commits)} commit(s) against origin/{base_branch}…\n")

    failures: list[tuple[str, str, list[str]]] = []
    total_warnings = 0

    for sha, subject in commits:
        errors, warnings = validate_subject(subject)
        if errors:
            failures.append((sha, subject, errors))
            print(f"  ✗  {sha}  {subject}")
        else:
            print(f"  ✓  {sha}  {subject}")

        for w in warnings:
            total_warnings += 1
            for line in w.splitlines():
                print(f"       ⚠  {line}", file=sys.stderr)

    print()

    if not failures:
        if total_warnings:
            print(f"All {len(commits)} commit(s) follow the convention. ✓  ({total_warnings} warning(s) above)")
        else:
            print(f"All {len(commits)} commit(s) follow the convention. ✓")
        return 0

    # ── Failure report ──────────────────────────────────────────────────────
    sep = "=" * 72
    print(sep)
    print(f"FAIL: {len(failures)} of {len(commits)} commit(s) do not follow the convention.")
    print(sep)
    print()

    for sha, subject, errors in failures:
        print(f"  ✗  Commit {sha}")
        print(f"     Subject: {subject!r}")
        for err in errors:
            for line in err.splitlines():
                print(f"     → {line}")
        print()

    print("─" * 72)
    print("Required format:  [TAG] scope: short description (imperative mood)")
    print()
    print("  • [TAG]   — upper-case tag (see list below)")
    print("  • scope   — technical module/package/area name (use 'various' for cross-cutting changes)")
    print("  • description — imperative present tense; completes the sentence:")
    print('                  "if applied, this commit will <description>"')
    print()

    col_tags = sorted(VALID_TAGS)
    print("Valid tags:")
    for i in range(0, len(col_tags), 7):
        print("  " + "  ".join(f"[{t}]" for t in col_tags[i:i+7]))
    print()

    print("Good examples:")
    print("  [IMP] sale_order: add automatic discount on bulk orders")
    print("  [FIX] auth: prevent token refresh race condition on concurrent requests")
    print("  [ADD] payment_stripe: integrate Stripe checkout for subscriptions")
    print("  [REF] api: extract validation helpers into shared utils module")
    print("  [CI]  .github: add commit message check to PR pipeline")
    print()
    print("Bad examples (and why):")
    print("  [IMP] sale_order: added discount logic  ← past tense, use 'add'")
    print("  [fix] auth: bugfix                      ← tag must be upper-case; description too vague")
    print("  [IMP]: remove unused code               ← scope is missing")
    print()
    print(
        "Tip: fix commit messages with  git commit --amend  or\n"
        f"     git rebase -i origin/{base_branch}"
    )
    print()

    return 1


if __name__ == "__main__":
    sys.exit(main())
