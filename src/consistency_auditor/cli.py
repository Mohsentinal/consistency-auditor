from __future__ import annotations

import argparse

from . import __version__
from .io_csv import read_trades_csv
from .match import audit_trades


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="consistency-auditor",
        description="Audit backtest vs live trading consistency and generate simple reports.",
    )
    p.add_argument("--version", action="store_true", help="Print version and exit")

    sub = p.add_subparsers(dest="cmd")

    a = sub.add_parser("audit", help="Audit backtest vs live trades (CSV inputs)")
    a.add_argument("--backtest", required=True, help="Path to backtest CSV")
    a.add_argument("--live", required=True, help="Path to live CSV")
    a.add_argument("--tolerance", type=int, default=120, help="Open-time tolerance in seconds")

    return p


def _print_audit(res) -> None:
    matched = len(res.matched)
    missing = len(res.missing_in_live)
    extra = len(res.extra_in_live)

    if matched:
        mean_time = sum(m.open_time_diff_s for m in res.matched) / matched
        mean_abs_price = sum(abs(m.open_price_diff) for m in res.matched) / matched
    else:
        mean_time = 0.0
        mean_abs_price = 0.0

    print(f"matched={matched} missing_in_live={missing} extra_in_live={extra}")
    print(f"mean_open_time_diff_s={mean_time:.2f} mean_abs_open_price_diff={mean_abs_price:.6f}")


def main(argv: list[str] | None = None) -> int:
    p = build_parser()
    args = p.parse_args(argv)

    if args.version:
        print(__version__)
        return 0

    if args.cmd == "audit":
        bt = read_trades_csv(args.backtest, source="backtest")
        lv = read_trades_csv(args.live, source="live")
        res = audit_trades(bt, lv, time_tolerance_s=args.tolerance)
        _print_audit(res)
        return 0

    p.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())