#!/usr/bin/env python3
"""check_commits.py <base_branch> [<head_ref>]

Validates that every commit on the current branch (since it diverged from
origin/<base_branch>) follows the organisation-wide commit message convention:

    [TAG] scope: short description in imperative mood

Rules enforced:
  - Subject line must match the pattern  [TAG] scope: description
  - TAG must be one of the recognised tags (case-sensitive, upper-case)
  - scope must be non-empty (the module, package, or area being changed)
  - description must be non-empty after the colon + space
  - Total subject line length should be ≤ 72 characters (warning only, not a failure)

Exempt commits (not validated):
  - GitHub auto-generated merge commits  ("Merge pull request …", "Merge branch …")
  - GitHub auto-generated revert commits ("Revert \\"…\\"")
  - Empty subject lines (git internal, e.g. merge-base calculations)

Exit codes:
  0  — all commits conform
  1  — one or more commits do not conform (prints a clear report)
"""

import re
import subprocess
import sys

# ---------------------------------------------------------------------------
# Valid tags — extend this list if new tags are adopted org-wide.
# ---------------------------------------------------------------------------
VALID_TAGS = {
    "ADD",    # new modules, features, files
    "FIX",    # bug fixes
    "UPD",    # dependency or data updates
    "REF",    # refactoring (heavy rewrite)
    "REM",    # removing resources, dead code, modules
    "MOV",    # moving / renaming files (no content changes)
    "IMP",    # incremental improvements (most common)
    "REL",    # release commits
    "MERGE",  # forward-port / cross-branch merges
    "REV",    # reverting a previous commit
    "CLN",    # code cleanup
    "LINT",   # linting / formatting passes
    "PERF",   # performance improvements
    "I18N",   # translation / i18n changes
    "CLA",    # Contributor License Agreement
    "SEC",    # security patches (added for completeness)
    "DOCS",   # documentation-only commits
    "TEST",   # test-only commits
    "CI",     # CI/CD configuration
    "CHORE",  # maintenance tasks (deps, tooling)
}

# Subject-line regex: [TAG] scope: description
# - TAG: one or more upper-case letters/digits
# - scope: anything except colon (trimmed)
# - description: anything after ": "
SUBJECT_RE = re.compile(r"^\[([A-Z][A-Z0-9]*)\] ([^:]+): (.+)$")

# Commits generated automatically by GitHub — exempt from format enforcement.
EXEMPT_PREFIXES = (
    "Merge pull request ",   # GitHub PR merge button
    "Merge branch ",         # git merge
    "Merge tag ",            # tag merges
    "Merge remote-tracking ",
    "Revert \"",             # GitHub revert button (preferred: use [REV])
    "Initial commit",        # first commit of a new repo
)


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


def validate_subject(subject: str) -> list[str]:
    """Return a list of validation errors for a commit subject line.
    Empty list means the commit is valid.
    """
    errors = []

    # Empty subject — skip silently (git internals)
    if not subject:
        return []

    # Exempt patterns
    for prefix in EXEMPT_PREFIXES:
        if subject.startswith(prefix):
            return []

    m = SUBJECT_RE.match(subject)
    if not m:
        errors.append(
            f"Does not match required format: [TAG] scope: description\n"
            f"    Got: {subject!r}"
        )
        return errors   # no point checking further if the base format is wrong

    tag, scope, description = m.group(1), m.group(2).strip(), m.group(3).strip()

    if tag not in VALID_TAGS:
        valid = ", ".join(sorted(VALID_TAGS))
        errors.append(
            f"Unknown tag [{tag}]. Valid tags: {valid}"
        )

    if not scope:
        errors.append("Scope is empty. Use the module, package, or area name.")

    if not description:
        errors.append("Description is empty. Add a short imperative sentence.")

    # Soft check: length warning (not a failure)
    if len(subject) > 72:
        print(
            f"  ⚠  Subject is {len(subject)} chars (recommended ≤ 72): {subject!r}",
            file=sys.stderr,
        )

    return errors


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: check_commits.py <base_branch>", file=sys.stderr)
        sys.exit(1)

    base_branch = sys.argv[1]
    commits = get_commits(base_branch)

    if not commits:
        print("No commits found to validate — nothing to check.")
        return 0

    print(f"Checking {len(commits)} commit(s) against origin/{base_branch}…")

    failures: list[tuple[str, str, list[str]]] = []

    for sha, subject in commits:
        errors = validate_subject(subject)
        if errors:
            failures.append((sha, subject, errors))
        else:
            print(f"  ✓  {sha}  {subject}")

    if not failures:
        print(f"\nAll {len(commits)} commit(s) follow the convention. ✓")
        return 0

    # ------------------------------------------------------------------
    # Print a clear, actionable failure report
    # ------------------------------------------------------------------
    print(f"\n{'='*72}")
    print(f"FAIL: {len(failures)} commit(s) do not follow the convention.")
    print(f"{'='*72}\n")

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
    print("Valid tags:")
    tags_sorted = sorted(VALID_TAGS)
    for i in range(0, len(tags_sorted), 6):
        print("  " + "  ".join(f"[{t}]" for t in tags_sorted[i:i+6]))
    print()
    print("Examples:")
    print("  [IMP] unifica_payment: add retry logic for failed transactions")
    print("  [FIX] auth: fix token expiry not refreshing on concurrent requests")
    print("  [ADD] ui: add dark mode toggle to settings page")
    print("  [REF] api: extract validation helpers into shared module")
    print("  [CI]  .github: add commit message lint check to PR pipeline")
    print()
    print(
        "Tip: amend your commit with  git commit --amend  or rebase with\n"
        "     git rebase -i origin/{} to fix the messages before pushing.".format(base_branch)
    )
    print()

    return 1


if __name__ == "__main__":
    sys.exit(main())
