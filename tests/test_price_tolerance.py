from __future__ import annotations

from datetime import datetime, timezone

from consistency_auditor.match import audit_trades
from consistency_auditor.models import Side, Trade


def dt(s: str) -> datetime:
    return datetime.fromisoformat(s).replace(tzinfo=timezone.utc)


def test_price_tolerance_blocks_match():
    bt = [Trade("backtest", "EURUSD", Side.BUY, dt("2026-01-01T10:00:00"), 1.1000)]
    lv = [Trade("live", "EURUSD", Side.BUY, dt("2026-01-01T10:01:00"), 1.1002)]  # diff = 0.0002

    res = audit_trades(bt, lv, time_tolerance_s=120, price_tolerance=0.0001)
    assert len(res.matched) == 0
    assert len(res.missing_in_live) == 1
    assert len(res.extra_in_live) == 1


def test_price_tolerance_allows_match():
    bt = [Trade("backtest", "EURUSD", Side.BUY, dt("2026-01-01T10:00:00"), 1.1000)]
    lv = [Trade("live", "EURUSD", Side.BUY, dt("2026-01-01T10:01:00"), 1.1002)]  # diff = 0.0002

    res = audit_trades(bt, lv, time_tolerance_s=120, price_tolerance=0.0003)
    assert len(res.matched) == 1
    assert len(res.missing_in_live) == 0
    assert len(res.extra_in_live) == 0