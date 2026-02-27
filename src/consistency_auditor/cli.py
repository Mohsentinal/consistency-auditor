from __future__ import annotations

import argparse
from pathlib import Path
from typing import Iterable

from . import __version__
from .io_csv import read_trades_csv
from .match import AuditResult, SlippageStats, audit_trades
from .replay import ReplayReport, replay_from_file
from .report_csv import write_audit_csv


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="consistency-auditor",
        description="Audit backtest vs live trading consistency and generate reports.",
    )
    p.add_argument("--version", action="store_true", help="Print version and exit")

    sub = p.add_subparsers(dest="cmd")

    # ---- audit subcommand ----
    pa = sub.add_parser("audit", help="Compare backtest vs live CSV trade lists")
    pa.add_argument("--backtest", required=True, help="Path to backtest CSV")
    pa.add_argument("--live", required=True, help="Path to live CSV")
    pa.add_argument("--tolerance", type=int, default=120, help="Match tolerance in seconds (default: 120)")
    pa.add_argument(
        "--price-tolerance", type=float, default=None,
        help="Optional max abs open-price diff to allow a match",
    )
    pa.add_argument("--out", default="", help="Optional output folder to write matched/unmatched CSVs")
    pa.add_argument("--out-prefix", default="", help="Optional prefix for output CSV filenames")
    pa.add_argument(
        "--fail-on",
        choices=["none", "any", "missing", "extra"],
        default="none",
        help="Exit with code 3 if mismatches exist (any/missing/extra). Default: none",
    )

    # ---- replay subcommand ----
    pr = sub.add_parser("replay", help="Audit a ConsistencyRecorder event log (JSONL)")
    pr.add_argument("--events", required=True, help="Path to events.jsonl produced by ConsistencyRecorder")
    pr.add_argument(
        "--fail-on",
        choices=["none", "any", "rejected", "unexecuted"],
        default="none",
        help="Exit with code 3 on anomalies (any/rejected/unexecuted). Default: none",
    )

    return p


# ---------------------------------------------------------------------------
# Formatting helpers
# ---------------------------------------------------------------------------

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


def _fmt_stats(label: str, s: SlippageStats) -> None:
    print(
        f"  {label}: mean={s.mean:.4f} ±{s.std:.4f} "
        f"[min={s.min:.4f}  p50={s.p50:.4f}  p95={s.p95:.4f}  max={s.max:.4f}]  n={s.count}"
    )


def _print_audit(res: AuditResult) -> None:
    n_matched = len(res.matched)
    n_missing = len(res.missing_in_live)
    n_extra = len(res.extra_in_live)

    print(f"matched={n_matched}  missing_in_live={n_missing}  extra_in_live={n_extra}")

    if n_matched:
        print("\n── Entry statistics ──────────────────────────────────────────")
        _fmt_stats("open_time_diff_s  ", res.stats.open_time_diff_s)
        _fmt_stats("abs_open_price_diff", res.stats.abs_open_price_diff)

        if res.stats.close_time_diff_s is not None:
            print("\n── Exit statistics ───────────────────────────────────────────")
            _fmt_stats("close_time_diff_s  ", res.stats.close_time_diff_s)
        if res.stats.abs_close_price_diff is not None:
            _fmt_stats("abs_close_price_diff", res.stats.abs_close_price_diff)

        if res.stats.pnl_diff is not None:
            print("\n── P&L drift statistics ──────────────────────────────────────")
            _fmt_stats("pnl_diff           ", res.stats.pnl_diff)
            total_bt = sum(m.bt_pnl for m in res.matched if m.bt_pnl is not None)
            total_lv = sum(m.lv_pnl for m in res.matched if m.lv_pnl is not None)
            print(f"  total_bt_pnl={total_bt:+.6f}  total_lv_pnl={total_lv:+.6f}  "
                  f"total_pnl_drift={total_lv - total_bt:+.6f}")

        print("\n── Matched pairs ─────────────────────────────────────────────")
        for m in res.matched:
            print(f"  BT: {_fmt_trade(m.backtest)}")
            print(f"  LV: {_fmt_trade(m.live)}")
            line = f"  entry: dt_s={m.open_time_diff_s:.2f}  price_diff={m.open_price_diff:+.6f}"
            if m.close_time_diff_s is not None:
                line += f"  exit: dt_s={m.close_time_diff_s:.2f}"
            if m.close_price_diff is not None:
                line += f"  close_price_diff={m.close_price_diff:+.6f}"
            if m.pnl_diff is not None:
                line += f"  pnl_diff={m.pnl_diff:+.6f}"
            print(line + "\n")

    _print_list("Missing in live", res.missing_in_live)
    _print_list("Extra in live", res.extra_in_live)


