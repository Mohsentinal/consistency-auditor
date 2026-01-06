# consistency-auditor

Audit **backtest vs live trading** consistency and generate simple reports:

- missing / extra trades
- entry & exit time alignment (MVP: open_time)
- price slippage statistics (MVP: open_price)
- latency (signal → fill, later)

## Dev setup (Windows)

    python -m venv .venv
    .\.venv\Scripts\Activate.ps1
    python -m pip install -U pip
    python -m pip install -e ".[dev]"
    pytest -q

## Quick check

    consistency-auditor --version

## Audit CSVs (example)

    consistency-auditor audit 
      --backtest .\examples\backtest.csv 
      --live .\examples\live.csv 
      --tolerance 120 
      --price-tolerance 0.0003 
      --out .\outputs 
      --out-prefix demo

Outputs (when --out is provided):

- outputs\matched_demo.csv
- outputs\unmatched_demo.csv

## CI

GitHub Actions runs **ruff + pytest** on push/PR.