# Changelog

## v0.2.0
### New features
- **Exit matching**: `audit` now computes `close_time_diff_s` and `close_price_diff` for every matched pair when close data is present in both CSVs
- **P&L drift analysis**: Each matched pair now includes `bt_pnl`, `lv_pnl`, and `pnl_diff`; the console summary shows cumulative P&L drift across all matched trades
- **Rich statistics**: All metrics (entry time diff, entry price diff, exit time diff, exit price diff, P&L diff) now report `mean ± std [min p50 p95 max]` instead of just a mean
- **`replay` subcommand**: New CLI command to audit a `ConsistencyRecorder` event log (JSONL). Reports decision counts, fill rate, rejection list, unexecuted signals, and decision-to-fill latency distribution
- **`replay.py` module**: Full parser for `events.jsonl` — builds `EventChain` objects linking `DECISION → ORDER_SENT → FILL/REJECTED`, exposes `ReplayReport` with aggregate stats
- **`--fail-on` for replay**: Exit code 3 can be triggered by `any`, `rejected`, or `unexecuted` conditions
- **CSV output expanded**: `matched_*.csv` now includes exit and P&L columns; `unmatched_*.csv` includes `close_time` and `close_price`

### Fixes
- Replace deprecated `datetime.utcnow()` with `datetime.now(timezone.utc)` in `report_csv.py`

### Tests added
- `test_close_matching.py` — exit time/price diff, P&L for BUY/SELL, missing close data → None
- `test_slippage_stats.py` — `SlippageStats.from_values` edge cases (empty, single, p95)
- `test_replay.py` — chain parsing, fill rate, latency, unexecuted detection, error handling
- `test_cli_replay.py` — integration tests for `replay` subcommand including `--fail-on` modes

## v0.1.0
- CLI: `audit` subcommand (backtest vs live CSV)
- Matching: time tolerance + optional `--price-tolerance`
- Reports: console summary + optional `--out` CSV export (matched / unmatched) with `--out-prefix`
- Robust CSV loader: supports normalized headers + MT5-style exports (Ticket/Type/Time/Price)
- Exit codes: friendly missing-file errors + mismatch gating via `--fail-on`
- CI: GitHub Actions runs ruff + pytest
- Docs: README + AUDITOR_SPEC
