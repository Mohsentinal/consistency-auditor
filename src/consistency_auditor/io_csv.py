from __future__ import annotations

import csv
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from .models import Side, Trade


def _parse_dt(s: str) -> datetime:
    s = str(s).strip()
    if not s:
        raise ValueError("empty datetime")

    # unix seconds
    if s.isdigit():
        return datetime.fromtimestamp(int(s), tz=timezone.utc)

    # ISO formats (allow trailing Z)
    s_iso = s.replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(s_iso)
        return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt
    except ValueError:
        pass

    # MT5 common: YYYY.MM.DD HH:MM:SS
    for fmt in ("%Y.%m.%d %H:%M:%S", "%Y-%m-%d %H:%M:%S"):
        try:
            dt = datetime.strptime(s, fmt)
            return dt.replace(tzinfo=timezone.utc)
        except ValueError:
            continue

    raise ValueError(f"invalid datetime: {s!r}")


def _parse_side(s: str) -> Side:
    v = str(s).strip().lower()
    if not v:
        raise ValueError("empty side/type")

    # text
    if v in ("buy", "long"):
        return Side.BUY
    if v in ("sell", "short"):
        return Side.SELL

    # numeric MT5-style:
    # 0 BUY, 1 SELL, 2 BUY_LIMIT, 3 SELL_LIMIT, 4 BUY_STOP, 5 SELL_STOP, 6 BUY_STOP_LIMIT, 7 SELL_STOP_LIMIT
    if v.isdigit():
        n = int(v)
        return Side.BUY if (n % 2 == 0) else Side.SELL

    raise ValueError(f"invalid side/type: {s!r}")


def _sniff_dialect(sample: str) -> csv.Dialect:
    try:
        return csv.Sniffer().sniff(sample, delimiters=[",", ";", "\t", "|"])
    except Exception:
        return csv.excel


def _get(row: dict, keymap: dict[str, str], *keys: str) -> str:
    """
    Case-insensitive key lookup with aliases.
    """
    for k in keys:
        actual = keymap.get(k.lower())
        if actual is None:
            continue
        v = row.get(actual)
        if v is None:
            continue
        s = str(v).strip()
        if s:
            return s
    return ""


def read_trades_csv(path: str | Path, source: str) -> list[Trade]:
    """
    Supported header styles:

    1) Normalized (recommended):
       trade_id,symbol,side,open_time,open_price,close_time,close_price,volume,sl,tp

    2) MT5-ish / export-ish:
       Ticket,Symbol,Type,Time,Price,Volume
       (Type can be BUY/SELL or 0/1/2/3/...)

    Minimal required (after aliasing):
      symbol, side/type, open_time/time, open_price/price
    """
    p = Path(path)
    trades: list[Trade] = []

    with p.open("r", encoding="utf-8-sig", newline="") as f:
        sample = f.read(4096)
        f.seek(0)
        dialect = _sniff_dialect(sample)

        reader = csv.DictReader(f, dialect=dialect)
        if reader.fieldnames is None:
            raise ValueError("CSV has no header row")

        for row in reader:
            # case-insensitive header map
            keymap = {str(k).strip().lower(): k for k in row.keys() if k is not None}

            symbol = _get(row, keymap, "symbol", "sym")
            side_raw = _get(row, keymap, "side", "type", "direction")
            open_time_raw = _get(row, keymap, "open_time", "time", "time_open", "timeopen")
            open_price_raw = _get(row, keymap, "open_price", "price", "price_open", "priceopen")

            if not symbol or not side_raw or not open_time_raw or not open_price_raw:
                raise ValueError(
                    f"missing required fields in {p.name}: "
                    f"symbol={bool(symbol)} side/type={bool(side_raw)} "
                    f"time={bool(open_time_raw)} price={bool(open_price_raw)}"
                )

            side = _parse_side(side_raw)
            open_time = _parse_dt(open_time_raw)
            open_price = float(open_price_raw)

            def fopt(*keys: str) -> Optional[float]:
                v = _get(row, keymap, *keys)
                return float(v) if v else None

            def dtopt(*keys: str) -> Optional[datetime]:
                v = _get(row, keymap, *keys)
                return _parse_dt(v) if v else None

            trade_id = _get(row, keymap, "trade_id", "ticket", "order", "position_id", "id") or None

            trades.append(
                Trade(
                    source=source,
                    symbol=symbol,
                    side=side,
                    open_time=open_time,
                    open_price=open_price,
                    close_time=dtopt("close_time", "time_close", "timeclose", "closetime"),
                    close_price=fopt("close_price", "price_close", "closeprice", "priceclose"),
                    volume=fopt("volume", "lots", "vol"),
                    sl=fopt("sl", "stoploss", "stop_loss"),
                    tp=fopt("tp", "takeprofit", "take_profit"),
                    trade_id=trade_id,
                )
            )

    return trades