def _print_replay(rep: ReplayReport) -> None:
    print("── Run info ──────────────────────────────────────────────────")
    if rep.run_info:
        ri = rep.run_info
        print(f"  run_id={ri.run_id}  version={ri.app_version}  config={ri.config_fingerprint}")
        print(f"  started={ri.timestamp}")
    else:
        print("  (no RUN_START event found)")

    print("\n── Decision summary ──────────────────────────────────────────")
    print(f"  total_decisions={rep.total_decisions}  actionable={rep.actionable_decisions}")
    print(f"  filled={rep.filled_count}  rejected={rep.rejected_count}  "
          f"unexecuted={rep.unexecuted_count}")
    if rep.actionable_decisions:
        print(f"  fill_rate={rep.fill_rate:.1%}")

    lats = rep.latencies_ms
    if lats:
        print("\n── Decision-to-fill latency (ms) ─────────────────────────────")
        s = SlippageStats.from_values(lats)
        _fmt_stats("latency_ms", s)

    if rep.rejected_count:
        print(f"\n── Rejections ({rep.rejected_count}) ──────────────────────────────────────")
        for c in rep.chains:
            if c.was_rejected:
                intent = c.decision.get("intent", "?") if c.decision else "?"
                sym = (c.decision or {}).get("context", {}).get("symbol", "?")
                reason = c.rejections[0].get("comment", "-")
                print(f"  signal_id={c.signal_id[:12]}  sym={sym}  intent={intent}  reason={reason}")

    if rep.unexecuted_count:
        print(f"\n── Unexecuted actionable decisions ({rep.unexecuted_count}) ────────────────")
        for c in rep.chains:
            if c.decision and c.decision.get("intent") != "NONE" and c.order_sent is None:
                sym = c.decision.get("context", {}).get("symbol", "?")
                intent = c.decision.get("intent", "?")
                print(f"  signal_id={c.signal_id[:12]}  sym={sym}  intent={intent}")

    if rep.orphaned_events:
        print(f"\n  orphaned_events={len(rep.orphaned_events)} (events with no matching DECISION)")


# ---------------------------------------------------------------------------
# Fail-on helpers
# ---------------------------------------------------------------------------

def _audit_should_fail(args, res: AuditResult) -> bool:
    if args.fail_on == "none":
        return False
    if args.fail_on == "any":
        return bool(res.missing_in_live or res.extra_in_live)
    if args.fail_on == "missing":
        return bool(res.missing_in_live)
    if args.fail_on == "extra":
        return bool(res.extra_in_live)
    return False


def _replay_should_fail(args, rep: ReplayReport) -> bool:
    if args.fail_on == "none":
        return False
    if args.fail_on == "any":
        return rep.rejected_count > 0 or rep.unexecuted_count > 0
    if args.fail_on == "rejected":
        return rep.rejected_count > 0
    if args.fail_on == "unexecuted":
        return rep.unexecuted_count > 0
    return False


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    p = build_parser()
    args = p.parse_args(argv)

    if args.version:
        print(__version__)
        return 0

    # ---- audit ----
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

        res = audit_trades(bt, lv, time_tolerance_s=args.tolerance, price_tolerance=args.price_tolerance)
        _print_audit(res)

        if args.out:
            matched_path, unmatched_path = write_audit_csv(res, args.out, prefix=args.out_prefix or None)
            print(f"\nWrote: {matched_path}")
            print(f"Wrote: {unmatched_path}")

        return 3 if _audit_should_fail(args, res) else 0

    # ---- replay ----
    if args.cmd == "replay":
        ev_path = Path(args.events)
        if not ev_path.exists():
            print(f"ERROR: events file not found: {ev_path}")
            return 2

        rep = replay_from_file(ev_path)
        _print_replay(rep)

        return 3 if _replay_should_fail(args, rep) else 0

    p.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
