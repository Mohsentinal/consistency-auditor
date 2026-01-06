from __future__ import annotations

import argparse
from pathlib import Path
from typing import Iterable

from . import __version__
from .io_csv import read_trades_csv
from .match import audit_trades
from .report_csv import write_audit_csv


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="consistency-auditor",
        description="Audit backtest vs live trading consistency and generate simple reports.",
    )
    p.add_argument("--version", action="store_true", help="Print version and exit")

    sub = p.add_subparsers(dest="cmd")

    pa = sub.add_parser("audit", help="Compare backtest vs live CSV trade lists")
    pa.add_argument("--backtest", required=True, help="Path to backtest CSV")
    pa.add_argument("--live", required=True, help="Path to live CSV")
    pa.add_argument("--tolerance", type=int, default=120, help="Match tolerance in seconds (default: 120)")
    pa.add_argument(
        "--price-tolerance",
        type=float,
        default=None,
        help="Optional max abs open-price diff to allow a match",
    )
    pa.add_argument("--out", default="", help="Optional output folder to write matched/unmatched CSVs")
    pa.add_argument("--out-prefix", default="", help="Optional prefix for output CSV filenames (avoid overwrites)")
    pa.add_argument(
        "--fail-on",
        choices=["none", "any", "missing", "extra"],
        default="none",
        help="Return nonzero exit code if audit detects issues (default: none)",
    )

    return p


def _fmt_trade(t) -> str:
    tid = t.trade_id or "-"
    return f"{t.symbol} {t.side.value} open={t.open_time.isoformat()} price={t.open_price:.6f} id={tid}"


def _print_list(title: str, trades: Iterable) -> None:
    trades = list(trades)
    print(f"\n{title} ({len(trades)}):")
    if not trades:
        print("  -")
        return
    for t in trades:
        print("  " + _fmt_trade(t))


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

    if matched:
        print("\nMatched pairs:")
        for m in res.matched:
            bt = _fmt_trade(m.backtest)
            lv = _fmt_trade(m.live)
            print(f"  BT: {bt}")
            print(f"  LV: {lv}")
            print(f"  dt_s={m.open_time_diff_s:.2f} price_diff={m.open_price_diff:+.6f}\n")

    _print_list("Missing in live", res.missing_in_live)
    _print_list("Extra in live", res.extra_in_live)


def _exit_code_for_fail_on(fail_on: str, missing: int, extra: int) -> int:
    if fail_on == "none":
        return 0
    if fail_on == "any":
        return 3 if (missing > 0 or extra > 0) else 0
    if fail_on == "missing":
        return 3 if missing > 0 else 0
    if fail_on == "extra":
        return 3 if extra > 0 else 0
    return 0


def main(argv: list[str] | None = None) -> int:
    p = build_parser()
    args = p.parse_args(argv)

    if args.version:
        print(__version__)
        return 0

    if args.cmd == "audit":
        bt_path = Path(args.backtest)
        lv_path = Path(args.live)

        if not bt_path.exists():
            print(f"ERROR: backtest file not found: {bt_path}")
            return 2
        if not lv_path.exists():
            print(f"ERROR: live file not found: {lv_path}")
            return 2

        bt = read_trades_csv(bt_path, source="backtest")
        lv = read_trades_csv(lv_path, source="live")

        res = audit_trades(
            bt,
            lv,
            time_tolerance_s=args.tolerance,
            price_tolerance=args.price_tolerance,
        )

        _print_audit(res)

        if args.out:
            matched_path, unmatched_path = write_audit_csv(res, args.out, prefix=args.out_prefix or None)
            print(f"\nWrote: {matched_path}")
            print(f"Wrote: {unmatched_path}")

        missing = len(res.missing_in_live)
        extra = len(res.extra_in_live)
        return _exit_code_for_fail_on(args.fail_on, missing, extra)

    p.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())