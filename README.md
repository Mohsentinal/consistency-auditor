# consistency-auditor

Audit backtest vs live trading consistency and generate reports from both CSV trade lists and `ConsistencyRecorder` event logs.

## What it does

- Match backtest vs live trades with exact-ID + fuzzy time matching
- Report missing / extra trades
- Measure entry and exit time/price alignment with full distribution statistics
- Estimate per-trade and cumulative P&L drift
- Replay `DECISION -> ORDER_SENT -> FILL/REJECTED` chains from JSONL logs
- Emit matched / unmatched CSV reports for further analysis

## Install

### From source

```bash
python -m pip install -e ".[dev]"
```

### Quick CLI check

```bash
consistency-auditor --version
```

## Audit CSVs

```bash
consistency-auditor audit   --backtest .\examples\backtest.csv   --live     .\examples\live.csv   --tolerance 120   --price-tolerance 0.0003   --out .\outputs   --out-prefix demo
```

Outputs when `--out` is provided:
- `outputs\matched_demo.csv`
- `outputs\unmatched_demo.csv`

## Replay event log

```bash
consistency-auditor replay   --events .\examples\events.jsonl   --fail-on rejected
```

Expected replay summary includes:
- run info
- total decisions / actionable decisions
- filled / rejected / unexecuted counts
- fill rate
- decision-to-fill latency stats
- rejection details

## Dev setup (Windows)

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -U pip
python -m pip install -e ".[dev]"
ruff check .
pytest -q
python -m build
```

## CI

GitHub Actions runs Ruff + pytest on push and pull request. The package is ready for build validation and PyPI release after CI is green.

## Files worth reading

- `AUDITOR_SPEC.md` — behavior/specification
- `CHANGELOG.md` — release history
- `CONTRIBUTING.md` — local workflow and release checklist
