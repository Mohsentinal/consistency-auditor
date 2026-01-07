from __future__ import annotations

import hashlib
import json
from typing import Any


def stable_hash(obj: Any) -> str:
    """
    Produce a stable SHA256 hash for a Python object (Step 14).
    - Sorts dictionary keys.
    - Normalizes floats to 8 decimals to avoid precision drift.
    - Converts all values to strings consistently.
    """
    def default(o):
        if isinstance(o, float):
            # Normalize floats to prevent 1.0000001 != 1.0 mismatch
            return f"{o:.8f}"
        return str(o)

    # sort_keys=True is critical for dict consistency
    s = json.dumps(obj, default=default, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def compute_signal_id(
    symbol: str,
    decision_time: Any,
    side: str,
    strategy_tag: str,
    bars_hash: str
) -> str:
    """
    Generate a unique ID for a trade signal (Step 23).
    Format: hash(symbol + time + side + strategy + inputs)
    """
    payload = {
        "sym": str(symbol),
        "dt": str(decision_time),
        "side": str(side),
        "tag": str(strategy_tag),
        "bars": str(bars_hash),
    }
    # We take the first 12 chars to keep it readable but unique enough
    return stable_hash(payload)[:12]


def compute_config_fingerprint(config: dict) -> str:
    """
    Hash only the subset of config that affects logic (Step 13).
    """
    return stable_hash(config)[:8]
