#!/usr/bin/env python3
"""Fitness function: seam-registry.md rows are complete and well-formed.

Does not resolve sibling-repo paths (those live outside Norma). Checks:
1. Registry file exists
2. Markdown table has required columns
3. Each data row has non-empty required cells
4. Proposed rows are allowed without a concrete gate path
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "docs" / "seam-registry.md"

REQUIRED_HEADERS = (
    "id",
    "producer",
    "consumer(s)",
    "artifact",
    "schema home",
    "versioning",
    "gate / status",
)


def _split_row(line: str) -> list[str]:
    raw = line.strip()
    if raw.startswith("|"):
        raw = raw[1:]
    if raw.endswith("|"):
        raw = raw[:-1]
    return [c.strip() for c in raw.split("|")]


def main() -> int:
    errors: list[str] = []

    if not REGISTRY.is_file():
        print("Seam registry FAILED: docs/seam-registry.md missing")
        return 1

    lines = REGISTRY.read_text(encoding="utf-8").splitlines()
    table_lines = [ln for ln in lines if ln.strip().startswith("|")]
    if len(table_lines) < 3:
        print("Seam registry FAILED: expected header + separator + at least one row")
        return 1

    headers = [h.lower() for h in _split_row(table_lines[0])]
    for req in REQUIRED_HEADERS:
        if req not in headers:
            errors.append(f"missing column {req!r} in header")

    if errors:
        print("Seam registry FAILED:")
        for e in errors:
            print(f"  - {e}")
        return 1

    idx = {name: headers.index(name) for name in REQUIRED_HEADERS}
    data_rows = 0
    for line in table_lines[2:]:
        cells = _split_row(line)
        # skip separator-like rows
        if all(re.fullmatch(r":?-+:?", c or "") for c in cells):
            continue
        if len(cells) < len(headers):
            errors.append(f"short row: {line.strip()}")
            continue
        data_rows += 1
        seam_id = cells[idx["id"]]
        for col in REQUIRED_HEADERS:
            val = cells[idx[col]]
            if not val:
                errors.append(f"seam {seam_id!r}: empty {col}")
        # id should be backtick-wrapped slug or plain slug
        id_raw = seam_id.strip("`")
        if not re.fullmatch(r"[a-z][a-z0-9_-]*", id_raw):
            errors.append(f"invalid seam id {seam_id!r}")

    if data_rows == 0:
        errors.append("no data rows in seam registry table")

    if errors:
        print("Seam registry FAILED:")
        for e in errors:
            print(f"  - {e}")
        return 1

    print(f"Seam registry OK: {data_rows} seams")
    return 0


if __name__ == "__main__":
    sys.exit(main())
