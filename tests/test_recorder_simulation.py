from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import pytest

# We need pandas for this test
try:
    import pandas as pd
except ImportError:
    pd = None

from consistency_auditor.recorder import ConsistencyRecorder
from consistency_auditor.schemas import DecisionContext


def test_recorder_full_flow(tmp_path: Path):
    """
    Simulates a bot run:
    1. Init recorder
    2. Log startup
    3. Log a BUY decision with snapshot
    4. Verify files exist
    """
    if pd is None:
        pytest.skip("Pandas not installed, cannot test snapshots")

    # 1. Setup
    run_id = "test_run_123"
    # tmp_path is a pytest fixture providing a temporary clean directory
    recorder = ConsistencyRecorder(root_dir=tmp_path, run_id=run_id)

    # 2. Log Startup
    config = {"param_a": 10, "mode": "aggressive"}
    recorder.log_startup(config, app_version="1.0.0")

    # Verify startup event
    events_file = tmp_path / run_id / "audit" / "events.jsonl"
    assert events_file.exists()
    content = events_file.read_text("utf-8")
    assert "RUN_START" in content
    assert "aggressive" in content

    # 3. Log Decision with Snapshot
    # Create dummy bars
    bars = pd.DataFrame({
        "open": [1.0, 1.1],
        "high": [1.2, 1.3],
        "low": [0.9, 1.0],
        "close": [1.1, 1.2],
        "volume": [100, 200]
    })
    
    ctx = DecisionContext(
        symbol="EURUSD",
        decision_time=datetime.now(timezone.utc),
        bid=1.2001,
        ask=1.2002,
        spread=0.0001,
        strategy_tag="MACD_X",
        params=config,
        bars_hash="dummy_hash",
        features_hash="dummy_features"
    )

    # Log the decision
    signal_id = recorder.log_decision(ctx, intent="BUY", bars=bars)

    # 4. Verification
    content_after = events_file.read_text("utf-8")
    
    # Ensure event was appended
    assert "DECISION" in content_after
    assert signal_id in content_after
    
    # Ensure snapshot was saved
    snapshot_file = tmp_path / run_id / "audit" / "snapshots" / f"bars_{signal_id}.parquet"
    assert snapshot_file.exists()
