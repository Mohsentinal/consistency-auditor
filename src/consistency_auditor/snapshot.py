from __future__ import annotations

from pathlib import Path
from typing import Any

# We use loose imports here so the library doesn't strictly crash 
# if pandas isn't installed (until you try to snapshot).
try:
    import pandas as pd
except ImportError:
    pd = None


def save_bars_snapshot(
    output_dir: str | Path,
    signal_id: str,
    bars: Any, # Expected: pd.DataFrame
) -> str:
    """
    Saves the exact market data used for a decision to a Parquet file.
    (Step 27)

    Args:
        output_dir: The root audit folder (e.g. 'audit_results/snapshots').
        signal_id: The unique ID linking this data to a Decision event.
        bars: The pandas DataFrame of OHLCV data.

    Returns:
        The relative filename of the saved snapshot.
    """
    if pd is None:
        raise ImportError("Pandas is required to save snapshots. pip install pandas pyarrow")

    if not isinstance(bars, pd.DataFrame):
        raise TypeError(f"Snapshot expects a DataFrame, got {type(bars)}")

    # Ensure snapshot directory exists (Step 25)
    p_dir = Path(output_dir)
    p_dir.mkdir(parents=True, exist_ok=True)

    # Filename format: bars_<signal_id>.parquet
    filename = f"bars_{signal_id}.parquet"
    full_path = p_dir / filename

    # Save to parquet (requires pyarrow or fastparquet)
    # index=True is crucial if your datetime is the index
    bars.to_parquet(full_path, index=True)

    return filename
