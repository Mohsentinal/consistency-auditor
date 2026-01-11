# Changelog

## v0.1.0
- CLI: udit subcommand (backtest vs live CSV)
- Matching: time tolerance + optional --price-tolerance
- Reports: console summary + optional --out CSV export (matched / unmatched) with --out-prefix
- Robust CSV loader: supports normalized headers + MT5-style exports (Ticket/Type/Time/Price)
- Exit codes: friendly missing-file errors + mismatch gating via --fail-on
- CI: GitHub Actions runs ruff + pytest
- Docs: README + AUDITOR_SPEC