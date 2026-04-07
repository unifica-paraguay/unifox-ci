"""Unit tests for check_commits.validate_subject().

Run with:  python -m pytest scripts/tests/test_check_commits.py -v
"""

import sys
from pathlib import Path

# Make the scripts/ directory importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from check_commits import validate_subject


# ---------------------------------------------------------------------------
# Valid commits — should return no errors
# ---------------------------------------------------------------------------

def test_valid_imp():
    assert validate_subject("[IMP] auth: refresh token on concurrent requests") == []


def test_valid_fix():
    assert validate_subject("[FIX] payment: handle declined card gracefully") == []


def test_valid_add():
    assert validate_subject("[ADD] dashboard: add dark mode toggle") == []


def test_valid_ci():
    assert validate_subject("[CI] .github: add commit message lint check") == []


def test_valid_chore():
    assert validate_subject("[CHORE] deps: upgrade requests to 2.31") == []


def test_valid_docs():
    assert validate_subject("[DOCS] api: document authentication endpoints") == []


def test_valid_test():
    assert validate_subject("[TEST] auth: add unit tests for token refresh") == []


# ---------------------------------------------------------------------------
# Exempt commits — should pass through without validation
# ---------------------------------------------------------------------------

def test_exempt_merge_pr():
    assert validate_subject("Merge pull request #42 from org/feature-branch") == []


def test_exempt_merge_branch():
    assert validate_subject("Merge branch 'main' into feature/foo") == []


def test_exempt_revert():
    assert validate_subject('Revert "[FIX] auth: fix token expiry"') == []


def test_exempt_initial_commit():
    assert validate_subject("Initial commit") == []


def test_exempt_merge_tag():
    assert validate_subject("Merge tag 'v1.2.3' into main") == []


def test_exempt_empty_subject():
    assert validate_subject("") == []


# ---------------------------------------------------------------------------
# Invalid commits — should return at least one error
# ---------------------------------------------------------------------------

def test_missing_tag():
    errors = validate_subject("auth: fix token expiry")
    assert errors, "Expected errors for missing [TAG]"
    assert any("required format" in e for e in errors)


def test_unknown_tag():
    errors = validate_subject("[OOPS] auth: fix something")
    assert errors, "Expected errors for unknown tag"
    assert any("Unknown tag" in e for e in errors)


def test_missing_scope():
    errors = validate_subject("[FIX] : fix something")
    assert errors, "Expected errors for missing scope"


def test_missing_description():
    errors = validate_subject("[FIX] auth:")
    assert errors, "Expected errors for missing description"


def test_wrong_format_no_colon():
    errors = validate_subject("[FIX] auth fix the bug")
    assert errors, "Expected errors when colon+space separator is absent"


def test_wrong_format_plain_message():
    errors = validate_subject("fixed the login bug")
    assert errors, "Expected errors for plain commit message"


def test_lowercase_tag_fails():
    errors = validate_subject("[fix] auth: fix token expiry")
    assert errors, "Expected errors for lowercase tag"


# ---------------------------------------------------------------------------
# Length warning — should NOT fail (no errors returned), but prints to stderr
# ---------------------------------------------------------------------------

def test_long_subject_no_error(capsys):
    subject = "[IMP] auth: " + "x" * 80   # > 72 chars total
    errors = validate_subject(subject)
    assert errors == [], "Long subject should produce a warning, not an error"
    captured = capsys.readouterr()
    assert "72" in captured.err, "Expected length warning in stderr"
