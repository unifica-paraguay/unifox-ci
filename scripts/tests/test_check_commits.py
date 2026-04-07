"""Unit tests for check_commits.validate_subject().

Run with:  python -m pytest scripts/tests/test_check_commits.py -v
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # noqa: E402

from check_commits import validate_subject  # noqa: E402


# ---------------------------------------------------------------------------
# Valid commits — should return no errors and no warnings
# ---------------------------------------------------------------------------

def test_valid_imp():
    errors, warnings = validate_subject("[IMP] auth: refresh token on concurrent requests")
    assert errors == []


def test_valid_fix():
    errors, warnings = validate_subject("[FIX] payment: handle declined card gracefully")
    assert errors == []


def test_valid_add():
    errors, warnings = validate_subject("[ADD] dashboard: add dark mode toggle")
    assert errors == []


def test_valid_ci():
    errors, warnings = validate_subject("[CI] .github: add commit message lint check")
    assert errors == []


def test_valid_chore():
    errors, warnings = validate_subject("[CHORE] deps: upgrade requests to 2.31")
    assert errors == []


def test_valid_docs():
    errors, warnings = validate_subject("[DOCS] api: document authentication endpoints")
    assert errors == []


def test_valid_test():
    errors, warnings = validate_subject("[TEST] auth: add unit tests for token refresh")
    assert errors == []


# ---------------------------------------------------------------------------
# Exempt commits — should pass through without validation
# ---------------------------------------------------------------------------

def test_exempt_merge_pr():
    errors, warnings = validate_subject("Merge pull request #42 from org/feature-branch")
    assert errors == [] and warnings == []


def test_exempt_merge_branch():
    errors, warnings = validate_subject("Merge branch 'main' into feature/foo")
    assert errors == [] and warnings == []


def test_exempt_revert():
    errors, warnings = validate_subject('Revert "[FIX] auth: fix token expiry"')
    assert errors == [] and warnings == []


def test_exempt_initial_commit():
    errors, warnings = validate_subject("Initial commit")
    assert errors == [] and warnings == []


def test_exempt_merge_tag():
    errors, warnings = validate_subject("Merge tag 'v1.2.3' into main")
    assert errors == [] and warnings == []


def test_exempt_empty_subject():
    errors, warnings = validate_subject("")
    assert errors == [] and warnings == []


def test_exempt_merge_sha():
    sha = "a" * 40
    errors, warnings = validate_subject(f"Merge {sha} into {sha}")
    assert errors == [] and warnings == []


# ---------------------------------------------------------------------------
# Invalid commits — should return at least one error
# ---------------------------------------------------------------------------

def test_missing_tag():
    errors, _ = validate_subject("auth: fix token expiry")
    assert errors, "Expected errors for missing [TAG]"
    assert any("required format" in e for e in errors)


def test_unknown_tag():
    errors, _ = validate_subject("[OOPS] auth: fix something")
    assert errors, "Expected errors for unknown tag"
    assert any("Unknown tag" in e for e in errors)


def test_missing_scope():
    errors, _ = validate_subject("[FIX] : fix something")
    assert errors, "Expected errors for missing scope"


def test_missing_description():
    errors, _ = validate_subject("[FIX] auth:")
    assert errors, "Expected errors for missing description"


def test_wrong_format_no_colon():
    errors, _ = validate_subject("[FIX] auth fix the bug")
    assert errors, "Expected errors when colon+space separator is absent"


def test_wrong_format_plain_message():
    errors, _ = validate_subject("fixed the login bug")
    assert errors, "Expected errors for plain commit message"


def test_lowercase_tag_fails():
    errors, _ = validate_subject("[fix] auth: fix token expiry")
    assert errors, "Expected errors for lowercase tag"


# ---------------------------------------------------------------------------
# Subject length — hard limit 72 chars (error), soft limit 50 chars (warning)
# ---------------------------------------------------------------------------

def test_subject_over_72_is_error():
    subject = "[IMP] auth: " + "x" * 62   # total > 72 chars
    errors, _ = validate_subject(subject)
    assert errors, "Subject over 72 chars should be a hard error"
    assert any("72" in e for e in errors)


def test_subject_51_to_72_is_warning_not_error():
    subject = "[IMP] auth: " + "x" * 40   # 52 chars total, within 72
    errors, warnings = validate_subject(subject)
    assert errors == [], "Subject between 50-72 chars should not be an error"
    assert warnings, "Subject between 50-72 chars should produce a warning"
    assert any("50" in w for w in warnings)


def test_subject_under_50_no_length_issue():
    subject = "[IMP] auth: add retry logic"   # short, clean
    errors, warnings = validate_subject(subject)
    assert errors == []
    assert not any("char" in w for w in warnings)


# ---------------------------------------------------------------------------
# Imperative mood detection (soft warnings)
# ---------------------------------------------------------------------------

def test_past_tense_warning():
    _, warnings = validate_subject("[IMP] auth: added retry logic")
    assert warnings, "Past-tense description should produce a warning"
    assert any("past tense" in w for w in warnings)


def test_gerund_warning():
    _, warnings = validate_subject("[IMP] auth: adding retry logic")
    assert warnings, "Gerund description should produce a warning"
    assert any("gerund" in w for w in warnings)


def test_imperative_no_mood_warning():
    _, warnings = validate_subject("[IMP] auth: add retry logic")
    mood_warnings = [w for w in warnings if "tense" in w or "gerund" in w]
    assert not mood_warnings, "Imperative verb should not trigger mood warning"
