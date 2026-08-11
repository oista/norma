"""Load stone.toml (or any Norma token file)."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib

# Theme-table keys that are identity/labels, never palette lookups
_THEME_LITERAL_KEYS = frozenset({"id", "name"})


def load_tokens(path: Path | str) -> dict[str, Any]:
    p = Path(path)
    with p.open("rb") as f:
        data = tomllib.load(f)
    palette: dict[str, str] = dict(data.get("palette") or {})
    layout: dict[str, str] = dict(data.get("layout") or {})
    semantic_raw: dict[str, str] = dict(data.get("semantic") or {})
    prodata_raw: dict[str, str] = dict(data.get("prodata") or {})

    def resolve(val: str) -> str:
        if val.startswith("#") or val in {"none", "0"} or val.endswith("px"):
            return val
        if val in palette:
            return palette[val]
        if val in layout:
            return layout[val]
        return val

    semantic = {k: resolve(v) for k, v in semantic_raw.items()}
    prodata = {
        k: (v if k in _THEME_LITERAL_KEYS else resolve(v))
        for k, v in prodata_raw.items()
    }
    return {
        "palette": palette,
        "layout": layout,
        "semantic": semantic,
        "prodata": prodata,
        "raw": data,
    }
