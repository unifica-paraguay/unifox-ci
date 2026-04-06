#!/usr/bin/env python3
"""Shared helper: call the Claude API and print the response to stdout.

Usage:
    echo "your prompt" | python claude_api.py
    python claude_api.py "your prompt"

The script builds a system prompt from:
  1. CLAUDE.md in the calling repo's cwd (if present)
  2. coding_guidelines.rst from unifox-ci/context/
  3. git_guidelines.rst from unifox-ci/context/

Environment variables:
    ANTHROPIC_API_KEY   required
    CLAUDE_MODEL        optional, defaults to claude-sonnet-4-6
"""

import os
import sys
import time
from pathlib import Path

try:
    import requests
except ImportError:
    print("ERROR: 'requests' is not installed. Run: pip install requests", file=sys.stderr)
    sys.exit(1)

MODEL = os.environ.get("CLAUDE_MODEL", "claude-sonnet-4-6")
API_URL = "https://api.anthropic.com/v1/messages"
MAX_RETRIES = 3
TIMEOUT = 60

# ---------------------------------------------------------------------------
# Load system prompt
# ---------------------------------------------------------------------------


def _load_system_prompt() -> str:
    # scripts/ lives one level below the unifox-ci repo root
    unifox_root = Path(__file__).resolve().parent.parent
    context_dir = unifox_root / "context"

    parts = [
        "You are a code reviewer and automation assistant.\n"
    ]

    # 1. Repo-specific conventions — CLAUDE.md from the calling workspace (cwd)
    caller_claude = Path.cwd() / "CLAUDE.md"
    if caller_claude.exists():
        parts.append(
            "=== Repository conventions (CLAUDE.md) ===\n\n"
            + caller_claude.read_text(encoding="utf-8")
        )

    # 2. Odoo coding guidelines (Python, XML, JS, SCSS)
    coding = context_dir / "coding_guidelines.rst"
    if coding.exists():
        parts.append(
            "\n=== Odoo coding guidelines ===\n\n"
            + coding.read_text(encoding="utf-8")
        )

    # 3. Odoo git / commit guidelines
    git_gl = context_dir / "git_guidelines.rst"
    if git_gl.exists():
        parts.append(
            "\n=== Odoo git guidelines ===\n\n"
            + git_gl.read_text(encoding="utf-8")
        )

    # 4. Documentation guidelines are available in context/ but not loaded by
    #    default to keep context size manageable. Load them conditionally when
    #    the UNIFOX_LOAD_DOC_GUIDELINES=1 env var is set.
    if os.environ.get("UNIFOX_LOAD_DOC_GUIDELINES") == "1":
        for fname in ("content_guidelines.rst", "rst_guidelines.rst"):
            path = context_dir / fname
            if path.exists():
                parts.append(
                    f"\n=== Odoo {fname} ===\n\n"
                    + path.read_text(encoding="utf-8")
                )

    return "\n\n".join(parts)


# ---------------------------------------------------------------------------
# API call with retry / backoff
# ---------------------------------------------------------------------------

def call_claude(prompt: str, max_tokens: int = 4096) -> str:
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        print("ERROR: ANTHROPIC_API_KEY environment variable is not set.", file=sys.stderr)
        sys.exit(1)

    system_prompt = _load_system_prompt()

    headers = {
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }
    payload = {
        "model": MODEL,
        "max_tokens": max_tokens,
        "system": system_prompt,
        "messages": [{"role": "user", "content": prompt}],
    }

    last_error: Exception | None = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = requests.post(API_URL, headers=headers, json=payload, timeout=TIMEOUT)
            if resp.status_code == 200:
                data = resp.json()
                for block in data.get("content", []):
                    if block.get("type") == "text":
                        return block["text"]
                print("ERROR: No text block in Claude response.", file=sys.stderr)
                sys.exit(1)

            if resp.status_code in (429, 500, 502, 503, 529):
                wait = 2 ** attempt
                print(
                    f"Attempt {attempt}/{MAX_RETRIES}: HTTP {resp.status_code} — "
                    f"retrying in {wait}s",
                    file=sys.stderr,
                )
                time.sleep(wait)
                last_error = RuntimeError(f"HTTP {resp.status_code}: {resp.text[:200]}")
                continue

            print(f"ERROR: Claude API returned {resp.status_code}: {resp.text[:500]}", file=sys.stderr)
            sys.exit(1)

        except requests.exceptions.Timeout:
            wait = 2 ** attempt
            print(
                f"Attempt {attempt}/{MAX_RETRIES}: request timed out — retrying in {wait}s",
                file=sys.stderr,
            )
            time.sleep(wait)
            last_error = TimeoutError("Request timed out")

        except requests.exceptions.RequestException as exc:
            print(f"ERROR: Network error — {exc}", file=sys.stderr)
            sys.exit(1)

    print(f"ERROR: All {MAX_RETRIES} attempts failed. Last error: {last_error}", file=sys.stderr)
    sys.exit(1)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    if len(sys.argv) > 1:
        prompt = " ".join(sys.argv[1:])
    elif not sys.stdin.isatty():
        prompt = sys.stdin.read().strip()
    else:
        print("Usage: echo 'prompt' | python claude_api.py", file=sys.stderr)
        print("   or: python claude_api.py 'prompt text'", file=sys.stderr)
        sys.exit(1)

    if not prompt:
        print("ERROR: Empty prompt.", file=sys.stderr)
        sys.exit(1)

    result = call_claude(prompt)
    print(result)
