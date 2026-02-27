from __future__ import annotations

import statistics
from dataclasses import dataclass
from datetime import timedelta
from typing import Optional

from .models import Trade


@dataclass(frozen=True)
class TradeMatch:
    backtest: Trade
    live: Trade
    # Entry metrics
    open_time_diff_s: float
    open_price_diff: float
    # Exit metrics (None if either side lacks close data)
    close_time_diff_s: Optional[float] = None
    close_price_diff: Optional[float] = None
    # P&L metrics (None if close prices unavailable)
    bt_pnl: Optional[float] = None
    lv_pnl: Optional[float] = None
    pnl_diff: Optional[float] = None


@dataclass(frozen=True)
class SlippageStats:
    """Detailed statistical breakdown of a numeric series."""
    mean: float
    std: float
    min: float
    max: float
    p50: float
    p95: float
    count: int

    @classmethod
    def from_values(cls, values: list[float]) -> "SlippageStats":
        n = len(values)
        if n == 0:
            return cls(0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0)
        sorted_v = sorted(values)
        mean = statistics.mean(sorted_v)
        std = statistics.stdev(sorted_v) if n > 1 else 0.0
        p50 = statistics.median(sorted_v)
        p95_idx = min(int(0.95 * n), n - 1)
        p95 = sorted_v[p95_idx]
        return cls(mean=mean, std=std, min=sorted_v[0], max=sorted_v[-1], p50=p50, p95=p95, count=n)

    def __str__(self) -> str:
        return (
            f"mean={self.mean:.4f} ±{self.std:.4f} "
            f"[min={self.min:.4f} p50={self.p50:.4f} p95={self.p95:.4f} max={self.max:.4f}]"
        )


@dataclass
class AuditStats:
    """Aggregate statistics computed from matched trades."""
    open_time_diff_s: SlippageStats
    abs_open_price_diff: SlippageStats
    close_time_diff_s: Optional[SlippageStats] = None
    abs_close_price_diff: Optional[SlippageStats] = None
    pnl_diff: Optional[SlippageStats] = None


@dataclass(frozen=True)
class AuditResult:
    matched: list[TradeMatch]
    missing_in_live: list[Trade]
    extra_in_live: list[Trade]
    stats: AuditStats


def _compute_pnl(trade: Trade) -> Optional[float]:
    """Compute simple P&L (close_price - open_price for BUY, inverse for SELL)."""
    if trade.close_price is None:
        return None
    from .models import Side
    diff = trade.close_price - trade.open_price
    volume = trade.volume or 1.0
    return diff * volume if trade.side == Side.BUY else -diff * volume


def _compute_stats(matched: list[TradeMatch]) -> AuditStats:
    open_time_diffs = [m.open_time_diff_s for m in matched]
    abs_open_price_diffs = [abs(m.open_price_diff) for m in matched]
    close_time_vals = [m.close_time_diff_s for m in matched if m.close_time_diff_s is not None]
    abs_close_price_vals = [abs(m.close_price_diff) for m in matched if m.close_price_diff is not None]
    pnl_diff_vals = [m.pnl_diff for m in matched if m.pnl_diff is not None]
    return AuditStats(
        open_time_diff_s=SlippageStats.from_values(open_time_diffs),
        abs_open_price_diff=SlippageStats.from_values(abs_open_price_diffs),
        close_time_diff_s=SlippageStats.from_values(close_time_vals) if close_time_vals else None,
        abs_close_price_diff=SlippageStats.from_values(abs_close_price_vals) if abs_close_price_vals else None,
        pnl_diff=SlippageStats.from_values(pnl_diff_vals) if pnl_diff_vals else None,
    )


def _make_match(bt: Trade, lt: Trade) -> TradeMatch:
    """Build a TradeMatch, computing exit and P&L diffs when data permits."""
    open_time_diff_s = abs((bt.open_time - lt.open_time).total_seconds())
    open_price_diff = lt.open_price - bt.open_price
    close_time_diff_s: Optional[float] = None
    close_price_diff: Optional[float] = None
    if bt.close_time is not None and lt.close_time is not None:
        close_time_diff_s = abs((bt.close_time - lt.close_time).total_seconds())
    if bt.close_price is not None and lt.close_price is not None:
        close_price_diff = lt.close_price - bt.close_price
    bt_pnl = _compute_pnl(bt)
    lv_pnl = _compute_pnl(lt)
    pnl_diff = (lv_pnl - bt_pnl) if (bt_pnl is not None and lv_pnl is not None) else None
    return TradeMatch(
        backtest=bt, live=lt,
        open_time_diff_s=open_time_diff_s, open_price_diff=open_price_diff,
        close_time_diff_s=close_time_diff_s, close_price_diff=close_price_diff,
        bt_pnl=bt_pnl, lv_pnl=lv_pnl, pnl_diff=pnl_diff,
    )


def audit_trades(
    backtest: list[Trade],
    live: list[Trade],
    time_tolerance_s: int = 120,
    price_tolerance: float | None = None,
) -> AuditResult:
    """
    Two-pass matcher:
    1. Exact Match: Link trades sharing the same trade_id.
    2. Fuzzy Match: Link remaining trades by (symbol, side, open_time) within tolerance.

    For matched pairs, also computes:
    - Exit: close_time_diff_s, close_price_diff (when close data present on both sides)
    - P&L:  bt_pnl, lv_pnl, pnl_diff           (when close prices available)
    """
    tol = timedelta(seconds=time_tolerance_s)
    matched: list[TradeMatch] = []
    bt_remaining = backtest[:]
    lv_remaining = live[:]

    # --- PASS 1: Exact ID Matching ---
    bt_map = {t.trade_id: i for i, t in enumerate(bt_remaining) if t.trade_id}
    lv_matched_indices: list[int] = []
    bt_matched_indices: list[int] = []

    for i, lt in enumerate(lv_remaining):
        if lt.trade_id and lt.trade_id in bt_map:
            bt_idx = bt_map[lt.trade_id]
            bt = bt_remaining[bt_idx]
            if bt.symbol == lt.symbol and bt.side == lt.side:
                matched.append(_make_match(bt, lt))
                lv_matched_indices.append(i)
                bt_matched_indices.append(bt_idx)

    for i in sorted(lv_matched_indices, reverse=True):
        lv_remaining.pop(i)
    for i in sorted(bt_matched_indices, reverse=True):
        bt_remaining.pop(i)

    # --- PASS 2: Fuzzy Time Matching ---
    extra_in_live: list[Trade] = []
    bt_remaining.sort(key=lambda t: (t.symbol, t.side.value, t.open_time))
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
        matched.append(_make_match(bt, lt))

    missing_in_live = bt_remaining
    return AuditResult(
        matched=matched,
        missing_in_live=missing_in_live,
        extra_in_live=extra_in_live,
        stats=_compute_stats(matched),
    )
