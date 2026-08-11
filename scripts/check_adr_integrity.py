#!/usr/bin/env python3
"""Fitness function: ADR numbering integrity for Norma.

Checks:
1. Unique ADR numbers in docs/adr/ADR-NNNN-*.md (excluding template/index)
2. Filename number matches H1
3. Every ADR file is listed in ADR-INDEX.md
4. Status is one of Proposed | Accepted | Deprecated | Superseded
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ADR_DIR = ROOT / "docs" / "adr"
INDEX = ADR_DIR / "ADR-INDEX.md"

ALLOWED_STATUS = frozenset({"Proposed", "Accepted", "Deprecated", "Superseded"})
FILE_RE = re.compile(r"^ADR-(\d{4})-[\w-]+\.md$", re.I)
STATUS_RE = re.compile(r"\*\*Статус:\*\*\s*(\w+)", re.I)
H1_RE = re.compile(r"^#\s+ADR-(\d{4})\b", re.M)


def _adr_files() -> list[Path]:
    return sorted(
        p
        for p in ADR_DIR.glob("ADR-*.md")
        if p.name.upper() != "ADR-INDEX.MD" and FILE_RE.match(p.name)
    )


def _parse_adr(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    m_file = FILE_RE.match(path.name)
    assert m_file
    number = m_file.group(1)
    h1 = H1_RE.search(text)
    status_m = STATUS_RE.search(text)
    return {
        "path": path,
        "number": number,
        "h1_number": h1.group(1) if h1 else None,
        "status": status_m.group(1) if status_m else None,
    }


def _index_ids() -> dict[str, str]:
    """Map ADR-NNNN → relative link target from ADR-INDEX.md."""
    text = INDEX.read_text(encoding="utf-8")
    found: dict[str, str] = {}
    for m in re.finditer(r"\[ADR-(\d{4})\]\((ADR-\d{4}-[^)]+\.md)\)", text):
        found[m.group(1)] = m.group(2)
    return found


def main() -> int:
    errors: list[str] = []

    if not ADR_DIR.is_dir():
        print("ADR integrity FAILED: docs/adr/ missing")
        return 1
    if not INDEX.is_file():
        print("ADR integrity FAILED: ADR-INDEX.md missing")
        return 1

    adrs = [_parse_adr(p) for p in _adr_files()]
    by_number: dict[str, list[dict]] = {}
    for adr in adrs:
        by_number.setdefault(adr["number"], []).append(adr)

    for number, group in sorted(by_number.items()):
        if len(group) > 1:
            names = ", ".join(a["path"].name for a in group)
            errors.append(f"Duplicate ADR number {number}: {names}")

    for adr in adrs:
        if adr["h1_number"] and adr["h1_number"] != adr["number"]:
            errors.append(
                f"{adr['path'].name}: H1 says ADR-{adr['h1_number']} "
                f"but filename is ADR-{adr['number']}"
            )
        if adr["status"] is None:
            errors.append(f"{adr['path'].name}: missing **Статус:** line")
        elif adr["status"] not in ALLOWED_STATUS:
            errors.append(
                f"{adr['path'].name}: invalid status {adr['status']!r}; "
                f"allowed {sorted(ALLOWED_STATUS)}"
            )

    index = _index_ids()
    for adr in adrs:
        if adr["number"] not in index:
            errors.append(f"{adr['path'].name}: not listed in ADR-INDEX.md")
        elif index[adr["number"]] != adr["path"].name:
            errors.append(
                f"ADR-{adr['number']}: index links to {index[adr['number']]}, "
                f"file is {adr['path'].name}"
            )

    for number, link in index.items():
        if number not in by_number:
            errors.append(f"ADR-INDEX lists ADR-{number} → {link} but file missing")

    if errors:
        print("ADR integrity FAILED:")
        for e in errors:
            print(f"  - {e}")
        return 1

    print(f"ADR integrity OK: {len(adrs)} ADRs")
    return 0


if __name__ == "__main__":
    sys.exit(main())
