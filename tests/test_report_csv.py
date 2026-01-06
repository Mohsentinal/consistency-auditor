from __future__ import annotations

from pathlib import Path

from consistency_auditor.cli import main


def test_cli_writes_csv_outputs(tmp_path: Path, capsys):
    backtest = tmp_path / "backtest.csv"
    live = tmp_path / "live.csv"
    out_dir = tmp_path / "out"

    backtest.write_text(
        "symbol,side,open_time,open_price,trade_id\n"
        "EURUSD,BUY,2026-01-01T10:00:00+00:00,1.1000,BT-1\n"
        "EURUSD,SELL,2026-01-01T12:00:00+00:00,1.2000,BT-2\n",
        encoding="utf-8",
    )
    live.write_text(
        "symbol,side,open_time,open_price,trade_id\n"
        "EURUSD,BUY,2026-01-01T10:01:00+00:00,1.1002,LV-1\n"
        "EURUSD,BUY,2026-01-02T09:00:00+00:00,1.1500,LV-2\n",
        encoding="utf-8",
    )

    rc = main(
        [
            "audit",
            "--backtest",
            str(backtest),
            "--live",
            str(live),
            "--tolerance",
            "120",
            "--out",
            str(out_dir),
        ]
    )
    _ = capsys.readouterr().out

    assert rc == 0
    assert (out_dir / "matched.csv").exists()
    assert (out_dir / "unmatched.csv").exists()