from __future__ import annotations

from pathlib import Path

from consistency_auditor.cli import main


def test_cli_audit_smoke(tmp_path: Path, capsys):
    backtest = tmp_path / "backtest.csv"
    live = tmp_path / "live.csv"

    backtest.write_text(
        "symbol,side,open_time,open_price\n"
        "EURUSD,BUY,2026-01-01T10:00:00+00:00,1.1000\n"
        "EURUSD,SELL,2026-01-01T12:00:00+00:00,1.2000\n",
        encoding="utf-8",
    )

    live.write_text(
        "symbol,side,open_time,open_price\n"
        "EURUSD,BUY,2026-01-01T10:01:00+00:00,1.1002\n",
        encoding="utf-8",
    )

    rc = main(["audit", "--backtest", str(backtest), "--live", str(live), "--tolerance", "120"])
    out = capsys.readouterr().out

    assert rc == 0
    assert "matched=1" in out
    assert "missing_in_live=1" in out