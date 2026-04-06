#!/usr/bin/env python3
"""
check_manifest.py <module1> [module2 ...]

Validates Odoo module structure and manifest fields for each module.
Exits 1 if any error is found.

Checks performed:
  - __init__.py exists at module root
  - __manifest__.py exists and is parseable
  - Required fields: name, version, depends, license
  - Unifica-specific fields: author, website (with expected values)
  - installable == True
  - models/ and controllers/ have __init__.py if present
  - security/ir.model.access.csv has correct header if present
  - All XML files in views/ and data/ are well-formed
"""
import ast
import os
import sys
import xml.etree.ElementTree as ET

REQUIRED_FIELDS = ["name", "version", "depends", "license"]

UNIFICA_REQUIRED = {
    "author": "Unifica Paraguay",
    "website": "https://www.unificadesign.com.py",
}

CSV_HEADER = "id,name,model_id:id,group_id:id,perm_read,perm_write,perm_create,perm_unlink"


def check_module(module: str) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []

    if not os.path.isfile(f"{module}/__init__.py"):
        errors.append(f"  {module}/__init__.py missing")

    manifest_path = f"{module}/__manifest__.py"
    if not os.path.isfile(manifest_path):
        errors.append(f"  {manifest_path} missing")
        return errors, warnings

    try:
        with open(manifest_path) as fh:
            manifest = ast.literal_eval(fh.read())
    except Exception as exc:
        errors.append(f"  {manifest_path}: parse error — {exc}")
        return errors, warnings

    for field in REQUIRED_FIELDS:
        if field not in manifest:
            errors.append(f"  {manifest_path}: missing required field '{field}'")

    for field, expected in UNIFICA_REQUIRED.items():
        val = manifest.get(field)
        if val is None:
            errors.append(f"  {manifest_path}: missing Unifica field '{field}' (expected '{expected}')")
        elif val != expected:
            errors.append(f"  {manifest_path}: '{field}' = {val!r}, expected {expected!r}")

    if manifest.get("installable") is not True:
        errors.append(
            f"  {manifest_path}: 'installable' must be True, got {manifest.get('installable')!r}"
        )

    for subdir in ("models", "controllers"):
        path = f"{module}/{subdir}"
        if os.path.isdir(path) and not os.path.isfile(f"{path}/__init__.py"):
            errors.append(f"  {path}/ exists but missing __init__.py")

    csv_path = f"{module}/security/ir.model.access.csv"
    if os.path.isfile(csv_path):
        with open(csv_path) as fh:
            header = fh.readline().strip()
        if header != CSV_HEADER:
            errors.append(
                f"  {csv_path}: incorrect CSV header\n"
                f"    got:      {header}\n"
                f"    expected: {CSV_HEADER}"
            )

    for xml_root in (f"{module}/views", f"{module}/data"):
        if not os.path.isdir(xml_root):
            continue
        for dirpath, _, filenames in os.walk(xml_root):
            for fname in filenames:
                if not fname.endswith(".xml"):
                    continue
                xml_path = os.path.join(dirpath, fname)
                try:
                    ET.parse(xml_path)
                except ET.ParseError as exc:
                    errors.append(f"  {xml_path}: XML parse error — {exc}")

    return errors, warnings


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: check_manifest.py <module1> [module2 ...]")
        sys.exit(1)

    all_errors: list[str] = []

    for mod in sys.argv[1:]:
        errors, warnings = check_module(mod)
        for w in warnings:
            print(f"  ⚠ {w}")
        if errors:
            print(f"  ✗ {mod}: {len(errors)} error(s)")
            for e in errors:
                print(e)
            all_errors.extend(errors)
        else:
            print(f"  ✓ {mod}: OK")

    if all_errors:
        sys.exit(1)


if __name__ == "__main__":
    main()
