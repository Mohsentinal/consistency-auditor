from __future__ import annotations

import csv
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from .models import Side, Trade


def _parse_dt(s: str) -> datetime:
    s = s.strip()
    if not s:
        raise ValueError("empty datetime")

    # unix seconds
    if s.isdigit():
        return datetime.fromtimestamp(int(s), tz=timezone.utc)

    # ISO formats (allow trailing Z)
    s = s.replace("Z", "+00:00")
    dt = datetime.fromisoformat(s)
    return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt


def _parse_side(s: str) -> Side:
    v = s.strip().upper()
    if v in ("BUY", "LONG"):
        return Side.BUY
    if v in ("SELL", "SHORT"):
        return Side.SELL
    raise ValueError(f"invalid side: {s!r}")


def read_trades_csv(path: str | Path, source: str) -> list[Trade]:
    """
    Normalized CSV columns (recommended):
      trade_id,symbol,side,open_time,open_price,close_time,close_price,volume,sl,tp

    Minimal required:
      symbol,side,open_time,open_price
    """
    p = Path(path)
    trades: list[Trade] = []

    with p.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames is None:
            raise ValueError("CSV has no header row")

        for row in reader:
            symbol = (row.get("symbol") or "").strip()
            side = _parse_side(row.get("side") or "")
            open_time = _parse_dt(row.get("open_time") or "")
            open_price = float(row.get("open_price") or "")

            def fopt(key: str) -> Optional[float]:
                v = (row.get(key) or "").strip()
                return float(v) if v else None

            def dtopt(key: str) -> Optional[datetime]:
                v = (row.get(key) or "").strip()
                return _parse_dt(v) if v else None

            trades.append(
                Trade(
                    source=source,
                    symbol=symbol,
                    side=side,
                    open_time=open_time,
                    open_price=open_price,
                    close_time=dtopt("close_time"),
                    close_price=fopt("close_price"),
                    volume=fopt("volume"),
                    sl=fopt("sl"),
                    tp=fopt("tp"),
                    trade_id=(row.get("trade_id") or "").strip() or None,
                )
            )

    return trades