from __future__ import annotations

from datetime import datetime, timezone

from consistency_auditor.match import audit_trades
from consistency_auditor.models import Side, Trade


def dt(s: str) -> datetime:
    return datetime.fromisoformat(s).replace(tzinfo=timezone.utc)


def test_audit_trades_basic_match():
    bt = [
        Trade("backtest", "EURUSD", Side.BUY, dt("2026-01-01T10:00:00"), 1.1000),
        Trade("backtest", "EURUSD", Side.SELL, dt("2026-01-01T12:00:00"), 1.2000),
    ]
    live = [
        Trade("live", "EURUSD", Side.BUY, dt("2026-01-01T10:01:00"), 1.1002),
    ]

    res = audit_trades(bt, live, time_tolerance_s=120)
    assert len(res.matched) == 1
    assert len(res.extra_in_live) == 0
    assert len(res.missing_in_live) == 1  # the SELL is missing