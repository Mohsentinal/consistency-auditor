from __future__ import annotations

import csv
from datetime import datetime
from pathlib import Path

from .match import AuditResult


def _default_prefix() -> str:
    return datetime.utcnow().strftime("%Y%m%d_%H%M%S")


def write_audit_csv(
    res: AuditResult,
    out_dir: str | Path,
    prefix: str | None = None,
) -> tuple[Path, Path]:
    """
    Write:
      - matched_<prefix>.csv: one row per matched pair
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
                "symbol",
                "side",
                "bt_trade_id",
                "lv_trade_id",
                "bt_open_time",
                "lv_open_time",
                "open_time_diff_s",
                "bt_open_price",
                "lv_open_price",
                "open_price_diff",
            ],
        )
        w.writeheader()
        for m in res.matched:
            w.writerow(
                {
                    "symbol": m.backtest.symbol,
                    "side": m.backtest.side.value,
                    "bt_trade_id": m.backtest.trade_id or "",
                    "lv_trade_id": m.live.trade_id or "",
                    "bt_open_time": m.backtest.open_time.isoformat(),
                    "lv_open_time": m.live.open_time.isoformat(),
                    "open_time_diff_s": f"{m.open_time_diff_s:.6f}",
                    "bt_open_price": f"{m.backtest.open_price:.6f}",
                    "lv_open_price": f"{m.live.open_price:.6f}",
                    "open_price_diff": f"{m.open_price_diff:+.6f}",
                }
            )

    with unmatched_path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(
            f,
            fieldnames=[
                "bucket",
                "symbol",
                "side",
                "trade_id",
                "open_time",
                "open_price",
                "source",
            ],
        )
        w.writeheader()

        for t in res.missing_in_live:
            w.writerow(
                {
                    "bucket": "missing_in_live",
                    "symbol": t.symbol,
                    "side": t.side.value,
                    "trade_id": t.trade_id or "",
                    "open_time": t.open_time.isoformat(),
                    "open_price": f"{t.open_price:.6f}",
                    "source": t.source,
                }
            )

        for t in res.extra_in_live:
            w.writerow(
                {
                    "bucket": "extra_in_live",
                    "symbol": t.symbol,
                    "side": t.side.value,
                    "trade_id": t.trade_id or "",
                    "open_time": t.open_time.isoformat(),
                    "open_price": f"{t.open_price:.6f}",
                    "source": t.source,
                }
            )

    return matched_path, unmatched_path