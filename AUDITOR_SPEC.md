# Consistency Auditor Spec (MVP)

This document defines the **current** behavior of the consistency-auditor CLI and its inputs/outputs.

## Goal (MVP)
Compare **backtest** vs **live** trade lists and report:
- matched trades
- missing in live
- extra in live
- time/price differences for matched entries

This is a **trade-list auditor** (not a full replay engine yet).

## Inputs

### 1) Backtest CSV
### 2) Live CSV

The loader accepts either:
A) Normalized headers (recommended):
  trade_id,symbol,side,open_time,open_price,close_time,close_price,volume,sl,tp

B) MT5-ish headers (common exports):
  Ticket,Symbol,Type,Time,Price,Volume

#### Required fields (after aliasing)
- symbol
- side/type
- open_time/time
- open_price/price

#### Supported aliases (case-insensitive)
- trade_id: trade_id, ticket, order, position_id, id
- symbol: symbol, sym
- side: side, type, direction
- open_time: open_time, time, time_open, timeopen
- open_price: open_price, price, price_open, priceopen
- close_time: close_time, time_close, timeclose, closetime
- close_price: close_price, price_close, closeprice, priceclose
- volume: volume, lots, vol
- sl: sl, stoploss, stop_loss
- tp: tp, takeprofit, take_profit

#### Side parsing
- BUY / LONG => BUY
- SELL / SHORT => SELL
- Numeric MT5 Type (0..7):
  Even => BUY (0,2,4,6), Odd => SELL (1,3,5,7)

#### Datetime parsing (UTC)
Accepted formats:
- ISO8601 (e.g., 2026-01-01T10:00:00+00:00 or trailing Z)
- Unix seconds (digits only)
- MT5 common: YYYY.MM.DD HH:MM:SS
- Also: YYYY-MM-DD HH:MM:SS

All parsed datetimes are treated/stored as timezone-aware UTC.

## Matching Logic (current MVP)
The matcher is greedy 1-to-1:
- Candidate match must have same (symbol, side)
- Choose nearest open_time within --tolerance seconds
- If --price-tolerance is provided, also require:
    abs(live.open_price - backtest.open_price) <= price_tolerance
- Each backtest trade can match at most one live trade (and vice versa)

Outputs:
- matched: list of paired trades with open_time_diff_s and open_price_diff
- missing_in_live: backtest trades not matched
- extra_in_live: live trades not matched

## CLI

### Version
  consistency-auditor --version

### Audit
  consistency-auditor audit --backtest <path> --live <path> [--tolerance 120] [--price-tolerance <float>] [--out <dir>] [--out-prefix <name>] [--fail-on <mode>]

Notes:
- If --out is provided, two CSVs are written:
  - matched_<prefix>.csv
  - unmatched_<prefix>.csv
  If prefix is empty, files are:
  - matched.csv
  - unmatched.csv

- --out-prefix exists to avoid overwriting outputs from repeated runs.

- --fail-on changes exit code behavior when mismatches exist.

## Exit Codes
- 0: success (normal run; even if mismatches exist, unless --fail-on triggers)
- 2: invalid usage / missing input file path on disk
- 3: mismatches detected and --fail-on condition met

## Known Limitations (current MVP)
- Matching is only based on (symbol, side, open_time proximity) + optional price tolerance
- No signal_id / decision snapshots yet
- No partial fill handling
- No exit/close matching metrics (only stored if present; not audited yet)