from __future__ import annotations

from pathlib import Path

from consistency_auditor.cli import main


def test_fail_on_any_returns_3_when_missing_or_extra(tmp_path: Path, capsys):
    backtest = tmp_path / "backtest.csv"
    live = tmp_path / "live.csv"

    backtest.write_text(
        "symbol,side,open_time,open_price\n"
        "EURUSD,BUY,2026-01-01T10:00:00+00:00,1.1000\n",
        encoding="utf-8",
    )
    live.write_text(
        "symbol,side,open_time,open_price\n"
        "EURUSD,BUY,2026-01-02T10:00:00+00:00,1.1000\n",
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
            "--fail-on",
            "any",
        ]
    )
    _ = capsys.readouterr().out
    assert rc == 3


def test_fail_on_none_returns_0_even_when_missing_or_extra(tmp_path: Path, capsys):
    backtest = tmp_path / "backtest.csv"
    live = tmp_path / "live.csv"

    backtest.write_text(
        "symbol,side,open_time,open_price\n"
        "EURUSD,BUY,2026-01-01T10:00:00+00:00,1.1000\n",
        encoding="utf-8",
    )
    live.write_text(
        "symbol,side,open_time,open_price\n"
        "EURUSD,BUY,2026-01-02T10:00:00+00:00,1.1000\n",
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
            "--fail-on",
            "none",
        ]
    )
    _ = capsys.readouterr().out
    assert rc == 0