from __future__ import annotations

from pathlib import Path

from consistency_auditor.io_csv import read_trades_csv
from consistency_auditor.models import Side


def test_read_trades_csv_mt5_style_headers(tmp_path: Path):
    p = tmp_path / "mt5.csv"
    p.write_text(
        "Ticket,Symbol,Type,Time,Price,Volume\n"
        "123,EURUSD,0,2026.01.01 10:00:00,1.1000,0.10\n"
        "124,EURUSD,1,2026.01.01 12:00:00,1.2000,0.10\n",
        encoding="utf-8",
    )

    trades = read_trades_csv(p, source="live")
    assert len(trades) == 2
    assert trades[0].trade_id == "123"
    assert trades[0].symbol == "EURUSD"
    assert trades[0].side == Side.BUY
    assert trades[1].side == Side.SELL