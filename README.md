# consistency-auditor

Audit **backtest vs live trading** consistency and generate reports:

- Missing / extra trades
- Entry time & price alignment with **full distribution statistics** (mean ± std, p50, p95, max)
- **Exit matching** — close time diff, close price diff
- **P&L drift** — per-trade and cumulative backtest vs live profit comparison
- **Event-log replay** — parse `ConsistencyRecorder` JSONL logs to audit the full decision → order → fill chain with latency stats

## Dev setup (Windows)

    python -m venv .venv
    .\.venv\Scripts\Activate.ps1
    python -m pip install -U pip
    python -m pip install -e ".[dev]"
    pytest -q

## Quick check

    consistency-auditor --version

---

## Audit CSVs

Compare a backtest CSV against a live CSV:

    consistency-auditor audit \
      --backtest .\examples\backtest.csv \
      --live     .\examples\live.csv \
      --tolerance 120 \
      --price-tolerance 0.0003 \
      --out .\outputs \
      --out-prefix demo

**Outputs (when `--out` is provided):**

- `outputs\matched_demo.csv`   — matched pairs with entry + exit + P&L columns
- `outputs\unmatched_demo.csv` — missing_in_live + extra_in_live

### Example output

~~~text
matched=1  missing_in_live=1  extra_in_live=1

── Entry statistics ──────────────────────────────────────────
  open_time_diff_s  : mean=60.0000 ±0.0000 [min=60.0000  p50=60.0000  p95=60.0000  max=60.0000]  n=1
  abs_open_price_diff: mean=0.0002 ±0.0000 [min=0.0002   p50=0.0002   p95=0.0002   max=0.0002 ]  n=1

── Exit statistics ───────────────────────────────────────────
  close_time_diff_s  : mean=70.0000 ±0.0000 [min=70.0000  p50=70.0000  p95=70.0000  max=70.0000]  n=1
  abs_close_price_diff: mean=0.0001 ±0.0000 [min=0.0001   p50=0.0001   p95=0.0001   max=0.0001 ]  n=1

── P&L drift statistics ──────────────────────────────────────
  pnl_diff           : mean=-0.0000 ±0.0000 [min=-0.0000  p50=-0.0000  p95=-0.0000  max=-0.0000]  n=1
  total_bt_pnl=+0.000100  total_lv_pnl=+0.000070  total_pnl_drift=-0.000030

── Matched pairs ─────────────────────────────────────────────
  BT: EURUSD BUY open=2026-01-01T10:00:00+00:00 price=1.100000 id=BT-1
  LV: EURUSD BUY open=2026-01-01T10:01:00+00:00 price=1.100200 id=LV-991
  entry: dt_s=60.00  price_diff=+0.000200  exit: dt_s=70.00  close_price_diff=-0.000100  pnl_diff=-0.000030

Missing in live (1):
  EURUSD SELL open=2026-01-01T12:00:00+00:00 price=1.200000 id=BT-2

Extra in live (1):
  EURUSD BUY open=2026-01-02T09:00:00+00:00 price=1.150000 id=LV-992

Wrote: outputs\matched_demo.csv
Wrote: outputs\unmatched_demo.csv
~~~

---

## Replay event log

If your bot uses `ConsistencyRecorder`, audit the full decision → order → fill chain:

    consistency-auditor replay \
      --events .\run_outputs\run_001\audit\events.jsonl \
      --fail-on rejected

### Example output

~~~text
── Run info ──────────────────────────────────────────────────
  run_id=run_001  version=1.0.0  config=abc12345
  started=2026-01-01T10:00:00+00:00

── Decision summary ──────────────────────────────────────────
  total_decisions=3  actionable=2
  filled=1  rejected=1  unexecuted=0
  fill_rate=50.0%

── Decision-to-fill latency (ms) ─────────────────────────────
  latency_ms: mean=250.0 ±0.0000 [min=250.0  p50=250.0  p95=250.0  max=250.0]  n=1

── Rejections (1) ────────────────────────────────────────────
  signal_id=sig_sell_002  sym=GBPUSD  intent=SELL  reason=Insufficient margin
~~~

### Integrating `ConsistencyRecorder` into your bot

```python
from consistency_auditor.recorder import ConsistencyRecorder
from consistency_auditor.schemas import DecisionContext, OrderRequest, ExecutionReport

recorder = ConsistencyRecorder(root_dir="./run_outputs", run_id="run_001")
recorder.log_startup(config=my_config, app_version="1.0.0")

# On every bar:
ctx = DecisionContext(
    symbol="EURUSD",
    decision_time=now,
    bid=1.10,
    ask=1.1001,
    spread=0.0001,
    strategy_tag="MACD_X",
    params=my_config,
    bars_hash=hash_of_bars,
    features_hash=hash_of_indicators,
)
signal_id = recorder.log_decision(ctx, intent="BUY", bars=df_bars)

# After order dispatch:
recorder.log_order_request(OrderRequest(signal_id=signal_id, ...))

# After broker response:
recorder.log_execution(ExecutionReport(signal_id=signal_id, event_subtype="FILL_OPEN", ...))
```

---

## CSV input formats

The loader accepts either normalized headers or MT5-style exports:

**Normalized (recommended):**

    trade_id,symbol,side,open_time,open_price,close_time,close_price,volume,sl,tp

**MT5-style:**

    Ticket,Symbol,Type,Time,Price,Volume

Exit columns (`close_time`, `close_price`) are optional — if present on both sides of a matched pair, exit diff and P&L are computed automatically.

---

## Exit codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 2 | Invalid usage / missing input file |
| 3 | Mismatch or anomaly detected (only when `--fail-on` is set) |

---

## CI

GitHub Actions runs **ruff + pytest** on push/PR.
