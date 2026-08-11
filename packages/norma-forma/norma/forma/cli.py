"""CLI: norma-forma emit --target … --tokens …"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from norma.forma.emitters import emit_entan_css, emit_pw_theme, emit_tailwind
from norma.forma.load import load_tokens

TARGETS = {
    "entan-css": emit_entan_css,
    "pw-theme": emit_pw_theme,
    "tailwind": emit_tailwind,
}


def _default_tokens() -> Path:
    # packages/norma-forma/norma/forma/cli.py → repo tokens/
    here = Path(__file__).resolve()
    candidate = here.parents[4] / "tokens" / "stone.toml"
    if candidate.is_file():
        return candidate
    return Path("tokens/stone.toml")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="norma-forma")
    sub = parser.add_subparsers(dest="cmd", required=True)
    emit = sub.add_parser("emit", help="Emit design artifact")
    emit.add_argument(
        "--target",
        required=True,
        choices=sorted(TARGETS),
        help="Artifact kind",
    )
    emit.add_argument(
        "--tokens",
        type=Path,
        default=None,
        help="Path to stone.toml (default: repo tokens/stone.toml)",
    )
    args = parser.parse_args(argv)
    if args.cmd == "emit":
        path = args.tokens or _default_tokens()
        tokens = load_tokens(path)
        text = TARGETS[args.target](tokens)
        sys.stdout.write(text)
        if not text.endswith("\n"):
            sys.stdout.write("\n")
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
