#!/usr/bin/env python3
"""
check_version_bump.py <base_ref> <module1> [module2 ...]

For each module, verifies that the version in __manifest__.py is strictly
greater than the version on origin/<base_ref>. Exits 1 if any module fails.

Odoo versions have the form  19.0.X.Y.Z — only the X.Y.Z part is compared.
"""
import ast
import subprocess
import sys


def parse_module_version(version_str: str) -> tuple:
    """Return the module-specific portion as a comparable int tuple."""
    parts = version_str.strip().split(".")
    if len(parts) < 3:
        raise ValueError(f"version too short: {version_str!r}")
    try:
        return tuple(int(p) for p in parts[2:])
    except ValueError:
        raise ValueError(f"non-numeric version segment in {version_str!r}")


def manifest_version(module: str, git_ref: str | None = None) -> str | None:
    """Extract 'version' from __manifest__.py, optionally from a git ref."""
    path = f"{module}/__manifest__.py"
    if git_ref:
        try:
            content = subprocess.check_output(
                ["git", "show", f"{git_ref}:{path}"],
                stderr=subprocess.DEVNULL,
            ).decode()
        except subprocess.CalledProcessError:
            return None  # module did not exist on base branch
    else:
        try:
            with open(path) as fh:
                content = fh.read()
        except FileNotFoundError:
            return None

    try:
        return ast.literal_eval(content).get("version", "").strip() or None
    except Exception:
        return None


def main() -> None:
    if len(sys.argv) < 3:
        print("Usage: check_version_bump.py <base_ref> <module1> [module2 ...]")
        sys.exit(1)

    base_ref = f"origin/{sys.argv[1]}"
    modules = sys.argv[2:]
    failures = []

    for mod in modules:
        head_ver = manifest_version(mod)
        base_ver = manifest_version(mod, git_ref=base_ref)

        if base_ver is None:
            print(f"  ✓ {mod}: new module — skipping version check")
            continue

        if head_ver is None:
            failures.append(f"  ✗ {mod}: __manifest__.py missing or no 'version' field")
            continue

        try:
            head_t = parse_module_version(head_ver)
            base_t = parse_module_version(base_ver)
        except ValueError as exc:
            failures.append(f"  ✗ {mod}: {exc}")
            continue

        if head_t > base_t:
            print(f"  ✓ {mod}: {base_ver} → {head_ver}")
        else:
            failures.append(
                f"  ✗ {mod}: version NOT bumped  (base: {base_ver}, current: {head_ver})"
            )

    if failures:
        print("\nVersion bump failures:")
        for msg in failures:
            print(msg)
        sys.exit(1)

    print("\nAll version checks passed.")


if __name__ == "__main__":
    main()
