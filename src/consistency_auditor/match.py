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
    Two-pass matcher:
    1. Exact Match: Link trades sharing the same 	rade_id (or signal_id).
    2. Fuzzy Match: Link remaining trades by (symbol, side, time) within tolerance.
    """
    tol = timedelta(seconds=time_tolerance_s)

    # Buckets for results
    matched: list[TradeMatch] = []

    # Working lists (mutable copies)
    bt_remaining = backtest[:]
    lv_remaining = live[:]

    # --- PASS 1: Exact ID Matching ---
    # Create a lookup for backtest trades that HAVE an ID
    bt_map = {t.trade_id: i for i, t in enumerate(bt_remaining) if t.trade_id}

    # INDICES to remove from lv_remaining and bt_remaining after Pass 1
    lv_matched_indices = []
    bt_matched_indices = []

    for i, lt in enumerate(lv_remaining):
        if lt.trade_id and lt.trade_id in bt_map:
            bt_idx = bt_map[lt.trade_id]

            # Safety check: ensure symbol/side actually match (prevent ID collisions)
            bt = bt_remaining[bt_idx]
            if bt.symbol == lt.symbol and bt.side == lt.side:
                # We have a match!
                matched.append(
                    TradeMatch(
                        backtest=bt,
                        live=lt,
                        open_time_diff_s=abs((bt.open_time - lt.open_time).total_seconds()),
                        open_price_diff=(lt.open_price - bt.open_price),
                    )
                )
                lv_matched_indices.append(i)
                bt_matched_indices.append(bt_idx)

    # Remove matched trades from the pool (in reverse order to preserve indices)
    for i in sorted(lv_matched_indices, reverse=True):
        lv_remaining.pop(i)

    for i in sorted(bt_matched_indices, reverse=True):
        bt_remaining.pop(i)

    # --- PASS 2: Fuzzy Time Matching (Existing Logic) ---
    extra_in_live: list[Trade] = []

    # Sort remaining for greedy time matching
    bt_remaining.sort(key=lambda t: (t.symbol, t.side.value, t.open_time))
    # lv_remaining is already roughly sorted, but let's be safe
    lv_remaining.sort(key=lambda t: (t.symbol, t.side.value, t.open_time))

    for lt in lv_remaining:
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
        matched.append(
            TradeMatch(
                backtest=bt,
                live=lt,
                open_time_diff_s=abs((bt.open_time - lt.open_time).total_seconds()),
                open_price_diff=(lt.open_price - bt.open_price),
            )
        )

    missing_in_live = bt_remaining

    return AuditResult(matched=matched, missing_in_live=missing_in_live, extra_in_live=extra_in_live)
