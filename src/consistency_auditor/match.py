from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from typing import Optional

from .models import Trade


@dataclass(frozen=True)
class TradeMatch:
    backtest: Trade
    live: Trade
    open_time_diff_s: float
    open_price_diff: float


@dataclass(frozen=True)
class AuditResult:
    matched: list[TradeMatch]
    missing_in_live: list[Trade]
    extra_in_live: list[Trade]


def audit_trades(
    backtest: list[Trade],
    live: list[Trade],
    time_tolerance_s: int = 120,
    price_tolerance: float | None = None,
) -> AuditResult:
    """
    MVP matcher:
    - match by (symbol, side) and nearest open_time within tolerance
    - optional price tolerance gate (abs(open_price_diff) <= price_tolerance)
    - 1-to-1 greedy matching
    """
    tol = timedelta(seconds=time_tolerance_s)

    bt_remaining = backtest[:]
    matched: list[TradeMatch] = []
    extra_in_live: list[Trade] = []

    bt_remaining.sort(key=lambda t: (t.symbol, t.side.value, t.open_time))
    live_sorted = sorted(live, key=lambda t: (t.symbol, t.side.value, t.open_time))

    for lt in live_sorted:
        best_i: Optional[int] = None
        best_dt: Optional[timedelta] = None

        for i, bt in enumerate(bt_remaining):
            if bt.symbol != lt.symbol or bt.side != lt.side:
                continue

            dt = abs(bt.open_time - lt.open_time)
            if dt > tol:
                continue

            # price gate (if enabled)
            if price_tolerance is not None:
                if abs(lt.open_price - bt.open_price) > price_tolerance:
                    continue

            if best_dt is None or dt < best_dt:
                best_dt = dt
                best_i = i

        if best_i is None:
            extra_in_live.append(lt)
            continue

        bt = bt_remaining.pop(best_i)
        open_time_diff_s = abs((bt.open_time - lt.open_time).total_seconds())
        open_price_diff = (lt.open_price - bt.open_price)

        matched.append(
            TradeMatch(
                backtest=bt,
                live=lt,
                open_time_diff_s=open_time_diff_s,
                open_price_diff=open_price_diff,
            )
        )

    missing_in_live = bt_remaining
    return AuditResult(matched=matched, missing_in_live=missing_in_live, extra_in_live=extra_in_live)