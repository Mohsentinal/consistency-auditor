from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Optional


class Side(str, Enum):
    BUY = "BUY"
    SELL = "SELL"


def _ensure_tz(dt: datetime) -> datetime:
    # If naive, assume UTC (we don't want tz bugs later).
    return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt


@dataclass(frozen=True)
class Trade:
    """
    Normalized trade record used by the auditor (independent of your bot/broker formats).
    """
    source: str               # "backtest" or "live" (or any label)
    symbol: str
    side: Side
    open_time: datetime
    open_price: float

    close_time: Optional[datetime] = None
    close_price: Optional[float] = None
    volume: Optional[float] = None
    sl: Optional[float] = None
    tp: Optional[float] = None

    trade_id: Optional[str] = None  # ticket / order id (if available)

    def __post_init__(self) -> None:
        object.__setattr__(self, "open_time", _ensure_tz(self.open_time))
        if self.close_time is not None:
            object.__setattr__(self, "close_time", _ensure_tz(self.close_time))