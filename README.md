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
## Example output

~~~text
matched=1 missing_in_live=1 extra_in_live=1
mean_open_time_diff_s=60.00 mean_abs_open_price_diff=0.000200

Matched pairs:
  BT: EURUSD BUY open=2026-01-01T10:00:00+00:00 price=1.100000 id=BT-1
  LV: EURUSD BUY open=2026-01-01T10:01:00+00:00 price=1.100200 id=LV-991
  dt_s=60.00 price_diff=+0.000200


Missing in live (1):
  EURUSD SELL open=2026-01-01T12:00:00+00:00 price=1.200000 id=BT-2

Extra in live (1):
  EURUSD BUY open=2026-01-02T09:00:00+00:00 price=1.150000 id=LV-992

Wrote: outputs\matched_demo.csv
Wrote: outputs\unmatched_demo.csv

~~~

