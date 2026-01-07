from __future__ import annotations

import json
from enum import Enum
from pathlib import Path
from typing import Any


class MismatchReason(str, Enum):
    """
    Reasons why a live trade might not match the replay (Step 6).
    """
    PARAM_DRIFT = "PARAM_DRIFT"           # Config changed between live and replay
    DATA_DRIFT = "DATA_DRIFT"             # Market data (inputs) differed
    EXECUTION_REJECTED = "EXECUTION_REJECTED" # Broker rejected the order
    COOLDOWN_DIFF = "COOLDOWN_DIFF"       # Bot was in cooldown in one but not other
    SLIPPAGE_TOO_HIGH = "SLIPPAGE_TOO_HIGH" # Price moved away before fill
    TIMEOUT = "TIMEOUT"                   # Signal expired before fill
    UNKNOWN = "UNKNOWN"


def write_jsonl(path: str | Path, event: dict[str, Any]) -> None:
    """
    Append a single event to a JSONL file (Steps 7 & 11).
    """
    p = Path(path)
    # Ensure the directory exists (prevents FileNotFoundError)
    p.parent.mkdir(parents=True, exist_ok=True)

    # Atomic append (text mode, utf-8)
    # json.dumps(default=str) handles datetimes/decimals safely
    with p.open("a", encoding="utf-8") as f:
        f.write(json.dumps(event, default=str) + "\n")
