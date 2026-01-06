from __future__ import annotations

import argparse

from . import __version__


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="consistency-auditor",
        description="Audit backtest vs live trading consistency and generate simple reports.",
    )
    p.add_argument("--version", action="store_true", help="Print version and exit")
    return p


def main(argv: list[str] | None = None) -> int:
    p = build_parser()
    args = p.parse_args(argv)

    if args.version:
        print(__version__)
        return 0

    p.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())