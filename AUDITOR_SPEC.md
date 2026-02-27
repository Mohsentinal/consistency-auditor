# Consistency Auditor Spec (v0.2.0)

This document defines the **current** behavior of the consistency-auditor CLI and its inputs/outputs.

---

## Goal
Compare **backtest** vs **live** trade lists and report:
- Matched trades with full entry + exit + P&L statistics
- Missing in live / extra in live
- Time/price differences with distribution stats (mean, std, p50, p95, max)

Additionally, parse **ConsistencyRecorder event logs** to audit the full
`DECISION → ORDER_SENT → FILL/REJECTED` chain and report fill rate, latency, and anomalies.

---

## `audit` subcommand

### Inputs

#### Backtest CSV / Live CSV

The loader accepts either:

**A) Normalized headers (recommended):**
```
trade_id,symbol,side,open_time,open_price,close_time,close_price,volume,sl,tp
```

**B) MT5-ish headers (common exports):**
```
Ticket,Symbol,Type,Time,Price,Volume
```

#### Required fields (after aliasing)
- `symbol`
- `side` / `type`
- `open_time` / `time`
- `open_price` / `price`

#### Optional fields (used for exit/P&L analysis when present)
- `close_time`, `close_price`
- `volume` (used for P&L calculation; defaults to 1.0 if absent)

#### Supported aliases (case-insensitive)
- `trade_id`:    trade_id, ticket, order, position_id, id
- `symbol`:      symbol, sym
- `side`:        side, type, direction
- `open_time`:   open_time, time, time_open, timeopen
- `open_price`:  open_price, price, price_open, priceopen
- `close_time`:  close_time, time_close, timeclose, closetime
- `close_price`: close_price, price_close, closeprice, priceclose
- `volume`:      volume, lots, vol
- `sl`:          sl, stoploss, stop_loss
- `tp`:          tp, takeprofit, take_profit

#### Side parsing
- BUY / LONG → BUY
- SELL / SHORT → SELL
- Numeric MT5 Type (0..7): Even → BUY (0,2,4,6), Odd → SELL (1,3,5,7)

#### Datetime parsing (UTC)
- ISO8601 (e.g., `2026-01-01T10:00:00+00:00` or trailing `Z`)
- Unix seconds (digits only)
- MT5 common: `YYYY.MM.DD HH:MM:SS`
- Also: `YYYY-MM-DD HH:MM:SS`

All parsed datetimes are stored as timezone-aware UTC.

### Matching Logic
Two-pass greedy 1-to-1 matcher:

**Pass 1 — Exact ID match:**
- If both backtest and live trades share the same `trade_id` AND same `(symbol, side)`, they are linked immediately.

**Pass 2 — Fuzzy time match (remaining trades):**
- Candidate match must have same `(symbol, side)`.
- Choose nearest `open_time` within `--tolerance` seconds.
- If `--price-tolerance` is provided, also require: `abs(live.open_price - backtest.open_price) ≤ price_tolerance`
- Each backtest trade can match at most one live trade (and vice versa).

### Per-match outputs
| Field | Description |
|-------|-------------|
| `open_time_diff_s` | \|bt.open_time - lv.open_time\| in seconds |
| `open_price_diff` | lv.open_price - bt.open_price |
| `close_time_diff_s` | \|bt.close_time - lv.close_time\| in seconds (if both present) |
| `close_price_diff` | lv.close_price - bt.close_price (if both present) |
| `bt_pnl` / `lv_pnl` | `(close - open) * volume` for BUY; `(open - close) * volume` for SELL |
| `pnl_diff` | lv_pnl - bt_pnl |

### Statistical summary
For each numeric metric across all matched pairs, the report includes:
- `mean ± std [min  p50  p95  max]  n=<count>`

P&L section additionally shows `total_bt_pnl`, `total_lv_pnl`, and `total_pnl_drift`.

### CLI

    consistency-auditor audit \
      --backtest <path> \
      --live <path> \
      [--tolerance 120] \
      [--price-tolerance <float>] \
      [--out <dir>] \
      [--out-prefix <str>] \
      [--fail-on none|any|missing|extra]

**Output files** (when `--out` is provided):
- `matched_<prefix>.csv`   — entry + exit + P&L columns per matched pair
- `unmatched_<prefix>.csv` — missing_in_live and extra_in_live with close data columns

---

## `replay` subcommand

### Input: `events.jsonl`

A JSONL file produced by `ConsistencyRecorder`. Each line is a JSON object with an `event_type` field.

#### Supported event types

| event_type | Key fields |
|------------|-----------|
| `RUN_START` | `run_id`, `timestamp`, `app_version`, `config_fingerprint` |
| `DECISION` | `signal_id`, `intent` (BUY/SELL/NONE), `context.symbol`, `context.decision_time` |
| `ORDER_SENT` | `signal_id`, `timestamp`, `symbol`, `side` |
| `FILL_OPEN` | `signal_id`, `timestamp`, `fill_price` |
| `FILL_CLOSE` | `signal_id`, `timestamp`, `fill_price`, `profit` |
| `ORDER_RESULT` | `signal_id`, `timestamp` (generic fill) |
| `REJECTED` | `signal_id`, `timestamp`, `comment` |

### Chain linking
All events sharing the same `signal_id` are grouped into an `EventChain`:
- `DECISION` → `ORDER_SENT` → `FILL_*` / `REJECTED`
- A chain is **complete** when all three stages are present.

### Report metrics
- `total_decisions` — total DECISION events
- `actionable_decisions` — DECISION events with intent ≠ NONE
- `filled` / `rejected` / `unexecuted`
- `fill_rate` — filled / actionable
- Decision-to-fill **latency** distribution (ms): mean ± std [min p50 p95 max]
- Rejection list with `comment`
- Unexecuted signals list

### CLI

    consistency-auditor replay \
      --events <path> \
      [--fail-on none|any|rejected|unexecuted]

---

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 2 | Invalid usage / missing input file |
| 3 | Mismatch or anomaly detected (only when `--fail-on` condition is met) |

---

## Known Limitations (v0.2.0)
- Exit matching computes diff but does **not** gate fuzzy matching on close proximity (entries only)
- P&L is a simplified `price_diff × volume`; no commission, swap, or spread adjustment
- Latency is computed from ISO timestamps; sub-millisecond precision depends on log quality
- No partial fill handling
- `replay` does not yet cross-reference with backtest CSV (`audit` + `replay` are separate workflows)
