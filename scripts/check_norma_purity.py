#!/usr/bin/env python3
"""Fitness function: Norma packages must not know about products.

Invariant (ADR-0001): Norma builds and tests if no product repo exists.

Checks (on packages/**/*.py):
1. Product brand names as identifiers in code (comments/docstrings ignored).
2. Product tool-id prefixes inside string literals (kg_ / ldm_ / lineage_).
"""

from __future__ import annotations

import io
import re
import sys
import tokenize
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACKAGES = ROOT / "packages"

BRAND_RES: list[tuple[str, re.Pattern[str]]] = [
    ("ENTAN", re.compile(r"\bENTAN(?:_[A-Z0-9]+)?\b")),
    ("PRODATA", re.compile(r"\bPRODATA(?:_[A-Z0-9]+)?\b")),
    ("Clavis", re.compile(r"\bClavis\b", re.I)),
    ("Cavis", re.compile(r"\bCavis\b", re.I)),
    ("MOEX", re.compile(r"\bMOEX\b")),
    ("Groma", re.compile(r"\bGroma\b")),
]

TOOL_PREFIX_RE = re.compile(r"\b(?:kg|ldm|lineage)_[a-z0-9_]+\b")


def _iter_tokens(path: Path) -> list[tokenize.TokenInfo]:
    src = path.read_bytes()
    return list(tokenize.tokenize(io.BytesIO(src).readline))


def _code_without_strings_comments(tokens: list[tokenize.TokenInfo]) -> str:
    """Reconstruct source with comments and string literals blanked."""
    if not tokens:
        return ""
    parts: list[str] = []
    for tok in tokens:
        if tok.type in (tokenize.COMMENT, tokenize.STRING, tokenize.NL, tokenize.NEWLINE):
            # keep newlines for line numbering alignment roughly; blank content
            if tok.type in (tokenize.NL, tokenize.NEWLINE):
                parts.append("\n")
            else:
                parts.append(" " * len(tok.string))
        elif tok.type == tokenize.ENCODING:
            continue
        else:
            parts.append(tok.string)
    return "".join(parts)


def _string_literal_values(tokens: list[tokenize.TokenInfo]) -> list[tuple[int, str]]:
    out: list[tuple[int, str]] = []
    for tok in tokens:
        if tok.type != tokenize.STRING:
            continue
        try:
            value = tokenize.untokenize([tok]).strip()
            # evaluate simple literals safely via literal_eval alternative: strip quotes
            if value.startswith(("'", '"')):
                # use ast? keep simple
                import ast

                value = ast.literal_eval(value)
            elif value.startswith(("f'", 'f"', "r'", 'r"', "rf", "fr")):
                # f-strings / raw — scan the raw token text for tool prefixes
                value = tok.string
            if isinstance(value, str):
                out.append((tok.start[0], value))
        except Exception:
            out.append((tok.start[0], tok.string))
    return out


def main() -> int:
    if not PACKAGES.is_dir():
        print("Norma purity FAILED: packages/ missing")
        return 1

    errors: list[str] = []
    py_files = sorted(
        p
        for p in PACKAGES.rglob("*.py")
        if "egg-info" not in p.parts and "__pycache__" not in p.parts
    )

    for path in py_files:
        rel = path.relative_to(ROOT).as_posix()
        try:
            tokens = _iter_tokens(path)
        except tokenize.TokenError as exc:
            errors.append(f"{rel}: tokenize error: {exc}")
            continue

        code = _code_without_strings_comments(tokens)
        for label, pattern in BRAND_RES:
            for m in pattern.finditer(code):
                # approximate line via counting newlines in blanked code
                line_no = code.count("\n", 0, m.start()) + 1
                errors.append(f"{rel}:{line_no}: product leak ({label}): {m.group(0)!r}")

        for line_no, value in _string_literal_values(tokens):
            for m in TOOL_PREFIX_RE.finditer(value):
                errors.append(
                    f"{rel}:{line_no}: product tool id in string: {m.group(0)!r}"
                )

    if errors:
        print("Norma purity FAILED:")
        for e in errors:
            print(f"  - {e}")
        return 1

    print(f"Norma purity OK: scanned {len(py_files)} Python files under packages/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
