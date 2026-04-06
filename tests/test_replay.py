from __future__ import annotations

from pathlib import Path

from consistency_auditor.cli import main
from consistency_auditor.replay import replay_from_file


def _write_events(path: Path) -> None:
    path.write_text(
        "\n".join(
            [
                '{"event_type":"RUN_START","run_id":"run_001","timestamp":"2026-01-01T10:00:00+00:00","app_version":"1.0.0","config_fingerprint":"abc12345"}',
                '{"event_type":"DECISION","signal_id":"sig_buy_001","intent":"BUY","context":{"symbol":"EURUSD","decision_time":"2026-01-01T10:00:00+00:00"}}',
                '{"event_type":"ORDER_SENT","signal_id":"sig_buy_001","timestamp":"2026-01-01T10:00:00.100000+00:00","symbol":"EURUSD","side":"BUY"}',
                '{"event_type":"FILL_OPEN","signal_id":"sig_buy_001","timestamp":"2026-01-01T10:00:00.250000+00:00","fill_price":1.1002}',
                '{"event_type":"DECISION","signal_id":"sig_sell_002","intent":"SELL","context":{"symbol":"GBPUSD","decision_time":"2026-01-01T10:05:00+00:00"}}',
                '{"event_type":"ORDER_SENT","signal_id":"sig_sell_002","timestamp":"2026-01-01T10:05:00.200000+00:00","symbol":"GBPUSD","side":"SELL"}',
                '{"event_type":"REJECTED","signal_id":"sig_sell_002","timestamp":"2026-01-01T10:05:00.400000+00:00","comment":"Insufficient margin"}',
                '{"event_type":"DECISION","signal_id":"sig_none_003","intent":"NONE","context":{"symbol":"USDJPY","decision_time":"2026-01-01T10:06:00+00:00"}}',
            ]
        )
        + "\n",
        encoding="utf-8",
    )


def test_replay_report_counts(tmp_path: Path):
    events = tmp_path / "events.jsonl"
    _write_events(events)

    rep = replay_from_file(events)

    assert rep.run_info is not None
    assert rep.total_decisions == 3
    assert rep.actionable_decisions == 2
    assert rep.filled_count == 1
    assert rep.rejected_count == 1
    assert rep.unexecuted_count == 0
    assert len(rep.latencies_ms) == 1
    assert rep.latencies_ms[0] == 250.0


def test_cli_replay_fail_on_rejected(tmp_path: Path, capsys):
    events = tmp_path / "events.jsonl"
    _write_events(events)

    rc = main(["replay", "--events", str(events), "--fail-on", "rejected"])
    out = capsys.readouterr().out

    assert rc == 3
    assert "filled=1  rejected=1  unexecuted=0" in out
    assert "signal_id=sig_sell_00" in out
