# consistency-auditor

Audit **backtest vs live trading** consistency and generate simple reports:

- missing / extra trades
- entry & exit time alignment
- price slippage statistics
- latency (signal → fill, if available)

## Dev setup (Windows)

    python -m venv .venv
    .\.venv\Scripts\Activate.ps1
    python -m pip install -U pip
    python -m pip install -e ".[dev]"
    pytest -q

## Quick check

    consistency-auditor --version
    consistency-auditor