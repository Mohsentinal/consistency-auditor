from __future__ import annotations

import csv
from datetime import datetime, timezone
from pathlib import Path

from .match import AuditResult


def _default_prefix() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")


def write_audit_csv(
    res: AuditResult,
    out_dir: str | Path,
    prefix: str | None = None,
) -> tuple[Path, Path]:
    """
    Write:
      - matched_<prefix>.csv : one row per matched pair (entry + exit + P&L)
      - unmatched_<prefix>.csv: missing_in_live + extra_in_live
    Returns (matched_path, unmatched_path).
    """
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    px = (prefix or "").strip() or _default_prefix()

    matched_path = out / f"matched_{px}.csv"
    unmatched_path = out / f"unmatched_{px}.csv"

    with matched_path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(
            f,
            fieldnames=[
                "symbol", "side",
                "bt_trade_id", "lv_trade_id",
                # Entry
                "bt_open_time", "lv_open_time", "open_time_diff_s",
                "bt_open_price", "lv_open_price", "open_price_diff",
                # Exit
                "bt_close_time", "lv_close_time", "close_time_diff_s",
                "bt_close_price", "lv_close_price", "close_price_diff",
                # P&L
                "bt_pnl", "lv_pnl", "pnl_diff",
            ],
        )
        w.writeheader()
        for m in res.matched:
            w.writerow({
                "symbol": m.backtest.symbol,
                "side": m.backtest.side.value,
                "bt_trade_id": m.backtest.trade_id or "",
                "lv_trade_id": m.live.trade_id or "",
                # Entry
                "bt_open_time": m.backtest.open_time.isoformat(),
                "lv_open_time": m.live.open_time.isoformat(),
                "open_time_diff_s": f"{m.open_time_diff_s:.6f}",
                "bt_open_price": f"{m.backtest.open_price:.6f}",
                "lv_open_price": f"{m.live.open_price:.6f}",
                "open_price_diff": f"{m.open_price_diff:+.6f}",
                # Exit
                "bt_close_time": m.backtest.close_time.isoformat() if m.backtest.close_time else "",
                "lv_close_time": m.live.close_time.isoformat() if m.live.close_time else "",
                "close_time_diff_s": f"{m.close_time_diff_s:.6f}" if m.close_time_diff_s is not None else "",
                "bt_close_price": f"{m.backtest.close_price:.6f}" if m.backtest.close_price is not None else "",
                "lv_close_price": f"{m.live.close_price:.6f}" if m.live.close_price is not None else "",
                "close_price_diff": f"{m.close_price_diff:+.6f}" if m.close_price_diff is not None else "",
                # P&L
                "bt_pnl": f"{m.bt_pnl:+.6f}" if m.bt_pnl is not None else "",
                "lv_pnl": f"{m.lv_pnl:+.6f}" if m.lv_pnl is not None else "",
                "pnl_diff": f"{m.pnl_diff:+.6f}" if m.pnl_diff is not None else "",
            })

    with unmatched_path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(
            f,
            fieldnames=[
                "bucket", "symbol", "side", "trade_id",
                "open_time", "open_price",
                "close_time", "close_price",
                "source",
            ],
        )
        w.writeheader()
        for t in res.missing_in_live:
            w.writerow({
                "bucket": "missing_in_live",
                "symbol": t.symbol, "side": t.side.value,
                "trade_id": t.trade_id or "",
                "open_time": t.open_time.isoformat(), "open_price": f"{t.open_price:.6f}",
                "close_time": t.close_time.isoformat() if t.close_time else "",
                "close_price": f"{t.close_price:.6f}" if t.close_price is not None else "",
                "source": t.source,
            })
        for t in res.extra_in_live:
            w.writerow({
                "bucket": "extra_in_live",
                "symbol": t.symbol, "side": t.side.value,
                "trade_id": t.trade_id or "",
                "open_time": t.open_time.isoformat(), "open_price": f"{t.open_price:.6f}",
                "close_time": t.close_time.isoformat() if t.close_time else "",
                "close_price": f"{t.close_price:.6f}" if t.close_price is not None else "",
                "source": t.source,
            })

    return matched_path, unmatched_path
