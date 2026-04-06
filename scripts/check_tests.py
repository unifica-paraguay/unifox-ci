#!/usr/bin/env python3
"""
check_tests.py <module1> [module2 ...]

Verifies that each module has a tests/ directory, tests/__init__.py,
and at least one test_*.py file. Exits 1 if any module fails.
"""
import glob
import os
import sys


def check(module: str) -> tuple[bool, str]:
    tests_dir = f"{module}/tests"

    if not os.path.isdir(tests_dir):
        return False, "tests/ directory missing"

    if not os.path.isfile(f"{tests_dir}/__init__.py"):
        return False, "tests/__init__.py missing"

    test_files = glob.glob(f"{tests_dir}/test_*.py")
    if not test_files:
        return False, "no test_*.py files found in tests/"

    names = ", ".join(sorted(os.path.basename(f) for f in test_files))
    return True, f"{len(test_files)} test file(s): {names}"


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: check_tests.py <module1> [module2 ...]")
        sys.exit(1)

    failures: list[str] = []

    for mod in sys.argv[1:]:
        ok, msg = check(mod)
        symbol = "✓" if ok else "✗"
        print(f"  {symbol} {mod}: {msg}")
        if not ok:
            failures.append(mod)

    if failures:
        sys.exit(1)


if __name__ == "__main__":
    main()
