from __future__ import annotations

from pathlib import Path

from consistency_auditor.cli import main


def test_cli_missing_backtest_file(tmp_path: Path, capsys):
    live = tmp_path / "live.csv"
    live.write_text("symbol,side,open_time,open_price\n", encoding="utf-8")

    rc = main(["audit", "--backtest", str(tmp_path / "nope.csv"), "--live", str(live)])
    out = capsys.readouterr().out

    assert rc == 2
    assert "ERROR: backtest file not found" in out